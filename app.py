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
        data = {"_subject": subject, "subject": subject, "message": message, "_template": "table", "_captcha": "false"}
        r = requests.post(url, data=data, timeout=20)
        print(f"MAIL {r.status_code}")
        return True
    except Exception as e:
        print(f"Errore: {e}")
        return False

threading.Thread(target=lambda: time.sleep(1), daemon=True).start()

@app.route("/")
def home():
    return f'<h2>BOT LIVE - EMAIL</h2>Email: {EMAIL}<br>Ora: {datetime.now(TZ)}<br><br><a href="/test">CLICCA QUI PER TEST MAIL</a>'

@app.route("/test")
def test():
    ok = send_email(
        "✅ TEST BOT PAOLO",
        f"Ciao Paolo! Test bot funzionante!\nOra: {datetime.now(TZ)}\nBot: https://asianbot-ku6n.onrender.com\nSe leggi questa, la mail va!"
    )
    return f"Test inviato a {EMAIL}!<br>Controlla posta e SPAM. Se è prima volta, apri mail FormSubmit e clicca ACTIVATE poi rifai /test."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
