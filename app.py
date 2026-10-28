import requests
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)
EMAIL = "paolo.zapp82@yahoo.com"
ACCESS_KEY = "86f83f9e-055c-42bc-bf69-a2c23d7c86c1"
TZ = pytz.timezone("Europe/Rome")

@app.route("/")
def home():
    ora = datetime.now(TZ).strftime("%H:%M:%S")
    return f'BOT LIVE - YAHOO OK<br>{EMAIL}<br>Ora {ora}<br><br><a href="/test">CLICCA QUI TEST MAIL</a>'

@app.route("/test")
def test():
    try:
        r = requests.post("https://api.web3forms.com/submit", data={
            "access_key": ACCESS_KEY,
            "subject": "TEST BOT PAOLO - YAHOO FUNZIONA",
            "from_name": "AsianBot",
            "to": EMAIL,
            "message": f"Ciao Paolo! Test riuscito {datetime.now(TZ)} - Se leggi questo, Yahoo funziona!",
            "from": "bot@asianbot.com"
        }, timeout=15)
        return f"✅ Invio a {EMAIL}<br>Status: {r.status_code}<br>Risultato: {r.text}<br><br>Controlla Yahoo Mail ora! Posta in arrivo e SPAM"
    except Exception as e:
        return f"Errore: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
