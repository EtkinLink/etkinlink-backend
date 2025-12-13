from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import text
from utils.auth_utils import verify_jwt, AuthError
from utils.pagination import paginate_query, get_pagination_params
from datetime import datetime

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.get("")
def get_notifications():
    """
    Get notifications for the authenticated user.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        user_id = verify_jwt()
        pagination_params = get_pagination_params()

        with current_app.engine.connect() as conn:
            base_query = """
                SELECT 
                    n.id,
                    n.user_id,
                    n.type,
                    n.title,
                    n.message,
                    n.is_read,
                    n.created_at,
                    n.related_event_id,
                    n.related_organization_id
                FROM notifications n
                WHERE n.user_id = :user_id
                ORDER BY n.created_at DESC
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM notifications 
                WHERE user_id = :user_id
            """
            
            params = {"user_id": user_id}
            result = paginate_query(conn, base_query, count_query, params, pagination_params)
            return jsonify(result)

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@notifications_bp.get("/unread-count")
def get_unread_count():
    """Get count of unread notifications for the authenticated user."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            count = conn.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM notifications 
                    WHERE user_id = :user_id AND is_read = FALSE
                """),
                {"user_id": user_id}
            ).scalar()

        return jsonify({"unread_count": count})

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@notifications_bp.put("/<int:notification_id>/mark-read")
def mark_notification_as_read(notification_id):
    """Mark a specific notification as read."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # Check if notification belongs to user
            notification = conn.execute(
                text("SELECT id FROM notifications WHERE id = :id AND user_id = :user_id"),
                {"id": notification_id, "user_id": user_id}
            ).fetchone()

            if not notification:
                return {"error": "Notification not found"}, 404

            # Mark as read
            conn.execute(
                text("UPDATE notifications SET is_read = TRUE WHERE id = :id"),
                {"id": notification_id}
            )
            conn.commit()

        return {"message": "Notification marked as read"}, 200

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@notifications_bp.put("/mark-all-read")
def mark_all_notifications_as_read():
    """Mark all notifications as read for the authenticated user."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            conn.execute(
                text("UPDATE notifications SET is_read = TRUE WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            conn.commit()

        return {"message": "All notifications marked as read"}, 200

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@notifications_bp.delete("/<int:notification_id>")
def delete_notification(notification_id):
    """Delete a specific notification."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            # Check if notification belongs to user
            notification = conn.execute(
                text("SELECT id FROM notifications WHERE id = :id AND user_id = :user_id"),
                {"id": notification_id, "user_id": user_id}
            ).fetchone()

            if not notification:
                return {"error": "Notification not found"}, 404

            # Delete notification
            conn.execute(
                text("DELETE FROM notifications WHERE id = :id"),
                {"id": notification_id}
            )
            conn.commit()

        return {"message": "Notification deleted"}, 200

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@notifications_bp.delete("/clear-all")
def clear_all_notifications():
    """Delete all notifications for the authenticated user."""
    try:
        user_id = verify_jwt()

        with current_app.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM notifications WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            conn.commit()

        return {"message": "All notifications cleared"}, 200

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503
