"""
Notification helper functions for creating notifications.
"""
from sqlalchemy import text
from datetime import datetime


def create_notification(conn, user_id, notification_type, title, message,
                       related_event_id=None, related_organization_id=None):
    """
    Create a notification for a user.

    Args:
        conn: Database connection
        user_id: User ID to send notification to
        notification_type: Type of notification (e.g., 'EVENT_REMINDER', 'APPLICATION_APPROVED')
        title: Notification title
        message: Notification message
        related_event_id: Optional event ID
        related_organization_id: Optional organization ID

    Returns:
        notification_id: ID of created notification
    """
    result = conn.execute(
        text("""
            INSERT INTO notifications
            (user_id, type, title, message, related_event_id, related_organization_id, created_at)
            VALUES
            (:user_id, :type, :title, :message, :event_id, :org_id, NOW())
        """),
        {
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "event_id": related_event_id,
            "org_id": related_organization_id
        }
    )
    return result.lastrowid


def notify_event_approved(conn, user_id, event_title, event_id):
    """Notify user that their event application was approved."""
    return create_notification(
        conn=conn,
        user_id=user_id,
        notification_type="APPLICATION_APPROVED",
        title="Application Approved!",
        message=f"Your application for '{event_title}' has been approved.",
        related_event_id=event_id
    )


def notify_event_rejected(conn, user_id, event_title, event_id):
    """Notify user that their event application was rejected."""
    return create_notification(
        conn=conn,
        user_id=user_id,
        notification_type="APPLICATION_REJECTED",
        title="Application Status",
        message=f"Your application for '{event_title}' was not approved.",
        related_event_id=event_id
    )


def notify_org_approved(conn, user_id, org_name, org_id):
    """Notify user that their organization application was approved."""
    return create_notification(
        conn=conn,
        user_id=user_id,
        notification_type="ORG_APPLICATION_APPROVED",
        title="Organization Application Approved!",
        message=f"You are now a member of '{org_name}'.",
        related_organization_id=org_id
    )


def notify_org_rejected(conn, user_id, org_name, org_id):
    """Notify user that their organization application was rejected."""
    return create_notification(
        conn=conn,
        user_id=user_id,
        notification_type="ORG_APPLICATION_REJECTED",
        title="Organization Application Status",
        message=f"Your application to join '{org_name}' was not approved.",
        related_organization_id=org_id
    )


def notify_event_reminder(conn, user_id, event_title, event_id, starts_at):
    """Notify user about upcoming event."""
    return create_notification(
        conn=conn,
        user_id=user_id,
        notification_type="EVENT_REMINDER",
        title="Event Reminder",
        message=f"'{event_title}' is starting soon at {starts_at}!",
        related_event_id=event_id
    )


def notify_event_cancelled(conn, user_id, event_title, event_id):
    """Notify user that an event was cancelled."""
    return create_notification(
        conn=conn,
        user_id=user_id,
        notification_type="EVENT_CANCELLED",
        title="Event Cancelled",
        message=f"Unfortunately, '{event_title}' has been cancelled.",
        related_event_id=event_id
    )
