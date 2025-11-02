# utils/auth_utils.py
import jwt
import os
from flask import request
from sqlalchemy import text

SECRET_KEY = os.getenv("SECRET_KEY")

class AuthError(Exception):
    """Custom exception for auth failures."""
    def __init__(self, message, code=401):
        super().__init__(message)
        self.code = code


def get_token_from_header():
    """Extracts JWT token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError("Authorization header missing or invalid", 401)
    return auth_header.split(" ", 1)[1]


def decode_jwt(token: str):
    """Decodes JWT token and returns payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired", 401)
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token", 401)


def verify_jwt():
    """
    Full helper: verifies Authorization header,
    decodes JWT, and returns user_id.
    """
    token = get_token_from_header()
    payload = decode_jwt(token)
    user_id = payload.get("userId")

    if not user_id:
        raise AuthError("Invalid token: userId missing", 401)
    return user_id


def check_organization_permission(conn, org_id, user_id, required_roles=None):
    """
    Check if user has required role in organization.
    
    Args:
        conn: Database connection
        org_id: Organization ID
        user_id: User ID
        required_roles: List of required roles (default: ["ADMIN", "REPRESENTATIVE"])
    
    Returns:
        role: User's role in organization
    
    Raises:
        AuthError: If user doesn't have required permissions
    """
    if required_roles is None:
        required_roles = ["ADMIN", "REPRESENTATIVE"]
    
    role_row = conn.execute(text("""
        SELECT role FROM organization_members
        WHERE organization_id = :org_id AND user_id = :uid
    """), {"org_id": org_id, "uid": user_id}).fetchone()
    
    if not role_row or role_row.role not in required_roles:
        raise AuthError("You are not authorized to perform this action for this organization", 403)
    
    return role_row.role


def check_event_ownership(conn, event_id, user_id):
    """
    Check if user can modify the event (owner or org admin/representative).
    
    Args:
        conn: Database connection
        event_id: Event ID
        user_id: User ID
    
    Returns:
        event: Event row with ownership info
    
    Raises:
        AuthError: If user doesn't have permissions or event not found
    """
    event = conn.execute(text("""
        SELECT owner_user_id, owner_type, owner_organization_id
        FROM events WHERE id = :id
    """), {"id": event_id}).fetchone()
    
    if not event:
        raise AuthError("Event not found", 404)
    
    owner_type = event.owner_type
    org_id = event.owner_organization_id
    
    # Check permission based on owner type
    if owner_type == "USER" and event.owner_user_id != user_id:
        raise AuthError("Not authorized to modify this event", 403)
    
    if owner_type == "ORGANIZATION":
        check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])
    
    return event


def check_organization_ownership(conn, org_id, user_id, allow_admin=True):
    """
    Check if user can modify the organization (owner or admin).
    
    Args:
        conn: Database connection
        org_id: Organization ID
        user_id: User ID
        allow_admin: Whether to allow admin role (default: True)
    
    Returns:
        org: Organization row with ownership info
    
    Raises:
        AuthError: If user doesn't have permissions or organization not found
    """
    org = conn.execute(text("""
        SELECT owner_user_id FROM organizations WHERE id = :id
    """), {"id": org_id}).fetchone()
    
    if not org:
        raise AuthError("Organization not found", 404)
    
    # Check if user is owner
    if org.owner_user_id == user_id:
        return org
    
    # Check if user is admin (if allowed)
    if allow_admin:
        try:
            check_organization_permission(conn, org_id, user_id, ["ADMIN"])
            return org
        except AuthError:
            pass
    
    raise AuthError("Not authorized to modify this organization", 403)


def require_auth(f):
    """
    Decorator that requires authentication and injects user_id.
    Usage: @require_auth
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = verify_jwt()
            return f(user_id, *args, **kwargs)
        except AuthError as e:
            return {"error": e.args[0]}, e.code
    return decorated_function