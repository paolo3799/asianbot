import requests, os
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)

FROM_EMAIL = "paolo.zapp82@yahoo.com"
TO_EMAIL = "paolo.zapp82@yahoo.com"
TZ = pytz.timezone("Europe/Rome")

def invia_mail_brevo(oggetto, testo):
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    if not BREVO_API_KEY:
        return "ERRORE: Manca BREVO_API_KEY su Render Environment"
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json", "accept": "application/json"}
    data = {
        "sender": {"name": "AsianBot LIVE", "email": FROM_EMAIL},
        "to": [{"email": TO_EMAIL}],
        "subject": oggetto,
        "htmlContent": f"<html><body><h2>{oggetto}</h2><p>{testo.replace(chr(10), '<br>')}</p></body></html>"
    }
    r = requests.post(url, json=data, headers=headers, timeout=20)
    return f"STATUS {r.status_code} - {r.text[:300]}"

@app.route("/")
def home():
    return f'BOT SICURO<br><a href="/test">CLICCA QUI PER TEST YAHOO</a>'

@app.route("/test")
def test():
    ris = invia_mail_brevo("TEST FINALE BOT PAOLO - CHIAVE NUOVA", f"Test ore {datetime.now(TZ)}")
    return f"Risultato: {ris}<br><br>Se vedi 201, controlla Yahoo!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
