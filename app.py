import requests
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)
EMAIL = "paolo.zapp82@yahoo.com"
TZ = pytz.timezone("Europe/Rome")

@app.route("/")
def home():
    ora = datetime.now(TZ).strftime("%H:%M:%S")
    return f'BOT LIVE OK - YAHOO<br>{EMAIL}<br>Ora {ora}<br><br><a href="/test">CLICCA QUI PER TEST MAIL</a>'

@app.route("/test")
def test():
    try:
        url = f"https://formsubmit.co/ajax/{EMAIL}"
        data = {
            "_subject": "TEST BOT PAOLO - YAHOO OK",
            "subject": "TEST BOT PAOLO",
            "message": f"Ciao Paolo! Test riuscito delle {datetime.now(TZ)} - Yahoo funziona!",
            "_template": "table",
            "_captcha": "false"
        }
        r = requests.post(url, data=data, timeout=15)
        return f"✅ Test inviato a {EMAIL}!<br>Status: {r.status_code}<br>Risposta: {r.text[:300]}<br><br>Ora vai su Yahoo Mail e controlla Posta in arrivo e SPAM!"
    except Exception as e:
        return f"Errore: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
