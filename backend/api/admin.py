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

@admin_bp.get("/overview")
@require_admin
def get_overview():
    """
    Get overview dashboard statistics and charts.
    Returns: total events, users, clubs, pending events, active events,
    attendance, monthly charts for events and attendance.
    """
    try:
        with current_app.engine.connect() as conn:
            # Total events
            total_events = conn.execute(
                text("SELECT COUNT(*) FROM events")
            ).scalar()
            
            # Total users
            total_users = conn.execute(
                text("SELECT COUNT(*) FROM users")
            ).scalar()
            
            # Active clubs
            active_clubs = conn.execute(
                text("SELECT COUNT(*) FROM organizations WHERE status='ACTIVE'")
            ).scalar()
            
            # Pending events
            pending_events = conn.execute(
                text("SELECT COUNT(*) FROM events WHERE status='PENDING'")
            ).scalar()
            
            # Active events (FUTURE status)
            active_events = conn.execute(
                text("SELECT COUNT(*) FROM events WHERE status='FUTURE'")
            ).scalar()
            
            # Total attendance (ATTENDED status)
            total_attendance = conn.execute(
                text("SELECT COUNT(*) FROM participants WHERE status='ATTENDED'")
            ).scalar()
            
            # Pending reports
            pending_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE status='PENDING'")
            ).scalar()
            
            # Unreviewed reports
            unreviewed_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE is_reviewed = FALSE")
            ).scalar()
            
            # Monthly events chart (last 6 months)
            monthly_events = conn.execute(text("""
                SELECT 
                    DATE_FORMAT(created_at, '%Y-%m') as month,
                    COUNT(*) as count
                FROM events
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                GROUP BY month
                ORDER BY month ASC
            """)).fetchall()
            
            # Monthly attendance chart (last 6 months)
            monthly_attendance = conn.execute(text("""
                SELECT 
                    DATE_FORMAT(e.starts_at, '%Y-%m') as month,
                    COUNT(p.id) as count
                FROM participants p
                JOIN events e ON p.event_id = e.id
                WHERE e.starts_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                    AND p.status = 'ATTENDED'
                GROUP BY month
                ORDER BY month ASC
            """)).fetchall()
            
            return jsonify({
                "total_events": total_events,
                "total_users": total_users,
                "active_clubs": active_clubs,
                "pending_events": pending_events,
                "active_events": active_events,
                "total_attendance": total_attendance,
                "pending_reports": pending_reports,
                "unreviewed_reports": unreviewed_reports,
                "monthly_events_chart": [
                    {"month": row.month, "count": row.count} 
                    for row in monthly_events
                ],
                "monthly_attendance_chart": [
                    {"month": row.month, "count": row.count} 
                    for row in monthly_attendance
                ]
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


@admin_bp.put("/events/<int:event_id>/status")
@require_admin
def update_event_status(event_id):
    """
    Update event status (PENDING, FUTURE, COMPLETED, REJECTED).
    Body: {"status": "FUTURE"}
    """
    try:
        data = request.get_json()
        new_status = data.get("status", "").upper()
        
        if new_status not in ["PENDING", "FUTURE", "COMPLETED", "REJECTED"]:
            return {"error": "Invalid status. Must be PENDING, FUTURE, COMPLETED, or REJECTED"}, 400
        
        with current_app.engine.connect() as conn:
            # Check if event exists
            event = conn.execute(
                text("SELECT id FROM events WHERE id = :id"),
                {"id": event_id}
            ).fetchone()
            
            if not event:
                return {"error": "Event not found"}, 404
            
            # Update status
            conn.execute(
                text("UPDATE events SET status = :status, updated_at = NOW() WHERE id = :id"),
                {"status": new_status, "id": event_id}
            )
            conn.commit()
        
        return {"message": f"Event status updated to {new_status}"}, 200
    
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


# =============================================
# REPORTS MANAGEMENT
# =============================================

@admin_bp.get("/reports")
@require_admin
def get_all_reports():
    """
    Get all reports with event and user details.
    Supports pagination and filtering by status and is_reviewed.
    Query params: 
      - ?page=1&per_page=20
      - ?status=PENDING
      - ?is_reviewed=false (show only unreviewed)
      - ?is_reviewed=true (show only reviewed)
    """
    try:
        status_filter = request.args.get("status")
        is_reviewed_filter = request.args.get("is_reviewed")
        pagination_params = get_pagination_params()
        
        with current_app.engine.connect() as conn:
            where_clauses = []
            params = {}
            
            if status_filter:
                where_clauses.append("r.status = :status")
                params["status"] = status_filter.upper()
            
            if is_reviewed_filter is not None:
                # Convert string to boolean
                is_reviewed = is_reviewed_filter.lower() in ['true', '1', 'yes']
                where_clauses.append("r.is_reviewed = :is_reviewed")
                params["is_reviewed"] = is_reviewed
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            base_query = f"""
                SELECT 
                    r.id,
                    r.event_id,
                    e.title as event_title,
                    e.owner_type,
                    COALESCE(o.name, u_owner.username) as event_owner,
                    u_reporter.username as reporter_username,
                    r.reason,
                    r.status,
                    r.is_reviewed,
                    r.admin_notes,
                    r.created_at
                FROM reports r
                JOIN events e ON r.event_id = e.id
                JOIN users u_reporter ON r.reporter_user_id = u_reporter.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN users u_owner ON e.owner_user_id = u_owner.id
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
    Get reports statistics including review status.
    """
    try:
        with current_app.engine.connect() as conn:
            # Total reports
            total_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports")
            ).scalar()
            
            # Pending reports
            pending_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE status='PENDING'")
            ).scalar()
            
            # Accepted reports
            accepted_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE status='ACCEPTED'")
            ).scalar()
            
            # Rejected reports
            rejected_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE status='REJECTED'")
            ).scalar()
            
            # Unreviewed reports
            unreviewed_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE is_reviewed = FALSE")
            ).scalar()
            
            # Reviewed reports
            reviewed_reports = conn.execute(
                text("SELECT COUNT(*) FROM reports WHERE is_reviewed = TRUE")
            ).scalar()
            
            return jsonify({
                "total_reports": total_reports,
                "pending_reports": pending_reports,
                "accepted_reports": accepted_reports,
                "rejected_reports": rejected_reports,
                "unreviewed_reports": unreviewed_reports,
                "reviewed_reports": reviewed_reports
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

