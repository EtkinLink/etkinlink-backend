# utils/mail_service.py

import requests
from datetime import datetime, timedelta
from flask import current_app, url_for, render_template
import jwt

# Mailtrap REST API endpoint
MAILTRAP_SEND_URL = "https://send.api.mailtrap.io/api/send"


# -------------------------------------------------------------------
# Core email sender (Mailtrap REST API)
# -------------------------------------------------------------------
def send_email(to_email: str, subject: str, html_body: str):
    """
    Sends an email via Mailtrap REST API.
    Uses domain-based FROM address (no-reply@etkinlink.website).
    """

    token = current_app.config.get("MAILTRAP_API_TOKEN")
    from_email = current_app.config.get("MAIL_FROM_EMAIL")
    from_name = current_app.config.get("MAIL_FROM_NAME", "EtkinLink")

    if not token:
        raise RuntimeError("MAILTRAP_API_TOKEN is not configured")

    if not from_email:
        raise RuntimeError("MAIL_FROM_EMAIL is not configured")

    payload = {
        "from": {
            "email": from_email,
            "name": from_name
        },
        "to": [
            {"email": to_email}
        ],
        "subject": subject,
        "html": html_body
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        MAILTRAP_SEND_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    if not response.ok:
        raise RuntimeError(
            f"Mailtrap send failed ({response.status_code}): {response.text}"
        )

    return True


# -------------------------------------------------------------------
# Verification token helpers
# -------------------------------------------------------------------
def generate_verification_token(payload: dict, expires_minutes: int = 30):
    """
    Generates a JWT verification token with expiration.
    """

    payload = payload.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)

    token = jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return token


def verify_token(token: str):
    """
    Verifies JWT verification token and returns payload or None.
    """

    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=["HS256"]
        )
        return payload

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# -------------------------------------------------------------------
# Business emails
# -------------------------------------------------------------------
def send_verification_email(
    email: str,
    token: str,
    device_info: str | None = None,
    location_info: str | None = None
):
    """
    Sends email verification mail.
    """

    base_url = current_app.config.get("BACKEND_BASE_URL")

    if not base_url:
        raise RuntimeError("BACKEND_BASE_URL is not configured")

    verification_url = f"{base_url}/auth/register/verify/{token}"

    html_body = render_template(
        "verification_email.html",
        verification_url=verification_url,
        device_info=device_info or "-",
        location_info=location_info or "-",
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    return send_email(
        to_email=email,
        subject="EtkinLink - Email Doğrulama",
        html_body=html_body
    )



def send_password_reset_email(to_email: str, reset_token: str):
    """
    Sends password reset email.
    FRONTEND_URL is taken from app config.
    """

    frontend_url = current_app.config.get(
        "FRONTEND_URL",
        "http://localhost:3000"
    )

    reset_url = f"{frontend_url}/reset-password?token={reset_token}"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Şifrenizi mi unuttunuz?</h2>
        <p>Hesabınız için bir şifre sıfırlama talebi aldık.</p>
        <p>Şifrenizi yenilemek için aşağıdaki butona tıklayın:</p>
        <a href="{reset_url}"
           style="background-color: #4CAF50;
                  color: white;
                  padding: 10px 20px;
                  text-decoration: none;
                  border-radius: 5px;">
            Şifremi Sıfırla
        </a>
        <p>veya şu linki tarayıcınıza yapıştırın:</p>
        <p>{reset_url}</p>
        <p>Link 1 saat boyunca geçerlidir.</p>
    </div>
    """

    return send_email(
        to_email=to_email,
        subject="EtkinLink - Şifre Sıfırlama Talebi",
        html_body=html_body
    )