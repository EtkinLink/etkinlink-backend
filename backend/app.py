from datetime import datetime, timedelta
from functools import wraps
import os
import re
from utils.auth_utils import verify_jwt, AuthError, check_organization_permission, check_event_ownership, check_organization_ownership, require_auth
from utils.email import generate_verification_token, verify_token, send_verification_email
from flask_mail import Mail

from flask import Flask, jsonify, request
from flask_cors import CORS
import jwt
from sqlalchemy import create_engine, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
CORS(app)

# Mail konfigürasyonları
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Mail nesnesini oluştur
mail = Mail(app)

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


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


@app.get("/universities")
def universities():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM universities"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503

# Auth fonksiyonlari
@app.post("/auth/register")
def register():
    #email normalization
    def normalize_email(email_str):
        """
            Normalizes an email address for DB storage and querying.
            1. Ignores the part after '+'.
            2. Removes all '.' (dot) characters from the local part.
            3. Converts the entire address to lowercase.
            
            Example: 'User.Name+Test@Example.Com' -> 'username@example.com'
        """
        if not email_str:
            return email_str
            
        try:
            email_str = email_str.strip()
            local_part, domain_part = email_str.split('@', 1)
            
            local_part = local_part.split('+', 1)[0]
            
            local_part = local_part.replace('.', '')
            local_part = local_part.lower()
            
            domain_part = domain_part.lower()
            
            return f"{local_part}@{domain_part}"
        
        except (ValueError, AttributeError):
            return email_str
    data = request.get_json()
    email = normalize_email(data.get("email"))
    password = data.get("password")
    name = data.get("name")

    if not email or not password or not name:
        return {"error": "All fields are required"}, 400

    try:
        with engine.connect() as conn:
            # Email kullanımda mı kontrol et
            existing_user = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email}
            ).fetchone()
            
            if existing_user:
                return {"error": "Email already registered"}, 400
            
            try:
                domain = email.split('@')[1]
            except IndexError:
                return {"error": "Invalid email format."}, 400
            
            sql_query = text("""
                SELECT 
                    ud.university_id 
                FROM 
                    university_domains ud
                WHERE 
                    ud.domain = :domain_name
            """)

            result = conn.execute(sql_query, {"domain_name": domain}).fetchone()

            if result:
                university_id = result[0]
            else:
                return {"error": "University not found."}, 404

            # Token payload'ı hazırla
            payload = {
                "email": email,
                "password": generate_password_hash(password),
                "name": name,
                # datetime nesnesini ISO format string'e çevir
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Verification token oluştur
            token = generate_verification_token(payload)
            
            # Verification emaili gönder
            send_verification_email(email, token)

            return {"message": "Verification email sent"}, 200

    except Exception as e:
        return {"error": f"Registration failed: {str(e)}"}, 503


@app.get("/auth/register/verify/<token>")
def verify_email(token):
    payload = verify_token(token)
    if not payload:
        return {"error": "Invalid or expired verification link"}, 400

    try:
        with engine.connect() as conn:
            # Email kullanımda mı tekrar kontrol et
            existing_user = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": payload["email"]}
            ).fetchone()
            
            if existing_user:
                return {"error": "Email already registered"}, 400

            # Kullanıcıyı kaydet
            result = conn.execute(
                text("""
                    INSERT INTO users (email, password_hash, name) 
                    VALUES (:email, :password, :name)
                """),
                {
                    "email": payload["email"],
                    "password": payload["password"],
                    "name": payload["name"]
                }
            )
            conn.commit()

            return {"message": "Account verified successfully"}, 200

    except Exception as e:
        return {"error": f"Verification failed: {str(e)}"}, 503


@app.post("/auth/login")
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"error": "Email and password are required."}, 400

    try:
        with engine.connect() as conn:
            user_row = conn.execute(
                text("SELECT id, password_hash FROM users WHERE email = :email"),
                {"email": email}
            ).fetchone()
            if not user_row:
                return {"error": "No registered account found."}, 401
            user = dict(user_row._mapping)
            stored_password_hash = user["password_hash"]
            if not check_password_hash(stored_password_hash, password):
                return {"error": "Incorrect password."}, 401
            payload = {
                "userId": user["id"],
                "exp": datetime.utcnow() + timedelta(hours=2)
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            response = {"access_token": token}

            return response
    except Exception as e:
        return {"error": f"Login failed: {str(e)}"}, 503


def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {"error": "Authorization header missing or invalid"}, 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("userId")
            if not user_id:
                return {"error": "Invalid token: userId missing"}, 401
            request.user_id = user_id
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return {"error": "Token expired"}, 401
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401
    return decorated


@app.get("/event_types")
def event_types():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM event_types"))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/events")
def get_events():
    """
    Returns all events (user or organization owned) with type, owner info, and participant count.
    """
    try:
        with engine.connect() as conn:
            query = text("""
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
                    e.latitude,
                    e.longitude,
                    e.created_at,
                    e.updated_at,
                    e.owner_type,
                    u.username AS owner_username,
                    o.name AS owner_organization_name,
                    et.code AS event_type,
                    (
                        SELECT COUNT(*) FROM participants p
                        WHERE p.event_id = e.id
                    ) AS participant_count
                FROM events e
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN event_types et ON e.type_id = et.id
                ORDER BY e.starts_at ASC
            """)
            result = conn.execute(query)
            rows = [dict(r._mapping) for r in result]

        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/events/<int:event_id>")
def get_event_by_id(event_id):
    """
    Returns detailed info about a specific event, including participants and applications.
    """
    try:
        with engine.connect() as conn:
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
                    e.latitude,
                    e.longitude,
                    e.created_at,
                    e.updated_at,
                    e.owner_type,
                    e.owner_organization_id,
                    u.username AS owner_username,
                    o.name AS owner_organization_name,
                    et.code AS event_type
                FROM events e
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN event_types et ON e.type_id = et.id
                WHERE e.id = :id
            """), {"id": event_id}).fetchone()

            if not event:
                return {"error": "Event not found"}, 404

            participants = conn.execute(text("""
                SELECT 
                    u.id,
                    u.username,
                    p.status
                FROM participants p
                JOIN users u ON u.id = p.user_id
                WHERE p.event_id = :id
            """), {"id": event_id}).fetchall()

            # Include applications if event belongs to an organization
            applications = []
            if event.owner_type == "ORGANIZATION" and event.owner_organization_id:
                applications = conn.execute(text("""
                    SELECT 
                        a.id,
                        a.user_id,
                        u.username,
                        a.motivation,
                        a.status,
                        a.created_at
                    FROM organization_applications a
                    JOIN users u ON a.user_id = u.id
                    WHERE a.organization_id = :org_id
                    ORDER BY a.created_at DESC
                """), {"org_id": event.owner_organization_id}).fetchall()

        event_data = dict(event._mapping)
        event_data["participants"] = [dict(p._mapping) for p in participants]
        event_data["applications"] = [dict(a._mapping) for a in applications]

        return jsonify(event_data)

    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/events/filter")
def filter_events():
    """
    Filters events by type, date range, university, and search query.
    Works for both user and organization events.
    """
    try:
        type_code = request.args.get("type")
        from_date = request.args.get("from")
        to_date = request.args.get("to")
        search = request.args.get("q")
        university = request.args.get("university")  # can be name or id
        organization = request.args.get("organization")

        filters = []
        params = {}

        # --- Existing filters ---
        if type_code:
            filters.append("et.code = :type_code")
            params["type_code"] = type_code

        if from_date:
            filters.append("e.starts_at >= :from_date")
            params["from_date"] = from_date

        if to_date:
            filters.append("e.starts_at <= :to_date")
            params["to_date"] = to_date

        if search:
            filters.append("(e.title LIKE :search OR o.name LIKE :search OR u.username LIKE :search)")
            params["search"] = f"%{search}%"

        # --- NEW: University filter ---
        if university:
            # Try numeric first (ID), else match by name
            if university.isdigit():
                filters.append("un.id = :university_id")
                params["university_id"] = int(university)
            else:
                filters.append("un.name LIKE :university_name")
                params["university_name"] = f"%{university}%"

        if organization:
            # ID or name filter for organizations
            if organization.isdigit():
                filters.append("o.id = :organization_id")
                params["organization_id"] = int(organization)
            else:
                filters.append("o.name LIKE :organization_name")
                params["organization_name"] = f"%{organization}%"

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        with engine.connect() as conn:
            query = text(f"""
                SELECT 
                    e.id,
                    e.title,
                    e.starts_at,
                    e.ends_at,
                    e.location_name,
                    e.status,
                    e.created_at,
                    e.owner_type,
                    u.username AS owner_username,
                    o.name AS owner_organization_name,
                    et.code AS event_type,
                    un.name AS university_name
                FROM events e
                LEFT JOIN event_types et ON e.type_id = et.id
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN organizations o ON e.owner_organization_id = o.id
                LEFT JOIN universities un ON u.university_id = un.id
                {where_clause}
                ORDER BY e.starts_at ASC
            """)
            result = conn.execute(query, params)
            rows = [dict(r._mapping) for r in result]

        return jsonify(rows)

    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/users/<int:user_id>/events")
def get_user_events(user_id):
    """
    Returns events that the user has participated in or owns, plus events of organizations they applied to.
    """
    try:
        with engine.connect() as conn:
            # Get participant events
            participant_events = conn.execute(text("""
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
                ORDER BY e.starts_at DESC
            """), {"uid": user_id}).fetchall()

            # Get events of organizations the user has applied to
            applied_org_events = conn.execute(text("""
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
                ORDER BY e.starts_at DESC
            """), {"uid": user_id}).fetchall()

            # Merge the results
            all_events = [dict(r._mapping) for r in participant_events]
            all_events.extend([dict(r._mapping) for r in applied_org_events])

            # Sort by starts_at descending
            all_events.sort(key=lambda x: x['starts_at'], reverse=True)

        return jsonify(all_events)
    except Exception as e:
        return {"error": str(e)}, 503


@app.post("/events")
def create_event():
    """
    Create a new event (owned by a user or an organization).
    Requires a valid JWT token.
    """
    try:
        user_id = verify_jwt()

        data = request.get_json()
        required_fields = ["title", "explanation", "type_id", "starts_at", "ends_at", "owner_type"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

        owner_type = data.get("owner_type", "USER").upper()
        org_id = data.get("organization_id") if owner_type == "ORGANIZATION" else None

        # If organization, check if user is admin/member of it
        if owner_type == "ORGANIZATION":
            with engine.connect() as conn:
                check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

        with engine.connect() as conn:
            query = text("""
                INSERT INTO events (
                    owner_user_id, owner_type, owner_organization_id,
                    title, explanation, type_id, price,
                    starts_at, ends_at, location_name, photo_url,
                    status, user_limit, latitude, longitude, created_at, updated_at
                )
                VALUES (
                    :owner_user_id, :owner_type, :owner_organization_id,
                    :title, :explanation, :type_id, :price,
                    :starts_at, :ends_at, :location_name, :photo_url,
                    'FUTURE', :user_limit, :latitude, :longitude, NOW(), NOW()
                )
            """)

            conn.execute(query, {
                "owner_user_id": user_id,
                "owner_type": owner_type,
                "owner_organization_id": org_id,
                "title": data.get("title"),
                "explanation": data.get("explanation"),
                "type_id": data.get("type_id"),
                "price": data.get("price", 0),
                "starts_at": data.get("starts_at"),
                "ends_at": data.get("ends_at"),
                "location_name": data.get("location_name"),
                "photo_url": data.get("photo_url"),
                "user_limit": data.get("user_limit"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
            })
            conn.commit()

        return {"message": "Event created successfully"}, 201

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@app.put("/events/<int:event_id>")
def update_event(event_id):
    """
    Update event details. Only event owner (user or org admin) can update.
    """
    try:
        user_id = verify_jwt()

        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400

        with engine.connect() as conn:
            # Check ownership and permissions
            check_event_ownership(conn, event_id, user_id)

            allowed_fields = {
                "title", "explanation", "price", "starts_at", "ends_at",
                "location_name", "photo_url", "status", "user_limit",
                "latitude", "longitude", "type_id"
            }
            updates = {k: v for k, v in data.items() if k in allowed_fields}

            if not updates:
                return {"error": "No valid fields to update"}, 400

            set_clause = ", ".join([f"{k} = :{k}" for k in updates])
            updates["id"] = event_id

            conn.execute(text(f"""
                UPDATE events
                SET {set_clause}, updated_at = NOW()
                WHERE id = :id
            """), updates)
            conn.commit()

        return {"message": "Event updated successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@app.delete("/events/<int:event_id>")
def delete_event(event_id):
    """
    Delete an event. Only the event owner (or org admin) can delete it.
    """
    try:
        user_id = verify_jwt()

        with engine.connect() as conn:
            # Check ownership and permissions
            check_event_ownership(conn, event_id, user_id)

            conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
            conn.commit()

        return {"message": "Event deleted successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/organizations")
def get_organizations():
    """List all organizations with member count and owner info."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
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
                ORDER BY o.name ASC
            """))
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/organizations/<int:org_id>")
def get_organization_by_id(org_id):
    """Get organization details with members and related events."""
    try:
        with engine.connect() as conn:
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
                WHERE o.id = :id
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


@app.post("/organizations")
def create_organization():
    """Create a new organization (only authenticated users)."""
    try:
        user_id = verify_jwt()

        data = request.get_json()
        if not data or "name" not in data:
            return {"error": "Organization name is required"}, 400

        with engine.connect() as conn:
            exists = conn.execute(text("SELECT id FROM organizations WHERE name = :n"), {"n": data["name"]}).fetchone()
            if exists:
                return {"error": "Organization name already exists"}, 409

            conn.execute(text("""
                INSERT INTO organizations (name, description, owner_user_id, photo_url, status, created_at, updated_at)
                VALUES (:name, :description, :owner_user_id, :photo_url, 'ACTIVE', NOW(), NOW())
            """), {
                "name": data["name"],
                "description": data.get("description"),
                "owner_user_id": user_id,
                "photo_url": data.get("photo_url")
            })
            conn.commit()

        return {"message": "Organization created successfully"}, 201
    
    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@app.post("/organizations/<int:org_id>/apply")
def apply_to_organization(org_id):
    """User applies to join an organization."""
    try:
        user_id = verify_jwt()

        data = request.get_json()
        motivation = data.get("motivation", "")

        with engine.connect() as conn:
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


@app.post("/organizations/<int:org_id>/applications/<int:app_id>/approve")
def approve_organization_application(org_id, app_id):
    """Approve a pending organization application (admin or representative only)."""
    try:
        user_id = verify_jwt()

        with engine.connect() as conn:
            # Check role
            check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

            app_row = conn.execute(text("""
                SELECT user_id FROM organization_applications
                WHERE id = :app_id AND organization_id = :oid AND status = 'PENDING'
            """), {"app_id": app_id, "oid": org_id}).fetchone()

            if not app_row:
                return {"error": "Application not found or already processed"}, 404

            applicant_id = app_row.user_id

            # Approve and move to members
            conn.execute(text("""
                UPDATE organization_applications SET status = 'APPROVED' WHERE id = :app_id
            """), {"app_id": app_id})
            conn.execute(text("""
                INSERT INTO organization_members (organization_id, user_id, role, joined_at)
                VALUES (:oid, :uid, 'MEMBER', NOW())
            """), {"oid": org_id, "uid": applicant_id})
            conn.commit()

        return {"message": "Application approved and member added"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@app.post("/organizations/<int:org_id>/applications/<int:app_id>/reject")
def reject_organization_application(org_id, app_id):
    """Reject a pending organization application (admin or representative only)."""
    try:
        user_id = verify_jwt()

        with engine.connect() as conn:
            # Check role
            check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

            app_row = conn.execute(text("""
                SELECT user_id FROM organization_applications
                WHERE id = :app_id AND organization_id = :oid AND status = 'PENDING'
            """), {"app_id": app_id, "oid": org_id}).fetchone()

            if not app_row:
                return {"error": "Application not found or already processed"}, 404

            # Reject the application
            conn.execute(text("""
                UPDATE organization_applications SET status = 'REJECTED' WHERE id = :app_id
            """), {"app_id": app_id})
            conn.commit()

        return {"message": "Application rejected successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@app.put("/organizations/<int:org_id>")
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

        with engine.connect() as conn:
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


@app.delete("/organizations/<int:org_id>")
def delete_organization(org_id):
    """Delete an organization (only owner or admin)."""
    try:
        user_id = verify_jwt()

        with engine.connect() as conn:
            # Check ownership/admin permissions
            check_organization_ownership(conn, org_id, user_id, allow_admin=True)

            conn.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": org_id})
            conn.commit()

        return {"message": "Organization deleted successfully"}

    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/organizations/<int:org_id>/applications")
def get_organization_applications(org_id):
    """List all applications for a specific organization (admin/representative only)."""
    try:
        user_id = verify_jwt()

        with engine.connect() as conn:
            # Role check
            check_organization_permission(conn, org_id, user_id, ["ADMIN", "REPRESENTATIVE"])

            result = conn.execute(text("""
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
            """), {"oid": org_id})

            rows = [dict(r._mapping) for r in result]

        return jsonify(rows)
    
    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503


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
