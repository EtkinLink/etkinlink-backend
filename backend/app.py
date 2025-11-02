from datetime import datetime, timedelta
from functools import wraps
import os
import re

from flask import Flask, jsonify, request
from flask_cors import CORS
import jwt
from sqlalchemy import create_engine, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
CORS(app)

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
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    username = data.get("username")
    name = data.get("name")
    if not email or not password or not username or not name:
        return {"error": "Missing fields."}, 400

    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT id FROM users WHERE email = :email OR username = :username"),
                {"email": email, "username": username}
            ).fetchone()

            if exists:
                return {"error": "Email or username already in use."}, 409

            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            try:
                domain = email.split('@')[1].lower()
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

            conn.execute(
                text("""
                    INSERT INTO users (name, username, email, password_hash, role, university_id)
                    VALUES (:name, :username, :email, :password_hash, :role, :university_id)
                """),
                {
                    "name": name,
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "role": "USER",
                    "university_id": university_id
                }
            )
            conn.commit()

        return {"message": "Registration successful."}, 201
    except Exception as e:
        return {"error": str(e)}, 503

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
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    e.id, e.title, e.explanation, e.price, e.starts_at, e.ends_at, e.location_name ,e.status,
                    e.user_limit, e.latitude, e.longitude, e.created_at, e.updated_at,
                    u.username AS owner_username,
                    et.code AS event_type,
                    (SELECT COUNT(*) FROM participants p WHERE p.event_id = e.id) AS participant_count
                FROM events e
                LEFT JOIN users u ON e.owner_user_id = u.id
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
    try:
        with engine.connect() as conn:
            event = conn.execute(text("""
                SELECT 
                    e.id, e.title, e.explanation, e.price, e.starts_at,e.ends_at, e.location_name, e.status,
                    e.user_limit, e.latitude, e.longitude, e.created_at, e.updated_at,
                    u.username AS owner_username,
                    et.code AS event_type
                FROM events e
                LEFT JOIN users u ON e.owner_user_id = u.id
                LEFT JOIN event_types et ON e.type_id = et.id
                WHERE e.id = :id
            """), {"id": event_id}).fetchone()

            if not event:
                return {"error": "Event not found"}, 404

            participants = conn.execute(text("""
                SELECT u.id, u.username, p.status
                FROM participants p
                JOIN users u ON u.id = p.user_id
                WHERE p.event_id = :id
            """), {"id": event_id}).fetchall()

        event_data = dict(event._mapping)
        event_data["participants"] = [dict(p._mapping) for p in participants]
        return jsonify(event_data)
    except Exception as e:
        return {"error": str(e)}, 503


@app.get("/events/filter")
def filter_events():
    try:
        type_code = request.args.get("type")
        from_date = request.args.get("from")
        to_date = request.args.get("to")
        search = request.args.get("q")

        filters = []
        params = {}

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
            filters.append("e.title LIKE :search")
            params["search"] = f"%{search}%"

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        with engine.connect() as conn:
            query = text(f"""
                SELECT 
                    e.id, e.title, e.starts_at,e.ends_at,e.location_name, e.status, e.created_at ,et.code AS event_type, 
                    u.username AS owner_username
                FROM events e
                LEFT JOIN event_types et ON e.type_id = et.id
                LEFT JOIN users u ON e.owner_user_id = u.id
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
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    e.id, e.title, e.starts_at, e.ends_at, e.location_name ,e.status, e.created_at,
                    et.code AS event_type,
                    p.status AS participation_status
                FROM participants p
                JOIN events e ON e.id = p.event_id
                LEFT JOIN event_types et ON e.type_id = et.id
                WHERE p.user_id = :uid
                ORDER BY e.starts_at DESC
            """)
            result = conn.execute(query, {"uid": user_id})
            rows = [dict(r._mapping) for r in result]
        return jsonify(rows)
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
