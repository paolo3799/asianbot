import os, json, re, requests
from flask import Flask, jsonify
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

DB_FILE = "pronostici.json"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "paolo.zapp82@yahoo.com")
RECEIVER_EMAIL = "paolo.zapp82@yahoo.com"

ASIAN_BASE = "https://www.asianbetsoccer.com"
ASIAN_URL = f"{ASIAN_BASE}/livescore.html"
BWIN_BASE = "https://www.bwin.it/it/sports/live/"

def load_db():
    if not os.path.exists(DB_FILE): return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_float(s):
    if not s: return None
    s = s.strip().replace("\u2212", "-").replace("\u2013", "-")
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s)
    if not m: return None
    try: return float(m.group())
    except: return None

def get_asian_match_link(tr):
    for a in tr.find_all("a", href=True):
        href = a["href"]
        if ".html" in href:
            if href.startswith("http"): return href
            if href.startswith("/"): return ASIAN_BASE + href
            return ASIAN_BASE + "/" + href
    return ASIAN_URL

def send_email(subject, html_body):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}
    payload = {"sender": {"email": SENDER_EMAIL, "name": "Bot 4 Regole"}, "to": [{"email": RECEIVER_EMAIL}], "subject": subject, "htmlContent": html_body}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        return r.status_code < 400
    except: return False

def build_email(camp, sq_a, sq_b, minuto, risultato, bet, spread_cu, spread_op, total_cu, total_op, link_asian):
    return f"""NOME CAMPIONATO: {camp}<br>SQUADRA A: {sq_a}<br>SQUADRA B: {sq_b}<br>MINUTO: {minuto}'<br>RISULTATO LIVE: {risultato}<br>BET: {bet}<br><br>Link pagina match notificato:<br><a href="{link_asian}" target="_blank">{link_asian}</a><br><br><a href="{BWIN_BASE}" target="_blank">{BWIN_BASE}</a><br><br>TOTAL LINE CU: {total_cu}<br>TOTAL LINE OP: {total_op}<br>SPREAD CU: {spread_cu}<br>SPREAD OP: {spread_op}<br>"""

def check_spread(cu, op):
    if cu is None or op is None: return False
    if cu > 0 and cu > op: return True
    if cu < 0 and cu < op: return True
    return False

def scan_livescore():
    db = load_db(); found_now = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(ASIAN_URL, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all("tr")
    except: return found_now
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 10: continue
        text_row = tr.get_text(" ", strip=True)
        m_min = re.search(r"(\d+)\s*['\u2032]", text_row)
        if not m_min: continue
        minuto = int(m_min.group(1))
        if not (50 <= minuto <= 60): continue
        m_res = re.search(r"(\d+)\s*-\s*(\d+)", text_row)
        if not m_res: continue
        gol_a = int(m_res.group(1)); gol_b = int(m_res.group(2))
        risultato = f"{gol_a}-{gol_b}"
        if tr.find("img", src=lambda x: x and "red" in x.lower() if x else False): continue
        if "red card" in text_row.lower(): continue
        try:
            cols_text = [td.get_text(" ", strip=True) for td in tds]
            camp = cols_text[0] if cols_text[0] else "N/D"
            sq_a = cols_text[2] if len(cols_text) > 2 else "Squadra A"
            sq_b = cols_text[4] if len(cols_text) > 4 else "Squadra B"
            spread_cu_raw = cols_text[5] if len(cols_text) > 5 else ""
            spread_op_raw = cols_text[6] if len(cols_text) > 6 else ""
            total_cu_raw = cols_text[7] if len(cols_text) > 7 else ""
            total_op_raw = cols_text[8] if len(cols_text) > 8 else ""
            spread_cu = parse_float(spread_cu_raw); spread_op = parse_float(spread_op_raw)
            match_id = f"{sq_a}-{sq_b}-{minuto}-{risultato}".replace(" ", "_")
            if any(x.get("id") == match_id for x in db): continue
            bet = None; regola = None
            if risultato == "0-0":
                if check_spread(spread_cu, spread_op): bet = "OVER 0.5"; regola = "R1"
            elif risultato == "1-0":
                if spread_cu is not None and spread_op is not None:
                    if (spread_cu > 0 and spread_cu > spread_op and spread_cu >= 0.75) or (spread_cu < 0 and spread_cu < spread_op and spread_cu <= -0.75):
                        bet = "OVER 1.5"; regola = "R2"
            elif risultato == "0-1":
                if spread_cu is not None and spread_op is not None:
                    if (spread_cu > 0 and spread_cu > spread_op and spread_cu >= 0.75) or (spread_cu < 0 and spread_cu < spread_op and spread_cu <= -0.75):
                        bet = "OVER 1.5"; regola = "R3"
            elif risultato == "1-1":
                if spread_cu is not None and spread_op is not None:
                    if (spread_cu > 0 and spread_cu > spread_op and spread_cu >= 1) or (spread_cu < 0 and spread_cu < spread_op and spread_cu <= -1):
                        bet = "OVER 2.5"; regola = "R4"
            if bet:
               
