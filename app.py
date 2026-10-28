import os
import json
import re
import requests
from flask import Flask, jsonify
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus

app = Flask(__name__)

DB_FILE = "pronostici.json"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "INSERISCI_QUI_LA_TUA_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "paolo.zapp82@yahoo.com")
RECEIVER_EMAIL = "paolo.zapp82@yahoo.com"

ASIAN_BASE = "https://www.asianbetsoccer.com"
ASIAN_URL = f"{ASIAN_BASE}/livescore.html"

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_float(s):
    if not s:
        return None
    s = s.strip().replace("−", "-")
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group())
    except:
        return None

def get_bwin_link(team_a, team_b):
    q = f"{team_a} {team_b}"
    return f"https://www.bwin.it/it/p/sports/search/?q={quote_plus(q)}"

def get_asian_match_link(tr):
    # Cerca link specifico del match nella riga
    for a in tr.find_all("a", href=True):
        href = a["href"]
        if ".html" in href and ("match" in href.lower() or "live" in href.lower() or "id=" in href.lower() or "game" in href.lower()):
            if href.startswith("http"):
                return href
            if href.startswith("/"):
                return ASIAN_BASE + href
            return ASIAN_BASE + "/" + href
    # fallback: cerca qualsiasi link .html nella riga
    for a in tr.find_all("a", href=True):
        href = a["href"]
        if ".html" in href:
            if href.startswith("http"):
                return href
            if href.startswith("/"):
                return ASIAN_BASE + href
            return ASIAN_BASE + "/" + href
    return ASIAN_URL

def send_email(subject, html_body):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}
    payload = {
        "sender": {"email": SENDER_EMAIL, "name": "Bot 4 Regole"},
        "to": [{"email": RECEIVER_EMAIL}],
        "subject": subject,
        "htmlContent": html_body
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"MAIL {subject} -> {r.status_code}")
        return r.status_code < 400
    except Exception as e:
        print(f"MAIL ERROR: {e}")
        return False

def build_email(camp, sq_a, sq_b, minuto, risultato, bet, spread_cu, spread_op, total_cu, total_op, link_asian, link_bwin):
    # ENTRAMBI I LINK ORA CLICCABILI E BLU
    return f"""
    NOME CAMPIONATO: {camp}<br>
    SQUADRA A: {sq_a}<br>
    SQUADRA B: {sq_b}<br>
    MINUTO: {minuto}'<br>
    RISULTATO LIVE: {risultato}<br>
    BET: {bet}<br><br>
    SPREAD CU: {spread_cu}<br>
    SPREAD OP: {spread_op}<br>
    TOTAL LINE CU: {total_cu}<br>
    TOTAL LINE OP: {total_op}<br><br>
    Link pagina asianbetsoccer.com del match notificato:<br>
    <a href="{link_asian}">{link_asian}</a><br><br>
    Link Bwin (ricerca diretta, se Bwin quota il match lo trovi subito):<br>
    <a href="{link_bwin}">{link_bwin}</a><br>
    """

def scan_livescore():
    db = load_db()
    found_now = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(ASIAN_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all("tr")
    except Exception as e:
        print(f"FETCH ERROR: {e}")
        return found_now

    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 10:
            continue
        text_row = tr.get_text(" ", strip=True)
        m_min = re.search(r"(\d+)\s*['′]", text_row)
        if not m_min:
            continue
        minuto = int(m_min.group(1))
        if not (50 <= minuto <= 60):
            continue

        m_res = re.search(r"(\d+)\s*-\s*(\d+)", text_row)
        if not m_res:
            continue
        gol_a = int(m_res.group(1))
        gol_b = int(m_res.group(2))
        risultato = f"{gol_a}-{gol_b}"

        # ROSSI = 0 (come da tuo screenshot allegato)
        if tr.find("img", src=lambda x: x and "red" in x.lower() if x else False):
            continue
        if tr.find("span", style=lambda x: x and "red" in x.lower() if x else False):
            txt_red = tr.find("span", style=lambda x: x and "red" in x.lower()).get_text()
            if parse_float(txt_red) and parse_float(txt_red) > 0:
                continue

       
