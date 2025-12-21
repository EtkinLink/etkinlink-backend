"""
Admin Panel API Endpoints
Provides comprehensive admin dashboard functionality including:
- Overview statistics and charts
- Events management
- Users management
- Clubs management
- Attendance statistics
- Reports management
"""

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text
from backend.utils.auth_utils import require_admin, AuthError
from backend.utils.pagination import paginate_query, get_pagination_params
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# =============================================
# OVERVIEW DASHBOARD
# =============================================

@admin_bp.get("/overview/summary")
@require_admin
def get_overview_summary():
    """
    Returns only the scalar counts for the dashboard cards.
    Loads very fast.
    """
    try:
        with current_app.engine.connect() as conn:
            # Sadece tekil sayılar (COUNT)
            total_events = conn.execute(text("SELECT COUNT(*) FROM events")).scalar()
            total_users = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            active_clubs = conn.execute(text("SELECT COUNT(*) FROM organizations WHERE status='ACTIVE'")).scalar()
            active_events = conn.execute(text("SELECT COUNT(*) FROM events WHERE status='FUTURE'")).scalar()
            total_attendance = conn.execute(text("SELECT COUNT(*) FROM participants WHERE status='ATTENDED'")).scalar()
            pending_reports = conn.execute(text("SELECT COUNT(*) FROM reports WHERE status='PENDING'")).scalar()
            unreviewed_reports = conn.execute(text("SELECT COUNT(*) FROM reports WHERE is_reviewed = FALSE")).scalar()

            return jsonify({
                "total_events": total_events,
                "total_users": total_users,
                "active_clubs": active_clubs,
                "active_events": active_events,
                "total_attendance": total_attendance,
                "pending_reports": pending_reports,
                "unreviewed_reports": unreviewed_reports,
            })
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/overview/charts")
@require_admin
def get_overview_charts():
    """
    Returns data for charts (Weekly, Monthly, 6-Months).
    May take longer to load.
    """
    try:
        with current_app.engine.connect() as conn:
            # --- CHARTS: EVENTS ---
            events_1w = conn.execute(text("""
                SELECT DATE_FORMAT(created_at, '%Y-%m-%d') as date, COUNT(*) as count
                FROM events WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY date ORDER BY date ASC
            """)).fetchall()

            events_1m = conn.execute(text("""
                SELECT DATE_FORMAT(created_at, '%Y-%m-%d') as date, COUNT(*) as count
                FROM events WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
                GROUP BY date ORDER BY date ASC
            """)).fetchall()

            events_6m = conn.execute(text("""
                SELECT DATE_FORMAT(created_at, '%Y-%m') as date, COUNT(*) as count
                FROM events WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                GROUP BY date ORDER BY date ASC
            """)).fetchall()
            
            # --- CHARTS: ATTENDANCE ---
            attendance_1w = conn.execute(text("""
                SELECT DATE_FORMAT(e.starts_at, '%Y-%m-%d') as date, COUNT(p.id) as count
                FROM participants p JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND p.status = 'ATTENDED'
                GROUP BY date ORDER BY date ASC
            """)).fetchall()

            attendance_1m = conn.execute(text("""
                SELECT DATE_FORMAT(e.starts_at, '%Y-%m-%d') as date, COUNT(p.id) as count
                FROM participants p JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH) AND p.status = 'ATTENDED'
                GROUP BY date ORDER BY date ASC
            """)).fetchall()

            attendance_6m = conn.execute(text("""
                SELECT DATE_FORMAT(e.starts_at, '%Y-%m') as date, COUNT(p.id) as count
                FROM participants p JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH) AND p.status = 'ATTENDED'
                GROUP BY date ORDER BY date ASC
            """)).fetchall()
            
            return jsonify({
                "events": {
                    "last_week": [{"date": r.date, "count": r.count} for r in events_1w],
                    "last_month": [{"date": r.date, "count": r.count} for r in events_1m],
                    "last_6_months": [{"date": r.date, "count": r.count} for r in events_6m]
                },
                "attendance": {
                    "last_week": [{"date": r.date, "count": r.count} for r in attendance_1w],
                    "last_month": [{"date": r.date, "count": r.count} for r in attendance_1m],
                    "last_6_months": [{"date": r.date, "count": r.count} for r in attendance_6m]
                }
            })
    
    except Exception as e:
        return {"error": str(e)}, 503

# =============================================
# EVENTS MANAGEMENT
# =============================================

@admin_bp.get("/events")
@require_admin
def get_all_events():
    """
    Get all events with details for admin management.
    Supports pagination and filtering by status.
    Query params: ?page=1&per_page=20&status=PENDING
    """
    try:
        status_filter = request.args.get("status")
        pagination_params = get_pagination_params()
        
        with current_app.engine.connect() as conn:
            # Build query with optional status filter
            where_clause = ""
            params = {}
            
            if status_filter:
                where_clause = "WHERE e.status = :status"
                params["status"] = status_filter.upper()
            
            base_query = f"""
                SELECT 
                    e.id,
                    e.title,
                    e.explanation,
                    e.owner_type,
                    e.starts_at as date,
                    e.status,
                    e.user_limit as capacity,
                    e.created_at,
                    COALESCE(o.name, u.username) as owner_name,
                    (
                        SELECT COUNT(*) FROM participants p
                        WHERE p.event_id = e.id AND p.status = 'ATTENDED'
                    ) AS attendance_count
                FROM events e
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN users u ON e.owner_user_id = u.id
                {where_clause}
                ORDER BY e.created_at DESC
            """
            
            count_query = f"""
                SELECT COUNT(*) 
                FROM events e
                {where_clause}
            """
            
            result = paginate_query(conn, base_query, count_query, params, pagination_params)
            return jsonify(result)
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/events/<int:event_id>")
@require_admin
def get_event_details_for_admin(event_id):
    """
    Get FULL event details for admin, bypassing privacy settings.
    Fixed: Removed 'created_at' fields from participants and applications
    as they don't exist in the database schema.
    """
    try:
        with current_app.engine.connect() as conn:
            # 1. Etkinlik Temel Bilgileri
            event = conn.execute(text("""
                SELECT 
                    e.id,
                    e.title,
                    e.explanation,
                    e.price,
                    e.starts_at,
                    e.ends_at,
                    e.location_name,
                    e.status,
                    e.user_limit,
                    e.photo_url,
                    e.created_at,
                    e.updated_at,
                    e.owner_type,
                    e.is_participants_private,
                    e.only_girls,
                    et.code AS event_type,
                    COALESCE(o.name, u.username) as owner_name,
                    u.email as owner_email
                    e.review_reason,
                    e.review_flags,
                    e.review_source

                FROM events e
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN event_types et ON e.type_id = et.id
                WHERE e.id = :id
            """), {"id": event_id}).fetchone()

            if not event:
                return {"error": "Event not found"}, 404

            # 2. Katılımcılar
            # DÜZELTME: p.created_at kaldırıldı. init.sql'de yok.
            participants = conn.execute(text("""
                SELECT 
                    p.id,
                    p.user_id,
                    u.username,
                    u.name,
                    u.email,
                    p.status,
                    p.ticket_code
                FROM participants p
                JOIN users u ON u.id = p.user_id
                WHERE p.event_id = :id
            """), {"id": event_id}).fetchall()

            # 3. Başvurular
            # DÜZELTME: a.created_at kaldırıldı. init.sql'de yok.
            applications = conn.execute(text("""
                SELECT 
                    a.id,
                    u.username,
                    a.why_me,
                    a.status
                FROM applications a
                JOIN users u ON a.user_id = u.id
                WHERE a.event_id = :id
            """), {"id": event_id}).fetchall()

            # 4. Raporlar
            # Reports tablosunda created_at VAR. Sorun yok.
            reports = conn.execute(text("""
                SELECT 
                    r.id,
                    u.username as reporter,
                    r.reason,
                    r.status,
                    r.created_at
                FROM reports r
                JOIN users u ON r.reporter_user_id = u.id
                WHERE r.event_id = :id
            """), {"id": event_id}).fetchall()

            # Response Oluşturma
            data = dict(event._mapping)
            data["participants"] = [dict(p._mapping) for p in participants]
            data["applications"] = [dict(a._mapping) for a in applications]
            data["reports"] = [dict(r._mapping) for r in reports]

            return jsonify(data)

    except Exception as e:
        return {"error": str(e)}, 503

@admin_bp.delete("/events/<int:event_id>")
@require_admin
def delete_event(event_id):
    """
    Delete an event (cascade deletes participants, applications, ratings).
    """
    try:
        with current_app.engine.connect() as conn:
            # Check if event exists
            event = conn.execute(
                text("SELECT id FROM events WHERE id = :id"),
                {"id": event_id}
            ).fetchone()
            
            if not event:
                return {"error": "Event not found"}, 404
            
            # Delete event (cascade will handle related records)
            conn.execute(
                text("DELETE FROM events WHERE id = :id"),
                {"id": event_id}
            )
            conn.commit()
        
        return {"message": "Event deleted successfully"}, 200
    
    except Exception as e:
        return {"error": str(e)}, 503


# =============================================
# USERS MANAGEMENT
# =============================================

@admin_bp.get("/users")
@require_admin
def get_all_users():
    """
    Get all users with statistics.
    Supports pagination and filtering.
    Query params: ?page=1&per_page=20&is_blocked=false
    """
    try:
        is_blocked = request.args.get("is_blocked")
        pagination_params = get_pagination_params()
        
        with current_app.engine.connect() as conn:
            where_clause = ""
            params = {}
            
            if is_blocked is not None:
                where_clause = "WHERE u.is_blocked = :is_blocked"
                params["is_blocked"] = is_blocked.lower() == 'true'
            
            base_query = f"""
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    u.username,
                    u.role,
                    u.is_blocked,
                    u.created_at,
                    (
                        SELECT COUNT(*) FROM participants p
                        WHERE p.user_id = u.id AND p.status = 'ATTENDED'
                    ) AS events_attended
                FROM users u
                {where_clause}
                ORDER BY u.created_at DESC
            """
            
            count_query = f"""
                SELECT COUNT(*) 
                FROM users u
                {where_clause}
            """
            
            result = paginate_query(conn, base_query, count_query, params, pagination_params)
            return jsonify(result)
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/users/<int:user_id>")
@require_admin
def get_user_details(user_id):
    """
    Get full profile details of a specific user for admin.
    """
    try:
        with current_app.engine.connect() as conn:
            # Kullanıcı detaylarını çek (Üniversite adı ile birlikte)
            user = conn.execute(
                text("""
                    SELECT 
                        u.id,
                        u.name,
                        u.username,
                        u.email,
                        u.role,
                        u.gender,
                        u.photo_url,
                        u.is_blocked,
                        u.created_at,
                        uni.name as university_name,
                        (
                            SELECT COUNT(*) FROM participants p 
                            WHERE p.user_id = u.id AND p.status = 'ATTENDED'
                        ) as total_attendance,
                        (
                            SELECT COUNT(*) FROM events e 
                            WHERE e.owner_user_id = u.id
                        ) as events_created
                    FROM users u
                    LEFT JOIN universities uni ON u.university_id = uni.id
                    WHERE u.id = :uid
                """),
                {"uid": user_id}
            ).fetchone()
            
            if not user:
                return {"error": "User not found"}, 404
            
            return jsonify(dict(user._mapping))
    
    except Exception as e:
        return {"error": str(e)}, 503

@admin_bp.get("/users/<int:user_id>/events")
@require_admin
def get_user_events(user_id):
    """
    Get events created and attended by a specific user.
    """
    try:
        with current_app.engine.connect() as conn:
            # Check if user exists
            user = conn.execute(
                text("SELECT id, name, username FROM users WHERE id = :id"),
                {"id": user_id}
            ).fetchone()
            
            if not user:
                return {"error": "User not found"}, 404
            
            # Events created by user
            created_events = conn.execute(text("""
                SELECT 
                    e.id,
                    e.title,
                    e.starts_at,
                    e.status,
                    e.owner_type
                FROM events e
                WHERE e.owner_user_id = :uid
                ORDER BY e.starts_at DESC
            """), {"uid": user_id}).fetchall()
            
            # Events attended by user
            attended_events = conn.execute(text("""
                SELECT 
                    e.id,
                    e.title,
                    e.starts_at,
                    p.status as participation_status
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE p.user_id = :uid
                ORDER BY e.starts_at DESC
            """), {"uid": user_id}).fetchall()
            
            return jsonify({
                "user": dict(user._mapping),
                "created_events": [dict(e._mapping) for e in created_events],
                "attended_events": [dict(e._mapping) for e in attended_events]
            })
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.put("/users/<int:user_id>/block")
@require_admin
def block_user(user_id):
    """
    Block or unblock a user.
    Body: {"is_blocked": true}
    """
    try:
        data = request.get_json()
        is_blocked = data.get("is_blocked")
        
        if is_blocked is None:
            return {"error": "is_blocked field is required"}, 400
        
        with current_app.engine.connect() as conn:
            # Check if user exists
            user = conn.execute(
                text("SELECT id, role FROM users WHERE id = :id"),
                {"id": user_id}
            ).fetchone()
            
            if not user:
                return {"error": "User not found"}, 404
            
            # Don't allow blocking other admins
            if user.role == 'ADMIN':
                return {"error": "Cannot block admin users"}, 403
            
            # Update block status
            conn.execute(
                text("UPDATE users SET is_blocked = :is_blocked WHERE id = :id"),
                {"is_blocked": is_blocked, "id": user_id}
            )
            conn.commit()
        
        action = "blocked" if is_blocked else "unblocked"
        return {"message": f"User {action} successfully"}, 200
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.delete("/users/<int:user_id>")
@require_admin
def delete_user(user_id):
    """
    Delete a user from the system.
    """
    try:
        with current_app.engine.connect() as conn:
            # Check if user exists
            user = conn.execute(
                text("SELECT id, role FROM users WHERE id = :id"),
                {"id": user_id}
            ).fetchone()
            
            if not user:
                return {"error": "User not found"}, 404
            
            # Don't allow deleting other admins
            if user.role == 'ADMIN':
                return {"error": "Cannot delete admin users"}, 403
            
            # Delete user
            conn.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": user_id}
            )
            conn.commit()
        
        return {"message": "User deleted successfully"}, 200
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/users/most-active")
@require_admin
def get_most_active_users():
    """
    Get most active users (by event attendance).
    Query params: ?limit=10
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        
        with current_app.engine.connect() as conn:
            users = conn.execute(text("""
                SELECT 
                    u.id,
                    u.name,
                    u.username,
                    COUNT(p.id) as events_attended,
                    MAX(e.starts_at) as last_event_date,
                    (
                        SELECT e2.title 
                        FROM participants p2
                        JOIN events e2 ON p2.event_id = e2.id
                        WHERE p2.user_id = u.id
                        ORDER BY e2.starts_at DESC
                        LIMIT 1
                    ) as last_event_title
                FROM users u
                LEFT JOIN participants p ON u.id = p.user_id AND p.status = 'ATTENDED'
                LEFT JOIN events e ON p.event_id = e.id
                GROUP BY u.id, u.name, u.username
                HAVING events_attended > 0
                ORDER BY events_attended DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            return jsonify({
                "data": [
                    {
                        "id": user.id,
                        "name": user.name,
                        "username": user.username,
                        "events_attended": user.events_attended,
                        "last_event": {
                            "title": user.last_event_title,
                            "date": user.last_event_date.strftime('%Y-%m-%d') if user.last_event_date else None
                        } if user.last_event_title else None
                    }
                    for user in users
                ]
            })
    
    except Exception as e:
        return {"error": str(e)}, 503


# =============================================
# CLUBS MANAGEMENT
# =============================================

@admin_bp.get("/clubs")
@require_admin
def get_all_clubs():
    """
    Get all clubs/organizations with statistics.
    Supports pagination.
    """
    try:
        pagination_params = get_pagination_params()
        
        with current_app.engine.connect() as conn:
            base_query = """
                SELECT 
                    o.id,
                    o.name,
                    o.description,
                    o.status,
                    o.created_at,
                    u.username as admin_username,
                    (
                        SELECT COUNT(*) FROM organization_members m
                        WHERE m.organization_id = o.id
                    ) AS member_count,
                    (
                        SELECT COUNT(*) FROM events e
                        WHERE e.owner_organization_id = o.id
                    ) AS event_count
                FROM organizations o
                LEFT JOIN users u ON o.owner_user_id = u.id
                ORDER BY o.created_at DESC
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM organizations o
            """
            
            result = paginate_query(conn, base_query, count_query, {}, pagination_params)
            return jsonify(result)
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/clubs/<int:club_id>")
@require_admin
def get_club_details(club_id):
    """
    Get FULL club details for admin.
    Includes:
    - Basic Info & Stats
    - Owner Contact Info (Email, Name)
    - Full Member List (with emails)
    - Events List
    """
    try:
        with current_app.engine.connect() as conn:
            # 1. Kulüp ve Sahip Detayları
            club = conn.execute(text("""
                SELECT 
                    o.id,
                    o.name,
                    o.description,
                    o.status,
                    o.photo_url,
                    o.created_at,
                    o.updated_at,
                    o.owner_user_id,
                    u.username AS owner_username,
                    u.name AS owner_name,
                    u.email AS owner_email,  -- Admin için önemli: İletişim
                    (
                        SELECT COUNT(*) FROM organization_members m 
                        WHERE m.organization_id = o.id
                    ) as member_count,
                    (
                        SELECT COUNT(*) FROM events e 
                        WHERE e.owner_organization_id = o.id
                    ) as event_count
                FROM organizations o
                LEFT JOIN users u ON o.owner_user_id = u.id
                WHERE o.id = :id
            """), {"id": club_id}).fetchone()

            if not club:
                return {"error": "Club not found"}, 404

            # 2. Üyeler (Detaylı - Email dahil)
            members = conn.execute(text("""
                SELECT 
                    m.user_id,
                    u.username,
                    u.name,
                    u.email,
                    u.photo_url,
                    m.role,
                    m.joined_at
                FROM organization_members m
                JOIN users u ON m.user_id = u.id
                WHERE m.organization_id = :id
                ORDER BY m.role ASC, m.joined_at DESC
            """), {"id": club_id}).fetchall()

            # 3. Kulübün Etkinlikleri
            events = conn.execute(text("""
                SELECT 
                    e.id,
                    e.title,
                    e.status,
                    e.starts_at,
                    e.created_at,
                    (SELECT COUNT(*) FROM participants p WHERE p.event_id = e.id) as participant_count
                FROM events e
                WHERE e.owner_organization_id = :id
                ORDER BY e.starts_at DESC
            """), {"id": club_id}).fetchall()

            # 4. Kulüp Hakkındaki Raporlar
            reports = conn.execute(text("""
                SELECT 
                    r.id,
                    u.username as reporter,
                    r.reason,
                    r.status,
                    r.is_reviewed,
                    r.admin_notes,
                    r.created_at
                FROM reports r
                JOIN users u ON r.reporter_user_id = u.id
                WHERE r.organization_id = :id
                ORDER BY r.created_at DESC
            """), {"id": club_id}).fetchall()
            
            # Response Hazırlama
            data = dict(club._mapping)
            data["members"] = [dict(m._mapping) for m in members]
            data["events"] = [dict(e._mapping) for e in events]
            data["reports"] = [dict(r._mapping) for r in reports]

            return jsonify(data)

    except Exception as e:
        return {"error": str(e)}, 503

@admin_bp.get("/clubs/stats")
@require_admin
def get_clubs_stats():
    """
    Get overall clubs statistics.
    """
    try:
        with current_app.engine.connect() as conn:
            # Total clubs
            total_clubs = conn.execute(
                text("SELECT COUNT(*) FROM organizations")
            ).scalar()
            
            # Total members (may have duplicates across clubs)
            total_members = conn.execute(
                text("SELECT COUNT(*) FROM organization_members")
            ).scalar()
            
            # Total events by clubs
            total_events = conn.execute(
                text("SELECT COUNT(*) FROM events WHERE owner_type = 'ORGANIZATION'")
            ).scalar()
            
            return jsonify({
                "total_clubs": total_clubs,
                "total_members": total_members,
                "total_events": total_events
            })
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.put("/clubs/<int:club_id>/status")
@require_admin
def update_club_status(club_id):
    """
    Update club status (ACTIVE, INACTIVE).
    Body: {"status": "INACTIVE"}
    """
    try:
        data = request.get_json()
        new_status = data.get("status", "").upper()
        
        if new_status not in ["ACTIVE", "INACTIVE"]:
            return {"error": "Invalid status. Must be ACTIVE or INACTIVE"}, 400
        
        with current_app.engine.connect() as conn:
            # Check if club exists
            club = conn.execute(
                text("SELECT id FROM organizations WHERE id = :id"),
                {"id": club_id}
            ).fetchone()
            
            if not club:
                return {"error": "Club not found"}, 404
            
            # Update status
            conn.execute(
                text("UPDATE organizations SET status = :status, updated_at = NOW() WHERE id = :id"),
                {"status": new_status, "id": club_id}
            )
            conn.commit()
        
        return {"message": f"Club status updated to {new_status}"}, 200
    
    except Exception as e:
        return {"error": str(e)}, 503

@admin_bp.delete("/clubs/<int:club_id>")
@require_admin
def delete_club(club_id):
    """
    Delete a club/organization permanently.
    Admin only.
    """
    try:
        with current_app.engine.connect() as conn:
            # 1. Kulüp var mı kontrol et
            club = conn.execute(
                text("SELECT id FROM organizations WHERE id = :id"),
                {"id": club_id}
            ).fetchone()
            
            if not club:
                return {"error": "Club not found"}, 404
            
            # 2. Kulübü sil
            # Not: init.sql'deki ayarlara göre:
            # - Üyeler (organization_members) -> OTOMATİK SİLİNİR (ON DELETE CASCADE)
            # - Başvurular (organization_applications) -> OTOMATİK SİLİNİR (ON DELETE CASCADE)
            # - Etkinlikler (events) -> SİLİNMEZ, owner_organization_id NULL olur (ON DELETE SET NULL)
            conn.execute(
                text("DELETE FROM organizations WHERE id = :id"),
                {"id": club_id}
            )
            conn.commit()
        
        return {"message": "Club deleted successfully"}, 200
    
    except Exception as e:
        return {"error": str(e)}, 503
# =============================================
# ATTENDANCE MANAGEMENT
# =============================================

@admin_bp.get("/attendance/stats")
@require_admin
def get_attendance_stats():
    """
    Get attendance statistics including weekly scans chart.
    """
    try:
        with current_app.engine.connect() as conn:
            # Total QR scans (all ATTENDED)
            total_scans = conn.execute(
                text("SELECT COUNT(*) FROM participants WHERE status='ATTENDED'")
            ).scalar()
            
            # Unique attendees
            unique_attendees = conn.execute(
                text("SELECT COUNT(DISTINCT user_id) FROM participants WHERE status='ATTENDED'")
            ).scalar()
            
            # Average attendance per event
            avg_attendance = conn.execute(text("""
                SELECT AVG(attendance_count) as avg_attendance
                FROM (
                    SELECT event_id, COUNT(*) as attendance_count
                    FROM participants
                    WHERE status = 'ATTENDED'
                    GROUP BY event_id
                ) as event_attendance
            """)).fetchone()
            
            # Weekly scans (last 7 days)
            weekly_scans = conn.execute(text("""
                SELECT 
                    DATE(e.starts_at) as date,
                    COUNT(p.id) as count
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    AND p.status = 'ATTENDED'
                GROUP BY DATE(e.starts_at)
                ORDER BY date ASC
            """)).fetchall()
            
            return jsonify({
                "total_scans": total_scans,
                "unique_attendees": unique_attendees,
                "average_attendance": float(avg_attendance.avg_attendance) if avg_attendance.avg_attendance else 0,
                "weekly_scans": [
                    {"date": row.date.strftime('%Y-%m-%d'), "count": row.count}
                    for row in weekly_scans
                ]
            })
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/attendance/top-events")
@require_admin
def get_top_attendance_events():
    """
    Get events with highest attendance rates.
    Query params: ?limit=10
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        
        with current_app.engine.connect() as conn:
            events = conn.execute(text("""
                SELECT 
                    e.id as event_id,
                    e.title as event_name,
                    e.user_limit as capacity,
                    COUNT(p.id) as attendance,
                    CASE 
                        WHEN e.user_limit IS NOT NULL AND e.user_limit > 0 
                        THEN (COUNT(p.id) * 100.0 / e.user_limit)
                        ELSE 100.0
                    END as percentage
                FROM events e
                LEFT JOIN participants p ON e.id = p.event_id AND p.status = 'ATTENDED'
                WHERE e.status = 'COMPLETED'
                GROUP BY e.id, e.title, e.user_limit
                HAVING attendance > 0
                ORDER BY percentage DESC, attendance DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            return jsonify({
                "data": [
                    {
                        "event_id": event.event_id,
                        "event_name": event.event_name,
                        "attendance": event.attendance,
                        "capacity": event.capacity,
                        "percentage": round(float(event.percentage), 2)
                    }
                    for event in events
                ]
            })
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/attendance/charts")
@require_admin
def get_attendance_charts():
    """
    Get attendance statistics for charts.
    Returns:
    - weekly: Last 7 days (Daily breakdown)
    - monthly: Last 1 month (Daily breakdown)
    - six_months: Last 6 months (Monthly breakdown)
    - yearly: Last 12 months (Monthly breakdown)
    """
    try:
        with current_app.engine.connect() as conn:
            # 1. Haftalık (Son 7 Gün - Gün Bazlı)
            weekly = conn.execute(text("""
                SELECT 
                    DATE_FORMAT(e.starts_at, '%Y-%m-%d') as date, 
                    COUNT(p.id) as count
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND p.status = 'ATTENDED'
                GROUP BY date 
                ORDER BY date ASC
            """)).fetchall()

            # 2. Aylık (Son 1 Ay - Gün Bazlı)
            monthly = conn.execute(text("""
                SELECT 
                    DATE_FORMAT(e.starts_at, '%Y-%m-%d') as date, 
                    COUNT(p.id) as count
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
                  AND p.status = 'ATTENDED'
                GROUP BY date 
                ORDER BY date ASC
            """)).fetchall()

            # 3. 6 Aylık (Son 6 Ay - Ay Bazlı)
            six_months = conn.execute(text("""
                SELECT 
                    DATE_FORMAT(e.starts_at, '%Y-%m') as date, 
                    COUNT(p.id) as count
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                  AND p.status = 'ATTENDED'
                GROUP BY date 
                ORDER BY date ASC
            """)).fetchall()

            # 4. Yıllık (Son 12 Ay - Ay Bazlı)
            yearly = conn.execute(text("""
                SELECT 
                    DATE_FORMAT(e.starts_at, '%Y-%m') as date, 
                    COUNT(p.id) as count
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                  AND p.status = 'ATTENDED'
                GROUP BY date 
                ORDER BY date ASC
            """)).fetchall()

            return jsonify({
                "weekly": [{"date": row.date, "count": row.count} for row in weekly],
                "monthly": [{"date": row.date, "count": row.count} for row in monthly],
                "six_months": [{"date": row.date, "count": row.count} for row in six_months],
                "yearly": [{"date": row.date, "count": row.count} for row in yearly]
            })

    except Exception as e:
        return {"error": str(e)}, 503

# =============================================
# REPORTS MANAGEMENT
# =============================================

@admin_bp.get("/reports")
@require_admin
def get_all_reports():
    """
    Get reports filtered by review status and type.
    Query params: 
      - ?page=1&per_page=20
      - ?status=REVIEWED    -> Returns is_reviewed = TRUE
      - ?status=UNREVIEWED  -> Returns is_reviewed = FALSE
      - ?type=EVENT         -> Returns only event reports
      - ?type=ORGANIZATION  -> Returns only organization reports
      - (No status/type)    -> Returns ALL
    """
    try:
        # Frontend 'status' parametresi ile 'REVIEWED' veya 'UNREVIEWED' gönderecek
        status_filter = request.args.get("status", "").upper()
        type_filter = request.args.get("type", "").upper()
        pagination_params = get_pagination_params()
        
        with current_app.engine.connect() as conn:
            where_clauses = []
            params = {}
            
            # Filtreleme Mantığı: is_reviewed sütununa bakıyoruz
            if status_filter == "REVIEWED":
                where_clauses.append("r.is_reviewed = TRUE")
            elif status_filter == "UNREVIEWED":
                where_clauses.append("r.is_reviewed = FALSE")
            
            # Report type filtresi
            if type_filter == "EVENT":
                where_clauses.append("r.event_id IS NOT NULL")
            elif type_filter == "ORGANIZATION":
                where_clauses.append("r.organization_id IS NOT NULL")
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            base_query = f"""
                SELECT 
                    r.id,
                    r.event_id,
                    r.organization_id,
                    CASE 
                        WHEN r.event_id IS NOT NULL THEN 'EVENT'
                        WHEN r.organization_id IS NOT NULL THEN 'ORGANIZATION'
                    END as report_type,
                    CASE 
                        WHEN r.event_id IS NOT NULL THEN e.title
                        WHEN r.organization_id IS NOT NULL THEN org.name
                    END as target_name,
                    CASE 
                        WHEN r.event_id IS NOT NULL THEN e.owner_type
                        WHEN r.organization_id IS NOT NULL THEN 'ORGANIZATION'
                    END as target_owner_type,
                    CASE 
                        WHEN r.event_id IS NOT NULL THEN COALESCE(o.name, u_owner.username)
                        WHEN r.organization_id IS NOT NULL THEN u_org_owner.username
                    END as target_owner,
                    u_reporter.username as reporter_username,
                    r.reason,
                    r.status AS decision,
                    r.is_reviewed,
                    r.admin_notes,
                    r.created_at,
                    r.updated_at
                FROM reports r
                LEFT JOIN events e ON r.event_id = e.id
                LEFT JOIN organizations org ON r.organization_id = org.id
                JOIN users u_reporter ON r.reporter_user_id = u_reporter.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN users u_owner ON e.owner_user_id = u_owner.id
                LEFT JOIN users u_org_owner ON org.owner_user_id = u_org_owner.id
                {where_clause}
                ORDER BY r.is_reviewed ASC, r.created_at DESC
            """
            
            count_query = f"""
                SELECT COUNT(*) 
                FROM reports r
                {where_clause}
            """
            
            result = paginate_query(conn, base_query, count_query, params, pagination_params)
            return jsonify(result)
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.get("/reports/stats")
@require_admin
def get_reports_stats():
    """
    Get comprehensive report statistics.
    Returns: total, reviewed, unreviewed, and breakdown by type.
    """
    try:
        with current_app.engine.connect() as conn:
            # 1. Toplam Rapor Sayısı
            total_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports")
            ).scalar()
            
            # 2. İncelenmiş (Reviewed) Sayısı
            reviewed_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE is_reviewed = TRUE")
            ).scalar()
            
            # 3. İncelenmemiş (Unreviewed) Sayısı
            unreviewed_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE is_reviewed = FALSE")
            ).scalar()
            
            # 4. Event Reports
            event_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE event_id IS NOT NULL")
            ).scalar()
            
            # 5. Organization Reports
            organization_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE organization_id IS NOT NULL")
            ).scalar()
            
            return jsonify({
                "total_reports": total_reports,
                "reviewed_reports": reviewed_reports,
                "unreviewed_reports": unreviewed_reports,
                "event_reports": event_reports,
                "organization_reports": organization_reports
            })
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.put("/reports/<int:report_id>/status")
@require_admin
def update_report_status(report_id):
    """
    Update report status and add admin notes.
    Body: {"status": "ACCEPTED", "admin_notes": "Event removed"}
    """
    try:
        data = request.get_json()
        new_status = data.get("status", "").upper()
        admin_notes = data.get("admin_notes", "")
        
        if new_status not in ["PENDING", "ACCEPTED", "REJECTED"]:
            return {"error": "Invalid status. Must be PENDING, ACCEPTED, or REJECTED"}, 400
        
        with current_app.engine.connect() as conn:
            # Check if report exists
            report = conn.execute(
                text("SELECT id FROM reports WHERE id = :id"),
                {"id": report_id}
            ).fetchone()
            
            if not report:
                return {"error": "Report not found"}, 404
            
            # Update report
            conn.execute(
                text("""
                    UPDATE reports 
                    SET status = :status, 
                        admin_notes = :notes,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"status": new_status, "notes": admin_notes, "id": report_id}
            )
            conn.commit()
        
        return {"message": f"Report status updated to {new_status}"}, 200
    
    except Exception as e:
        return {"error": str(e)}, 503


@admin_bp.put("/reports/<int:report_id>/review")
@require_admin
def mark_report_reviewed(report_id):
    """
    Mark a report as reviewed or unreviewed.
    Body: {"is_reviewed": true}
    """
    try:
        data = request.get_json()
        is_reviewed = data.get("is_reviewed", True)
        
        # Validate boolean
        if not isinstance(is_reviewed, bool):
            return {"error": "is_reviewed must be a boolean"}, 400
        
        with current_app.engine.connect() as conn:
            # Check if report exists
            report = conn.execute(
                text("SELECT id FROM reports WHERE id = :id"),
                {"id": report_id}
            ).fetchone()
            
            if not report:
                return {"error": "Report not found"}, 404
            
            # Update review status
            conn.execute(
                text("""
                    UPDATE reports 
                    SET is_reviewed = :is_reviewed,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"is_reviewed": is_reviewed, "id": report_id}
            )
            conn.commit()
        
        status_text = "reviewed" if is_reviewed else "unreviewed"
        return {"message": f"Report marked as {status_text}"}, 200
    
    except Exception as e:
        return {"error": str(e)}, 503
@admin_bp.put("/events/<int:event_id>/review")
@require_admin
def review_event(event_id):
    """
    Approve or reject an event that is pending AI review.

    Body:
    {
      "status": "APPROVED" | "REJECTED",
      "admin_note": "Optional explanation"
    }
    """
    try:
        # JWT doğrula (require_admin sadece yetki kontrolü yapıyor)
        from backend.utils.auth_utils import verify_jwt
        admin_user_id = verify_jwt()

        data = request.get_json()
        decision = data.get("status")
        admin_note = data.get("admin_note")

        if decision not in ["APPROVED", "REJECTED"]:
            return {"error": "status must be APPROVED or REJECTED"}, 400

        with current_app.engine.connect() as conn:
            event = conn.execute(
                text("""
                    SELECT status
                    FROM events
                    WHERE id = :id
                """),
                {"id": event_id}
            ).fetchone()

            if not event:
                return {"error": "Event not found"}, 404

            if event.status != "PENDING_REVIEW":
                return {"error": "Event is not pending review"}, 409

            new_status = "FUTURE" if decision == "APPROVED" else "REJECTED"

            conn.execute(
                text("""
                    UPDATE events
                    SET
                        status = :status,
                        admin_note = :admin_note,
                        reviewed_by = :admin_id,
                        reviewed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "status": new_status,
                    "admin_note": admin_note,
                    "admin_id": admin_user_id,
                    "id": event_id
                }
            )

            conn.commit()

        return {
            "message": f"Event {decision.lower()} successfully",
            "event_id": event_id,
            "new_status": new_status
        }, 200

    except Exception as e:
        return {"error": str(e)}, 503
