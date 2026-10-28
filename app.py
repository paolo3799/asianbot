from flask import Flask
import requests, re, time, threading
from bs4 import BeautifulSoup

app = Flask(__name__)
TOPIC = "asianbot-caorle-paolo"

def send(msg):
    try:
        requests.post(f"https://ntfy.sh/{TOPIC}", data=msg.encode(), timeout=10)
    except: pass

def bot():
    while True:
        try:
            r = requests.get("https://www.asianbetsoccer.com/livescore.html", headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for tr in soup.find_all("tr"):
                txt = tr.get_text(" ", strip=True)
                m = re.search(r"(\d+)'", txt)
                if not m: continue
                minute = int(m.group(1))
                if not 50 <= minute <= 60: continue
                if "0-0" not in txt and "0 - 0" not in txt: continue
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(tds) < 5: continue
                campionato = tds[0] if len(tds)>0 else ""
                squadraA = tds[1] if len(tds)>1 else ""
                squadraB = tds[2] if len(tds)>2 else ""
                msg = f"NOME CAMPIONATO: {campionato}\nSQUADRA A: {squadraA}\nSQUADRA B: {squadraB}\nMINUTO: {minute}'\nRISULTATO: 0-0\nBET: OVER 0.5"
                send(msg)
        except: pass
        time.sleep(90)

threading.Thread(target=bot, daemon=True).start()

@app.route("/")
def home():
    return f"BOT ATTIVO - topic ntfy: {TOPIC}"
