import requests
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)
EMAIL = "paolo.zapp82@gmail.com"
TZ = pytz.timezone("Europe/Rome")

def send_email(subject, message):
    url = f"https://formsubmit.co/ajax/{EMAIL}"
    data = {
        "_subject": subject,
        "subject": subject,
        "message": message,
        "_template": "table",
        "_captcha": "false"
    }
    requests.post(url, data=data, timeout=15)

@app.route("/")
def home():
    ora = datetime.now(TZ).strftime("%H:%M:%S")
    return f'BOT LIVE - EMAIL OK<br>Email: {EMAIL}<br>Ora: {ora}<br><br><a href="/test">CLICCA QUI PER TEST MAIL</a>'

@app.route("/test")
def test():
    ora = datetime.now(TZ).strftime("%d/%m %H:%M")
    send_email("TEST BOT PAOLO OK", f"Ciao Paolo! Test riuscito! Ora {ora}. Bot https://asianbot-ku6n.onrender.com")
    return f'Test inviato a {EMAIL}!<br><br>Controlla posta e SPAM.<br>Prima mail da FormSubmit: clicca ACTIVATE, poi rifai /test'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
