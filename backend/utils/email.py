from flask import current_app, url_for, render_template
from flask_mail import Message, Mail
from threading import Thread
import jwt
from datetime import datetime, timedelta

# Mail nesnesini global olarak tanımlamak yerine, 
# onu fonksiyonlar içinde current_app ile kullanacağız veya
# ana dosyadan (run.py) buraya import edip kullanacağız.

# Mail gönderme işlemini ayrı bir thread'de yapan yardımcı fonksiyon
def send_async_email(app, msg):
    # Uygulama bağlamına girilir. Flask-Mail, app.config'e erişebilir.
    with app.app_context():
        # Mail nesnesini bağlam içinde tekrar oluşturuyoruz veya ana dosyadan gelen
        # Mail nesnesini kullanıyoruz. En güvenli yol her zaman uygulamanın config'ini kullanmaktır.
        mail = Mail(app)
        try:
            mail.send(msg)
        except Exception as e:
            # Hata yakalama önemlidir!
            print(f"Mail gönderme hatası: {e}")


# Mail göndermeyi tetikleyen ana fonksiyon
# Bu fonksiyon, harici olarak bir Mail nesnesi (flask_mail.Mail) alabilir
# veya Thread'e sadece app objesini geçirip orada yeniden Mail objesi oluşturabilir.
def send_confirmation_email(user_email, subject, html_body):
    
    # current_app, bu fonksiyonun zaten bir Flask isteği (request) sırasında çağrıldığını varsayar.
    # Eğer bu fonksiyon bir dış betik tarafından çağrılacaksa (Flask isteği dışında)
    # uygulamanın bağlamını manuel olarak oluşturmanız gerekir. (Aşağıdaki notta açıklanmıştır.)
    app = current_app._get_current_object() # Güvenli bir şekilde çalışan uygulama nesnesini alır
    
    msg = Message(
        subject=subject,
        recipients=[user_email],
        html=html_body,
        sender=app.config['MAIL_DEFAULT_SENDER'] # Konfigürasyondan okur
    )
    
    # Maili ayrı bir thread'de gönderir
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

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