from datetime import datetime, timedelta
from functools import wraps
import os
import re
import uuid
import secrets
from backend.utils.auth_utils import verify_jwt, AuthError, check_organization_permission, check_event_ownership, check_organization_ownership, require_auth
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.mail_service import (
    generate_verification_token,
    verify_token,
    send_verification_email,
    send_password_reset_email
)
from backend.config import get_config

from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
import jwt
import pkgutil
import importlib
import backend.api as api
from sqlalchemy import create_engine, text

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load configuration
config = get_config()
app.config.from_object(config)

# Mail nesnesini oluştur
app.config["MAILTRAP_API_TOKEN"] = os.getenv("MAILTRAP_API_TOKEN")
app.config["MAIL_FROM_EMAIL"] = os.getenv("MAIL_FROM_EMAIL")
app.config["MAIL_FROM_NAME"] = os.getenv("MAIL_FROM_NAME")

# Backend base url
app.config["BACKEND_BASE_URL"] = os.getenv("BACKEND_BASE_URL")

#Frontend base url
app.config["FRONTEND_BASE_URL"] = os.getenv("FRONTEND_BASE_URL")

# Database engine
DATABASE_URL = app.config['DATABASE_URL']
SECRET_KEY = app.config['SECRET_KEY']
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# Engine'i app'e ekle ki Blueprint'ler current_app.engine ile erişebilsin
app.engine = engine

# =============================================
# Moduler yapinin calismasi icin gerekli kodlar
# =============================================
def register_blueprints(app):
    """api/ klasöründeki tüm Blueprint'leri otomatik olarak bulur ve kaydeder."""
    # api paketinin içindeki tüm modülleri (users.py, auth.py, vb.) tarar
    for finder, name, ispkg in pkgutil.iter_modules(api.__path__, api.__name__ + '.'):
        # Örnek: 'api.users', 'api.auth'
        module = importlib.import_module(name)
        
        # Modülün içinde Blueprint nesnesi olup olmadığını kontrol et
        for item_name in dir(module):
            item = getattr(module, item_name)
            
            # Flask'ın Blueprint tipinde bir nesne bulursak
            if isinstance(item, Blueprint):
                app.register_blueprint(item)
                print(f"✓ Blueprint Kaydedildi: {item.name} → {item.url_prefix or '/'}")

# Blueprint keşfini çalıştır
register_blueprints(app)


@app.post("/test-login")
def test_login():
    try:
        user_id = request.json.get("user_id")
        if not user_id:
            return {"error": "user_id required"}, 400

        payload = {
            "userId": user_id,
            "exp": datetime.utcnow() + timedelta(hours=2)
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return {"access_token": token}

    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as e:

        return {"ok": False, "error": str(e)}, 503
    
    
@app.route("/users/me", methods=["GET", "PUT"])
def users_me():
    try:
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {"error": "Authorization header missing or invalid"}, 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("userId")
            if not user_id:
                return {"error": "Invalid token: userId missing"}, 401
        except jwt.ExpiredSignatureError:
            return {"error": "Token expired"}, 401
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401

        
        if request.method == "GET":
            with engine.connect() as conn:
                user_row = conn.execute(
                    text("SELECT  username, name, email FROM users WHERE id = :id"),
                    {"id": user_id}
                ).fetchone()

                if not user_row:
                    return {"error": "User not found"}, 404

                user = dict(user_row._mapping)

                total_events = conn.execute(
                    text("SELECT COUNT(*) FROM participants WHERE user_id = :id"),
                    {"id": user_id}
                ).scalar()

                attended_events = conn.execute(
                    text("SELECT COUNT(*) FROM participants WHERE user_id = :id AND status = 'ATTENDED'"),
                    {"id": user_id}
                ).scalar()

                if total_events == 0:
                    attendance_rate = -1  
                else:
                    attendance_rate = int((attended_events * 100) // total_events)  

                user["attendance_rate"] = attendance_rate

                return jsonify(user)

        
        if request.method == "PUT":
            data = request.get_json(silent=True)
            if not data:
                return {"error": "No data provided"}, 400

            allowed_fields = {"username"}  # ileride genişletilir
            update_data = {k: v for k, v in data.items() if k in allowed_fields}

            if not update_data:
                return {"error": "No valid fields to update"}, 400

            if "username" in update_data:
                new_username = update_data["username"].strip()
                if len(new_username) < 3:
                    return {"error": "Username must be at least 3 characters"}, 400
                if not re.match(r"^[a-zA-Z0-9_]+$", new_username):
                    return {"error": "Username can only contain letters, numbers and _"}, 400

                with engine.connect() as conn:
                    exists = conn.execute(
                        text("SELECT id FROM users WHERE username = :u AND id != :id"),
                        {"u": new_username, "id": user_id}
                    ).fetchone()

                    if exists:
                        return {"error": "Username already taken"}, 409

            set_clause = ", ".join([f"{k} = :{k}" for k in update_data])
            update_data["id"] = user_id

            with engine.connect() as conn:
                conn.execute(
                    text(f"UPDATE users SET {set_clause} WHERE id = :id"),
                    update_data
                )
                conn.commit()

            return {"message": "Profile updated successfully", **update_data}

    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/users/me/organizations")
def get_my_organizations():
    """
    List organizations the authenticated user has joined or applied to.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        user_id = verify_jwt()  # ✅ JWT doğrulama (token'dan user_id alır)
        pagination_params = get_pagination_params()

        with engine.connect() as conn:
            # Combined query for both member and applied organizations
            base_query = """
                (
                    SELECT 
                        o.id,
                        o.name,
                        o.description,
                        m.role,
                        'MEMBER' AS relation,
                        m.joined_at AS date
                    FROM organization_members m
                    JOIN organizations o ON o.id = m.organization_id
                    WHERE m.user_id = :uid
                )
                UNION
                (
                    SELECT 
                        o.id,
                        o.name,
                        o.description,
                        a.status AS role,
                        'APPLIED' AS relation,
                        a.created_at AS date
                    FROM organization_applications a
                    JOIN organizations o ON o.id = a.organization_id
                    WHERE a.user_id = :uid
                    AND a.organization_id NOT IN (
                        SELECT organization_id FROM organization_members WHERE user_id = :uid
                    )
                )
                ORDER BY date DESC
            """
            
            count_query = """
                SELECT COUNT(*) FROM (
                    SELECT o.id
                    FROM organization_members m
                    JOIN organizations o ON o.id = m.organization_id
                    WHERE m.user_id = :uid
                    
                    UNION
                    
                    SELECT o.id
                    FROM organization_applications a
                    JOIN organizations o ON o.id = a.organization_id
                    WHERE a.user_id = :uid
                    AND a.organization_id NOT IN (
                        SELECT organization_id FROM organization_members WHERE user_id = :uid
                    )
                ) AS combined_orgs
            """
            
            params = {"uid": user_id}
            result = paginate_query(conn, base_query, count_query, params, pagination_params)
            return jsonify(result)

    except AuthError as e:
        return {"error": e.args[0]}, e.code  # 🔒 Token hatalarını düzgün döndür
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/universities")
def universities():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM universities"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/event_types")
def event_types():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM event_types"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/users/me/events")
def get_my_events_and_tickets():
    """
    Get authenticated user's events and tickets.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        user_id = verify_jwt() 

        with engine.connect() as conn:
            base_query = """
                SELECT 
                    e.id AS event_id,
                    e.title AS event_title,
                    e.starts_at,
                    e.location_name,
                    p.ticket_code,
                    p.status AS participation_status
                FROM participants p
                JOIN events e ON e.id = p.event_id
                WHERE p.user_id = :uid
                ORDER BY e.starts_at DESC
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM participants p
                JOIN events e ON e.id = p.event_id
                WHERE p.user_id = :uid
            """
            
            params = {"uid": user_id}
            result = paginate_query(conn, base_query, count_query, params)
            return jsonify(result)

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503



@app.get("/users/<int:user_id>/events")
def get_user_events(user_id):
    """
    Returns events that the user has participated in or owns, plus events of organizations they applied to.
    Supports pagination with ?page=1&per_page=20 parameters.
    """
    try:
        pagination_params = get_pagination_params()
        
        with engine.connect() as conn:
            base_query = """
                (
                    SELECT 
                        e.id,
                        e.title,
                        e.starts_at,
                        e.ends_at,
                        e.location_name,
                        e.status,
                        e.created_at,
                        e.owner_type,
                        et.code AS event_type,
                        p.status AS participation_status,
                        o.name AS owner_organization_name,
                        u.username AS owner_username
                    FROM participants p
                    JOIN events e ON e.id = p.event_id
                    LEFT JOIN event_types et ON e.type_id = et.id
                    LEFT JOIN organizations o ON e.owner_organization_id = o.id
                    LEFT JOIN users u ON e.owner_user_id = u.id
                    WHERE p.user_id = :uid
                )
                UNION
                (
                    SELECT 
                        e.id,
                        e.title,
                        e.starts_at,
                        e.ends_at,
                        e.location_name,
                        e.status,
                        e.created_at,
                        e.owner_type,
                        et.code AS event_type,
                        'APPLIED' AS participation_status,
                        o.name AS owner_organization_name,
                        u.username AS owner_username
                    FROM organization_applications a
                    JOIN events e ON e.owner_organization_id = a.organization_id
                    LEFT JOIN event_types et ON e.type_id = et.id
                    LEFT JOIN organizations o ON e.owner_organization_id = o.id
                    LEFT JOIN users u ON e.owner_user_id = u.id
                    WHERE a.user_id = :uid
                    AND e.id NOT IN (
                        SELECT p.event_id FROM participants p WHERE p.user_id = :uid
                    )
                )
                UNION
                (
                    SELECT
                        e.id,
                        e.title,
                        e.starts_at,
                        e.ends_at,
                        e.location_name,
                        e.status,
                        e.created_at,
                        e.owner_type,
                        et.code AS event_type,
                        'OWNER' AS participation_status,
                        o.name AS owner_organization_name,
                        u.username AS owner_username
                    FROM events e
                    LEFT JOIN event_types et ON e.type_id = et.id
                    LEFT JOIN organizations o ON e.owner_organization_id = o.id
                    LEFT JOIN users u ON e.owner_user_id = u.id
                    WHERE e.owner_user_id = :uid
                )
                ORDER BY starts_at DESC
            """
            
            count_query = """
                SELECT COUNT(*) FROM (
                    SELECT e.id
                    FROM participants p
                    JOIN events e ON e.id = p.event_id
                    WHERE p.user_id = :uid
                    
                    UNION
                    
                    SELECT e.id
                    FROM organization_applications a
                    JOIN events e ON e.owner_organization_id = a.organization_id
                    WHERE a.user_id = :uid
                    AND e.id NOT IN (
                        SELECT p.event_id FROM participants p WHERE p.user_id = :uid
                    )

                    UNION

                    SELECT e.id
                    FROM events e
                    WHERE e.owner_user_id = :uid
                ) AS combined_events
            """
            
            params = {"uid": user_id}
            result = paginate_query(conn, base_query, count_query, params, pagination_params)
            return jsonify(result)
            
    except Exception as e:
        return {"error": str(e)}, 503


# Manage (approve/reject) an event application
@app.put("/applications/<int:application_id>/status")
def manage_event_application(application_id):
    """
    Approve or reject an event application.
    Only the event owner (user or org admin/rep) can access this.
    """
    try:
        organizer_user_id = verify_jwt()

        data = request.get_json()
        new_status = data.get("status", "").upper()

        if new_status not in ["APPROVED", "REJECTED"]:
            return {"error": "Invalid status. Must be 'APPROVED' or 'REJECTED'"}, 400

        with engine.connect() as conn:
            
            application_details = conn.execute(
                text("""
                    SELECT 
                        a.event_id, 
                        a.user_id AS applicant_user_id,
                        a.status AS current_status,
                        e.user_limit
                    FROM applications a
                    JOIN events e ON a.event_id = e.id
                    WHERE a.id = :app_id
                """),
                {"app_id": application_id}
            ).fetchone()

            if not application_details:
                return {"error": "Application not found"}, 404
            
            if application_details.current_status != 'PENDING':
                return {"error": "Application has already been processed"}, 409

            try:
                check_event_ownership(conn, application_details.event_id, organizer_user_id)
            except AuthError as auth_err:
                return {"error": auth_err.args[0]}, auth_err.code

            
            with conn.begin() as trans:
                
                if new_status == 'APPROVED':
                    
                    user_limit = application_details.user_limit
                    
                    if user_limit is not None:
                        current_participant_count = conn.execute(
                            text("SELECT COUNT(*) FROM participants WHERE event_id = :eid"),
                            {"eid": application_details.event_id}
                        ).scalar()
                        
                        if current_participant_count >= user_limit:
                            trans.rollback()
                            return {"error": "Event user limit reached. Cannot approve."}, 409

                    ticket_code = str(uuid.uuid4())
                    
                    conn.execute(
                        text("""
                            INSERT INTO participants (event_id, user_id, application_id, status, ticket_code)
                            VALUES (:eid, :uid, :app_id, 'NO_SHOW', :ticket)
                        """),
                        {
                            "eid": application_details.event_id,
                            "uid": application_details.applicant_user_id,
                            "app_id": application_id,
                            "ticket": ticket_code
                        }
                    )
                
                conn.execute(
                    text("UPDATE applications SET status = :status WHERE id = :app_id"),
                    {"status": new_status, "app_id": application_id}
                )
            

        return {"message": f"Application {new_status.lower()}"}, 200

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}, 503


@app.get("/applications")
def applications():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM applications"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/participants")
def participants():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM participants"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/ratings")
def ratings():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM ratings"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))