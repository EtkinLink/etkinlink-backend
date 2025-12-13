from flask import Blueprint, jsonify, request, current_app
import jwt
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from datetime import datetime, timedelta
from backend.utils.mail_service import generate_verification_token, verify_token, send_verification_email, send_password_reset_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Helper function
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


# Auth fonksiyonlari
@auth_bp.post("/register")
def register():
    engine = current_app.engine

    data = request.get_json()
    email = normalize_email(data.get("email", "").strip())
    password = data.get("password", "").strip()
    name = data.get("name", "").strip()
    
    # Get device and location info from request headers
    device_info = request.headers.get('User-Agent')
    # You might want to use a geolocation service here
    location_info = request.headers.get('X-Location')

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
                "username": email.split('@')[0],
                "university_id": university_id,
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Verification token oluştur
            token = generate_verification_token(payload)
            
            try:
                send_verification_email(
                    email, 
                    token,
                    device_info=device_info,
                    location_info=location_info
                )
                return {"message": "Verification email sent"}, 200
            except Exception as e:
                return {"error": f"Failed to send verification email: {str(e)}"}, 500

    except Exception as e:
        return {"error": f"Registration failed: {str(e)}"}, 503


@auth_bp.get("/register/verify/<token>")
def verify_email(token):
    engine = current_app.engine
    
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
                    INSERT INTO users (email, password_hash, name, username, university_id) 
                    VALUES (:email, :password, :name, :username, :university_id)
                """),
                {
                    "email": payload["email"],
                    "password": payload["password"],
                    "name": payload["name"],
                    "username": payload["username"],
                    "university_id": payload["university_id"]
                }
            )
            conn.commit()

            return {"message": "Account verified successfully"}, 200

    except Exception as e:
        return {"error": f"Verification failed: {str(e)}"}, 503


@auth_bp.post("/forgot-password")
def forgot_password():
    engine = current_app.engine
    
    data = request.get_json()
    email = data.get("email")
    
    normalized_email = normalize_email(email)
    
    if not normalized_email:
        return {"error": "Email is required"}, 400

    try:
        with engine.connect() as conn:
            user = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": normalized_email}
            ).fetchone()

            if not user:
                return {"error": "User not found"}, 404

            # Token oluştur
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)

            # DB Güncelle
            conn.execute(
                text("""
                    UPDATE users 
                    SET reset_password_token = :token, 
                        reset_password_expires = :expires 
                    WHERE email = :email
                """),
                {
                    "token": token,
                    "expires": expires_at,
                    "email": normalized_email
                }
            )
            conn.commit()
            
            # Mail Gönder (Pylance hatasını çözen kısım burası)
            try:
                send_password_reset_email(normalized_email, token)
                return {"message": "Password reset link sent to your email."}, 200
            except Exception as mail_error:
                return {"error": f"Failed to send email: {str(mail_error)}"}, 500

    except Exception as e:
        return {"error": str(e)}, 503


@auth_bp.post("/reset-password")
def reset_password_action():
    engine = current_app.engine
    
    data = request.get_json()
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return {"error": "Token and new password are required"}, 400
    
    if len(new_password) < 6:
        return {"error": "Password must be at least 6 characters"}, 400

    try:
        with engine.connect() as conn:
            user = conn.execute(
                text("""
                    SELECT id 
                    FROM users 
                    WHERE reset_password_token = :token 
                      AND reset_password_expires > NOW()
                """),
                {"token": token}
            ).fetchone()

            if not user:
                return {"error": "Invalid or expired token"}, 400

            new_hash = generate_password_hash(new_password)

            conn.execute(
                text("""
                    UPDATE users 
                    SET password_hash = :p_hash,
                        reset_password_token = NULL,
                        reset_password_expires = NULL
                    WHERE id = :uid
                """),
                {
                    "p_hash": new_hash,
                    "uid": user.id
                }
            )
            conn.commit()

            return {"message": "Password has been reset successfully."}, 200

    except Exception as e:
        return {"error": str(e)}, 503


@auth_bp.post("/login")
def login():
    engine = current_app.engine
    SECRET_KEY = current_app.config['SECRET_KEY']
    
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    normalized_email = normalize_email(email)

    if not normalized_email or not password:
        return {"error": "Email and password are required."}, 400

    try:
        with engine.connect() as conn:
            user_row = conn.execute(
                text("SELECT id, password_hash FROM users WHERE email = :email"),
                {"email": normalized_email}
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


@auth_bp.get("/me")
def get_current_user():
    """
    Get current user profile including role.
    Returns user information based on JWT token.
    """
    from backend.utils.auth_utils import verify_jwt, AuthError
    
    try:
        user_id = verify_jwt()
        
        with current_app.engine.connect() as conn:
            user = conn.execute(
                text("""
                    SELECT 
                        u.id,
                        u.username,
                        u.name,
                        u.email,
                        u.role,
                        u.university_id,
                        u.photo_url,
                        u.created_at,
                        u.is_blocked,
                        uni.name as university_name
                    FROM users u
                    LEFT JOIN universities uni ON u.university_id = uni.id
                    WHERE u.id = :id
                """),
                {"id": user_id}
            ).fetchone()
            
            if not user:
                return {"error": "User not found"}, 404
            
            return jsonify(dict(user._mapping))
    
    except AuthError as e:
        return {"error": e.args[0]}, e.code
    except Exception as e:
        return {"error": str(e)}, 503
