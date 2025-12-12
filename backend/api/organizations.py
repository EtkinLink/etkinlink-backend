from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from utils.auth_utils import verify_jwt, check_organization_permission, check_organization_ownership, AuthError
from utils.pagination import paginate_query
from utils.notification_service import notify_org_approved, notify_org_rejected
from datetime import datetime
import jwt

organization_bp = Blueprint('organizations', __name__, url_prefix='/organizations')

@organization_bp.get("/<int:org_id>")
def get_organization_by_id(org_id):
    """Get organization details with members and related events."""
    try:
        with current_app.engine.connect() as conn:
            org = conn.execute(text("""
                SELECT
                    o.id,
                    o.name,
                    o.description,
                    o.status,
                    o.photo_url,
                    o.created_at,
                    o.updated_at,
                    u.username AS owner_username
                FROM organizations o
                LEFT JOIN users u ON o.owner_user_id = u.id
                WHERE o.id = :id AND o.status = 'ACTIVE'
            """), {"id": org_id}).fetchone()

            if not org:
                return {"error": "Organization not found"}, 404

            members = conn.execute(text("""
                SELECT
                    u.id,
                    u.username,
                    m.role,
                    m.joined_at
                FROM organization_members m
                JOIN users u ON m.user_id = u.id
                WHERE m.organization_id = :id
            """), {"id": org_id}).fetchall()

            events = conn.execute(text("""
                SELECT
                    e.id,
                    e.title,
                    e.starts_at,
                    e.ends_at,
                    e.status,
                    et.code AS event_type
                FROM events e
                LEFT JOIN event_types et ON e.type_id = et.id
                WHERE e.owner_organization_id = :id
                ORDER BY e.starts_at DESC
            """), {"id": org_id}).fetchall()

        data = dict(org._mapping)
        data["members"] = [dict(m._mapping) for m in members]
        data["events"] = [dict(ev._mapping) for ev in events]

        return jsonify(data)
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.post("/")
def create_organization():
    try:
        user_id = verify_jwt()

        data = request.get_json()
        if not data or "name" not in data:
            return {"error": "Organization name is required"}, 400

        with current_app.engine.begin() as conn:  # <-- auto-commit / auto-rollback
            exists = conn.execute(
                text("SELECT id FROM organizations WHERE name = :n"),
                {"n": data["name"]}
            ).fetchone()
            if exists:
                return {"error": "Organization name already exists"}, 409

            res = conn.execute(text("""
                INSERT INTO organizations (name, description, owner_user_id, photo_url, status, created_at, updated_at)
                VALUES (:name, :description, :owner_user_id, :photo_url, 'ACTIVE', NOW(), NOW())
            """), {
                "name": data["name"],
                "description": data.get("description"),
                "owner_user_id": user_id,
                "photo_url": data.get("photo_url")
            })

            new_org_id = res.lastrowid  # <-- LAST_INSERT_ID yerine bu daha güvenli

            conn.execute(text("""
                INSERT INTO organization_members (organization_id, user_id, role, joined_at)
                VALUES (:oid, :uid, 'ADMIN', NOW())
            """), {"oid": new_org_id, "uid": user_id})

        return {"message": "Organization created successfully"}, 201

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503



@organization_bp.post("/<int:org_id>/apply")
def apply_to_organization(org_id):
    """User applies to join an organization."""
    try:
        user_id = verify_jwt()

        data = request.get_json()
        motivation = data.get("motivation", "")

        with current_app.engine.connect() as conn:
            # Check if already a member or applied
            existing = conn.execute(text("""
                SELECT 1 FROM organization_members WHERE organization_id = :oid AND user_id = :uid
                UNION
                SELECT 1 FROM organization_applications WHERE organization_id = :oid AND user_id = :uid
            """), {"oid": org_id, "uid": user_id}).fetchone()

            if existing:
                return {"error": "Already applied or already a member"}, 409

            conn.execute(text("""
                INSERT INTO organization_applications (organization_id, user_id, motivation, status, created_at)
                VALUES (:oid, :uid, :motivation, 'PENDING', NOW())
            """), {"oid": org_id, "uid": user_id, "motivation": motivation})
            conn.commit()

        return {"message": "Application submitted successfully"}, 201

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.post("/<int:org_id>/applications/<int:app_id>/approve")
def approve_organization_application(org_id, app_id):
    """Approve a pending organization application (admin or representative only)."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # Check role
            check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

            app_row = conn.execute(text("""
                SELECT user_id FROM organization_applications
                WHERE id = :app_id AND organization_id = :oid AND status = 'PENDING'
            """), {"app_id": app_id, "oid": org_id}).fetchone()

            if not app_row:
                return {"error": "Application not found or already processed"}, 404

            applicant_id = app_row.user_id

            # Get organization name for notification
            org = conn.execute(text("""
                SELECT name FROM organizations WHERE id = :oid
            """), {"oid": org_id}).fetchone()
            org_name = org.name if org else "Organization"

            # Approve and move to members
            conn.execute(text("""
                UPDATE organization_applications SET status = 'APPROVED' WHERE id = :app_id
            """), {"app_id": app_id})
            conn.execute(text("""
                INSERT INTO organization_members (organization_id, user_id, role, joined_at)
                VALUES (:oid, :uid, 'MEMBER', NOW())
            """), {"oid": org_id, "uid": applicant_id})

            # Send notification
            notify_org_approved(conn, applicant_id, org_name, org_id)

            conn.commit()

        return {"message": "Application approved and member added"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.post("/<int:org_id>/applications/<int:app_id>/reject")
def reject_organization_application(org_id, app_id):
    """Reject a pending organization application (admin or representative only)."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # Check role
            check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

            app_row = conn.execute(text("""
                SELECT user_id FROM organization_applications
                WHERE id = :app_id AND organization_id = :oid AND status = 'PENDING'
            """), {"app_id": app_id, "oid": org_id}).fetchone()

            if not app_row:
                return {"error": "Application not found or already processed"}, 404

            applicant_id = app_row.user_id

            # Get organization name for notification
            org = conn.execute(text("""
                SELECT name FROM organizations WHERE id = :oid
            """), {"oid": org_id}).fetchone()
            org_name = org.name if org else "Organization"

            # Reject the application
            conn.execute(text("""
                UPDATE organization_applications SET status = 'REJECTED' WHERE id = :app_id
            """), {"app_id": app_id})

            # Send notification
            notify_org_rejected(conn, applicant_id, org_name, org_id)

            conn.commit()

        return {"message": "Application rejected successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.put("/<int:org_id>")
def update_organization(org_id):
    """Update organization info (only owner or admin)."""
    try:
        user_id = verify_jwt()

        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400

        allowed_fields = {"description", "photo_url", "status"}
        updates = {k: v for k, v in data.items() if k in allowed_fields}

        if not updates:
            return {"error": "No valid fields to update"}, 400

        with current_app.engine.connect() as conn:
            # Check ownership/admin permissions
            check_organization_ownership(conn, org_id, user_id, allow_admin=True)

            set_clause = ", ".join([f"{k} = :{k}" for k in updates])
            updates["id"] = org_id

            conn.execute(text(f"""
                UPDATE organizations
                SET {set_clause}, updated_at = NOW()
                WHERE id = :id
            """), updates)
            conn.commit()

        return {"message": "Organization updated successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.delete("/<int:org_id>")
def delete_organization(org_id):
    """Delete an organization (only owner or admin)."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # Check ownership/admin permissions
            check_organization_ownership(conn, org_id, user_id, allow_admin=True)

            conn.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": org_id})
            conn.commit()

        return {"message": "Organization deleted successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.get("/<int:org_id>/applications")
def get_organization_applications(org_id):
    """
    List all applications for a specific organization (admin/representative only).
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # Role check
            check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

            base_query = """
                SELECT
                    a.id,
                    a.user_id,
                    u.username,
                    a.motivation,
                    a.status,
                    a.created_at
                FROM organization_applications a
                JOIN users u ON a.user_id = u.id
                WHERE a.organization_id = :oid
                ORDER BY a.created_at DESC
            """

            count_query = """
                SELECT COUNT(*)
                FROM organization_applications a
                WHERE a.organization_id = :oid
            """

            params = {"oid": org_id}
            result = paginate_query(conn, base_query, count_query, params)
            return jsonify(result)

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.get("/")
def get_organizations():
    """
    List all organizations with member count and owner info.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        with current_app.engine.connect() as conn:
            base_query = """
                SELECT
                    o.id,
                    o.name,
                    o.description,
                    o.status,
                    o.created_at,
                    o.updated_at,
                    u.username AS owner_username,
                    (
                        SELECT COUNT(*) FROM organization_members m
                        WHERE m.organization_id = o.id
                    ) AS member_count
                FROM organizations o
                LEFT JOIN users u ON o.owner_user_id = u.id
                WHERE o.status = 'ACTIVE'
                ORDER BY o.name ASC
            """

            count_query = """
                SELECT COUNT(*)
                FROM organizations o
                WHERE o.status = 'ACTIVE'
            """

            result = paginate_query(conn, base_query, count_query)
            return jsonify(result)

    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.get("/filter")
def filter_organizations():
    """
    Filters organizations by:
      - q: only organization name (LIKE)
      - university: exact university id (digit guaranteed)

    Supports pagination with ?page=1&per_page=20
    """
    try:
        search = request.args.get("q")
        university = request.args.get("university")  # guaranteed digit

        filters = []
        params = {}

        # Always filter out inactive organizations
        filters.append("o.status = 'ACTIVE'")

        if search:
            filters.append("LOWER(o.name) LIKE LOWER(:search)")
            params["search"] = f"%{search.strip()}%"

        if university:
            filters.append("uni.id = :university_id")
            params["university_id"] = int(university)

        where_clause = "WHERE " + " AND ".join(filters)

        with current_app.engine.connect() as conn:
            base_query = f"""
                SELECT
                    o.id,
                    o.name,
                    o.description,
                    o.status,
                    o.photo_url,
                    o.created_at,
                    o.updated_at,
                    u.username AS owner_username,
                    uni.id AS university_id,
                    uni.name AS university_name,
                    (
                        SELECT COUNT(*)
                        FROM organization_members m
                        WHERE m.organization_id = o.id
                    ) AS member_count
                FROM organizations o
                LEFT JOIN users u ON o.owner_user_id = u.id
                LEFT JOIN universities uni ON u.university_id = uni.id
                {where_clause}
                ORDER BY o.name ASC
            """

            count_query = f"""
                SELECT COUNT(*)
                FROM organizations o
                LEFT JOIN users u ON o.owner_user_id = u.id
                LEFT JOIN universities uni ON u.university_id = uni.id
                {where_clause}
            """

            result = paginate_query(conn, base_query, count_query, params)
            return jsonify(result)

    except ValueError:
        return {"error": "Invalid university id"}, 400
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.delete("/<int:org_id>/members/<int:target_user_id>")
def remove_member(org_id, target_user_id):
    """
    Remove a user from an organization.
    - A user can remove themselves.
    - Admins can remove other members (not other admins).
    """
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # 🔍 Hedef kullanıcının organizasyonda olup olmadığını kontrol et
            target_member = conn.execute(text("""
                SELECT role FROM organization_members
                WHERE organization_id = :oid AND user_id = :uid
            """), {"oid": org_id, "uid": target_user_id}).fetchone()

            if not target_member:
                return {"error": "Target user is not a member of this organization."}, 404

            # 🔍 İstek yapan kişinin rolünü kontrol et
            requester = conn.execute(text("""
                SELECT role FROM organization_members
                WHERE organization_id = :oid AND user_id = :uid
            """), {"oid": org_id, "uid": user_id}).fetchone()

            if not requester:
                return {"error": "You are not a member of this organization."}, 403

            requester_role = requester.role
            target_role = target_member.role

            # 🔒 Yetki kontrolü
            if user_id == target_user_id:
                # kullanıcı kendi çıkmak istiyor
                if requester_role in ("ADMIN"):
                    return {
                        "error": "Admins or owners cannot leave the organization directly. Transfer ownership or delegate first."
                    }, 403
                # normal member çıkabilir
            elif requester_role == "ADMIN":
                # admin başka üyeyi çıkarabilir ama başka admini çıkaramaz
                if target_role in ("ADMIN"):
                    return {"error": "You cannot remove other admins or the owner."}, 403
            else:
                # member başkasını çıkaramaz
                return {"error": "You do not have permission to remove other members."}, 403

            # 🗑️ Silme işlemi
            conn.execute(text("""
                DELETE FROM organization_members
                WHERE organization_id = :oid AND user_id = :uid
            """), {"oid": org_id, "uid": target_user_id})
            conn.commit()

        msg = (
            "You have successfully left the organization."
            if user_id == target_user_id
            else "Member removed successfully."
        )

        return {"message": msg}, 200

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired."}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token."}, 401
    except Exception as e:
        return {"error": f"Internal server error: {str(e)}"}, 500


@organization_bp.post("/<int:org_id>/report")
def report_organization(org_id):
    """
    Report an organization for inappropriate content.
    Body: {"reason": "This organization contains spam"}
    """
    try:
        user_id = verify_jwt()
        data = request.get_json()
        reason = data.get("reason", "").strip()
        
        if not reason:
            return {"error": "Reason is required"}, 400
        
        if len(reason) < 10:
            return {"error": "Reason must be at least 10 characters"}, 400
        
        with current_app.engine.connect() as conn:
            # Check if organization exists
            org = conn.execute(
                text("SELECT id FROM organizations WHERE id = :id"),
                {"id": org_id}
            ).fetchone()
            
            if not org:
                return {"error": "Organization not found"}, 404
            
            # Check if user already reported this organization
            existing = conn.execute(
                text("""
                    SELECT id FROM reports 
                    WHERE organization_id = :oid AND reporter_user_id = :uid
                """),
                {"oid": org_id, "uid": user_id}
            ).fetchone()
            
            if existing:
                return {"error": "You have already reported this organization"}, 409
            
            # Create report
            conn.execute(
                text("""
                    INSERT INTO reports (organization_id, reporter_user_id, reason, status, created_at)
                    VALUES (:oid, :uid, :reason, 'PENDING', NOW())
                """),
                {"oid": org_id, "uid": user_id, "reason": reason}
            )
            conn.commit()
        
        return {"message": "Report submitted successfully"}, 201
    
    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@organization_bp.get("/my-reports")
def get_my_organization_reports():
    """
    Get current user's organization reports.
    Query params: ?page=1&per_page=20
    """
    try:
        user_id = verify_jwt()
        
        with current_app.engine.connect() as conn:
            base_query = """
                SELECT 
                    r.id,
                    r.organization_id,
                    o.name as organization_name,
                    r.reason,
                    r.status,
                    r.admin_notes,
                    r.created_at,
                    r.updated_at
                FROM reports r
                JOIN organizations o ON r.organization_id = o.id
                WHERE r.reporter_user_id = :uid
                ORDER BY r.created_at DESC
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM reports
                WHERE reporter_user_id = :uid AND organization_id IS NOT NULL
            """
            
            params = {"uid": user_id}
            result = paginate_query(conn, base_query, count_query, params)
            return jsonify(result)
    
    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503
