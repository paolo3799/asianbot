import time, threading, requests
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)

EMAIL = "paolo.zapp82@gmail.com"
TZ = pytz.timezone("Europe/Rome")

def send_email(subject, message):
    try:
        url = f"https://formsubmit.co/ajax/{EMAIL}"
        data = {
            "subject": subject,
            "_subject": subject,
            "message": message,
            "_template": "table",
            "_captcha": "false"
        }
        r = requests.post(url, data=data, timeout=15)
        print(f"EMAIL {r.status_code}: {r.text[:200]}")
        return True
    except Exception as e:
        print(f"Errore email: {e}")
        return False

def log(msg):
    print(f"[{datetime.now(TZ).strftime('%H:%M:%S')}] {msg}")

def check_matches():
    while True:
        try:
            log("Controllo partite...")
        except Exception as e:
            log(f"Errore: {e}")
        time.sleep(180)

threading.Thread(target=check_matches, daemon=True).start()

@app.route("/")
def home():
    return f"""
    <h2>BOT LIVE - PAOLO</h2>
    Email: {EMAIL}<br>
    Ora: {datetime.now(TZ)}<br><br>
    <a href='/test'>CLICCA QUI PER TEST MAIL</a><br>
    """

@app.route("/test")
def test():
    ok = send_email(
        subject="✅ TEST BOT ATTIVO - OVER 0.5",
        message=f"""Ciao Paolo,

Questo è il test del tuo bot asianbet.

Se leggi questa mail, funziona!

Bot: https://asianbot-ku6n.onrender.com
Ora test: {datetime.now(TZ)}

Prossime notifiche reali:
OVER 0.5 50-60' 0-0 con CU/OP filtrati

- Il tuo Bot Caorle
"""
    )
    if ok:
        return f"Test inviato a {EMAIL}!<br>Controlla posta e SPAM. Se è la prima volta, cerca mail da FormSubmit e clicca ACTIVATE poi rifai /test."
    else:
        return "Errore invio"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
