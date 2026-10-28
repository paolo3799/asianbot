import os
import re
import requests
from flask import Flask
from bs4 import BeautifulSoup

app = Flask(__name__)

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
FROM_EMAIL = "paolo.zapp82@yahoo.com"
TO_EMAIL = "paolo.zapp82@yahoo.com"
inviate = set()

def send_email(subject, html):
    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
            json={
                "sender": {"name": "AsianBot", "email": FROM_EMAIL},
                "to": [{"email": TO_EMAIL}],
                "subject": subject,
                "htmlContent": html
            },
            timeout=15
        )
        return r.status_code in [200,201,202]
    except Exception as e:
        print(f"Mail error {e}")
        return False

def parse_float(v):
    try:
        m = re.search(r'[-+]?\d*\.?\d+', str(v).replace(',', '.'))
        if m:
            return float(m.group())
    except:
        pass
    return None

def check_cu_op(cu, op):
    if cu is None or op is None:
        return False
    if cu > 0 and op > 0:
        return cu > op
    if cu < 0 and op < 0:
        return cu < op
    return False

@app.route("/")
def home():
    return 'AsianBot OK - <a href="/test">TEST MAIL</a> | <a href="/scan">SCAN LIVESCORE</a>'

@app.route("/test")
def test():
    ok = send_email("TEST BOT OK", "Deploy leggero funziona su yahoo")
    return f"Mail inviata? {ok}"

@app.route("/scan")
def scan():
    url = "https://www.asianbetsoccer.com/livescore.html"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.asianbetsoccer.com/"
        }
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        trovati = []
        for tr in soup.find_all('tr'):
            cols = tr.find_all('td')
            if len(cols) < 7:
                continue
            txt = tr.get_text(" ", strip=True)
            m = re.search(r"(\d+)'", txt)
            if not m:
                continue
            minuto = int(m.group(1))
            if not (50 <= minuto <= 60):
                continue
            if "0-0" not in txt and "0 - 0" not in txt:
                continue
            cu_raw = cols[6].get_text(strip=True) if len(cols) > 6 else ""
            op_raw = cols[7].get_text(strip=True) if len(cols) > 7 else ""
            cu = parse_float(cu_raw.split('/')[0])
            op = parse_float(op_raw.split('/')[0])
            if not check_cu_op(cu, op):
                continue
            campionato = cols[1].get_text(strip=True) if len(cols) > 1 else "N/A"
            squadre = cols[2].get_text(" vs ", strip=True)
            link = url
            mid = f"{squadre}-{minuto}"
            if mid in inviate:
                continue
            inviate.add(mid)
            html = f"CAMPIONATO: {campionato}<br>SQUADRE: {squadre}<br>MINUTO: {minuto}<br>RISULTATO: 0-0<br>BET: OVER 0.5<br>SPREAD CU: {cu_raw}<br>SPREAD OP: {op_raw}<br>Link: {link}"
            send_email(f"OVER 0.5 {squadre} {minuto}'", html)
            trovati.append(squadre)
        return f"Scan ok. Trovati: {trovati}"
    except Exception as e:
        return f"Errore scan: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
