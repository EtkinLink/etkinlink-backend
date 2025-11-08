from flask import current_app, url_for, render_template
from flask_mail import Message, Mail
from threading import Thread
from datetime import datetime, timedelta
import os

def init_mail(app):
    """Mail konfigürasyonlarını yükle ve Mail nesnesini oluştur"""
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER')
    )
    return Mail(app)

def send_async_email(app, msg):
    with app.app_context():
        mail = Mail(app)
        mail.send(msg)

def send_confirmation_email(user_email, subject, html_body):
    msg = Message(subject,
                 recipients=[user_email],
                 html=html_body)
    
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start()
    
    return True

def generate_verification_token(payload):
    """Kullanıcı bilgileri için verification token oluşturur"""
    # Token'a expire time ekliyoruz (30 dakika)
    payload['exp'] = datetime.utcnow() + timedelta(minutes=30)
    # Token'ı oluştur
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

def send_verification_email(email, token):
    """Verification emaili gönder"""
    verification_url = url_for('verify_email', token=token, _external=True)
    subject = "EtkinLink - Email Doğrulama"
    
    # HTML template'i render et
    html_body = render_template('verification_email.html',
                              verification_url=verification_url)
    
    return send_confirmation_email(email, subject, html_body)