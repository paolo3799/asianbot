import requests
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)

# CONFIG
BREVO_API_KEY = "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"
FROM_EMAIL = "paolo.zapp82@gmail.com"
TO_EMAIL = "paolo.zapp82@yahoo.com"
TZ = pytz.timezone("Europe/Rome")

def invia_mail_brevo(oggetto, testo):
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
            "accept": "application/json"
        }
        data = {
            "sender": {"name": "AsianBot LIVE", "email": FROM_EMAIL},
            "to": [{"email": TO_EMAIL}],
            "subject": oggetto,
            "htmlContent": f"<html><body><h2>{oggetto}</h2><p>{testo.replace(chr(10), '<br>')}</p><p>Ora: {datetime.now(TZ)}</p></body></html>"
        }
        r = requests.post(url, json=data, headers=headers, timeout=20)
        return f"STATUS {r.status_code} - {r.text[:200]}"
    except Exception as e:
        return f"Errore: {e}"

@app.route("/")
def home():
    ora = datetime.now(TZ).strftime("%H:%M:%S")
    return f'BOT BREVO LIVE!<br>Da {FROM_EMAIL}<br>A {TO_EMAIL}<br>Ora {ora}<br><br><a href="/test"><b>CLICCA QUI PER TEST MAIL SU YAHOO</b></a>'

@app.route("/test")
def test():
    risultato = invia_mail_brevo(
        "TEST FINALE - BOT PAOLO FUNZIONA!",
        f"Ciao Paolo!\n\nSe leggi questa mail su Yahoo paolo.zapp82@yahoo.com, il bot via Brevo funziona al 100%!\n\nOra possiamo mettere il bot vero che controlla i gol asiatici ogni minuto!\n\nOra: {datetime.now(TZ)}"
    )
    return f"Invio a {TO_EMAIL}<br>Risultato Brevo: {risultato}<br><br>Controlla Yahoo Mail! Se vedi STATUS 201, la mail è partita!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
