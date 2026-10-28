import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)

# CREDENZIALI
GMAIL_USER = "paolo.zapp82@gmail.com"
GMAIL_PASS = "pdbhgpljsxbwlrgd"  # la tua app password senza spazi
TO_EMAIL = "paolo.zapp82@yahoo.com"
TZ = pytz.timezone("Europe/Rome")

def invia_mail(oggetto, testo):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = TO_EMAIL
        msg['Subject'] = oggetto
        msg.attach(MIMEText(testo, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return "OK - Mail inviata via Gmail!"
    except Exception as e:
        return f"Errore: {e}"

@app.route("/")
def home():
    ora = datetime.now(TZ).strftime("%H:%M:%S")
    return f'BOT LIVE - GMAIL SMTP OK<br>Da {GMAIL_USER}<br>A {TO_EMAIL}<br>Ora {ora}<br><br><a href="/test">CLICCA QUI PER TEST MAIL</a>'

@app.route("/test")
def test():
    risultato = invia_mail(
        "TEST BOT PAOLO - GMAIL FUNZIONA!", 
        f"Ciao Paolo!\n\nTest riuscito alle {datetime.now(TZ)}\n\nSe leggi questa mail su Yahoo, il sistema GMAIL SMTP funziona perfettamente!\n\nOra possiamo mettere il bot vero delle partite asiatiche!"
    )
    return f"Invio a {TO_EMAIL}<br>Risultato: {risultato}<br><br>Vai su Yahoo Mail e controlla! Deve arrivare in 10 secondi!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
