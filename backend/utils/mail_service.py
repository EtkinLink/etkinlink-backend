from flask import current_app, url_for, render_template
from flask_mail import Message, Mail
from threading import Thread
from datetime import datetime, timedelta
import os
from queue import Queue
import jwt

# Email sonuçlarını tutmak için global queue
email_status_queue = Queue()

def init_mail(app):
    """Mail konfigürasyonlarını yükle ve Mail nesnesini oluştur"""
    # Config zaten app.config'de yüklü olmalı
    return Mail(app)

def send_async_email(app, msg, queue):
    """Asenkron email gönderimi ve sonucu queue'ya ekle"""
    try:
        with app.app_context():
            mail = Mail(app)
            mail.send(msg)
            queue.put({"success": True, "message": "Email sent successfully"})
    except Exception as e:
        queue.put({"success": False, "message": str(e)})

def send_confirmation_email(user_email, subject, html_body):
    """Email gönder ve sonucu kontrol et"""
    msg = Message(subject,
                 recipients=[user_email],
                 html=html_body)
    
    # Email gönderimi için yeni thread başlat
    thread = Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg, email_status_queue)
    )
    thread.start()
    
    # Maksimum 5 saniye bekle
    try:
        result = email_status_queue.get(timeout=5)
        if not result["success"]:
            raise Exception(f"Email sending failed: {result['message']}")
        return True
    except Exception as e:
        raise Exception(f"Email sending failed: {str(e)}")

def generate_verification_token(payload):
    """Kullanıcı bilgileri için verification token oluşturur"""
    payload['exp'] = datetime.utcnow() + timedelta(minutes=30)
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

def verify_token(token):
    """Token'ı doğrula ve payload'ı döndür"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def send_verification_email(email, token, device_info=None, location_info=None):
    """Verification emaili gönder ve sonucu kontrol et"""
    try:
        verification_url = url_for('verify_email', token=token, _external=True)
        subject = "EtkinLink - Email Doğrulama"
        
        device_info = device_info or "-"
        location_info = location_info or "-"
        
        html_body = render_template('verification_email.html',
                                  verification_url=verification_url,
                                  device_info=device_info,
                                  location_info=location_info,
                                  timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
        
        return send_confirmation_email(email, subject, html_body)
    except Exception as e:
        raise Exception(f"Verification email failed: {str(e)}")

def send_password_reset_email(to_email, reset_token):
    """
    Şifre sıfırlama maili gönderir.
    Backend'de oluşturulan 'secrets' token'ını kullanır.
    FRONTEND_URL ortam değişkenini kullanır, yoksa localhost'a düşer.
    """
    # Get FRONTEND_URL from app config
    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
    reset_url = f"{frontend_url}/reset-password?token={reset_token}"
    
    subject = "EtkinLink - Şifre Sıfırlama Talebi"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Şifrenizi mi unuttunuz?</h2>
        <p>Hesabınız için bir şifre sıfırlama talebi aldık.</p>
        <p>Şifrenizi yenilemek için aşağıdaki butona tıklayın:</p>
        <a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Şifremi Sıfırla
        </a>
        <p>veya şu linki tarayıcınıza yapıştırın:</p>
        <p>{reset_url}</p>
        <p>Link 1 saat boyunca geçerlidir.</p>
    </div>
    """
    
    return send_confirmation_email(to_email, subject, html_body)