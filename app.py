import os
import json
import re
import requests
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
    s = s.strip().replace("−", "-").replace("–", "-")
    m = re.search(r"[+-]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group())
    except:
        return None

def get_asian_match_link(tr):
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
        return r.status_code < 400
    except:
        return False

def build_email(camp, sq_a, sq_b, minuto, risultato, bet, spread_cu, spread_op, total_cu, total_op, link_asian):
    return f"""
    NOME CAMPIONATO: {camp}<br>
    SQUADRA A: {sq_a}<br>
    SQUADRA B: {sq_b}<br>
    MINUTO: {minuto}'<br>
    RISULTATO LIVE: {risultato}<br>
    BET: {bet}<br><br>
    Link pagina match notificato:<br>
    <a href="{link_asian}" target="_blank">{link_asian}</a><br><br>
    <a href="{BWIN_BASE}" target="_blank">{BWIN_BASE}</a><br><br>
    TOTAL LINE CU: {total_cu}<br>
    TOTAL LINE OP: {total_op}<br>
    SPREAD CU: {spread_cu}<br>
    SPREAD OP: {spread_op}<br>
    """

def check_spread(cu, op):
    if cu is None or op is None:
        return False
    if cu > 0 and cu > op:
        return True
    if cu < 0 and cu < op:
        return True
    return False

def scan_livescore():
    db = load_db()
    found_now = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(ASIAN_URL, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all("tr")
    except Exception as e:
        print(f"FETCH ERROR {e}")
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
        risultato = f"{int(m_res.group(1))}-{int(m_res.group(2))}"
        if tr.find("img", src=lambda x: x and "red" in x.lower() if x else False):
            continue
        try:
            cols = [td.get_text(" ", strip=True) for td in tds]
            camp = cols[0] or "N/D"
            sq_a = cols[2] or "A"
            sq_b = cols[4] or "B"
            scu_raw = cols[5] or ""
            sop_raw = cols[6] or ""
            tcu_raw = cols[7] or ""
            top_raw = cols[8] or ""
            scu = parse_float(scu_raw)
            sop = parse_float(sop_raw)
            mid = f"{sq_a}-{sq_b}-{minuto}-{risultato}".replace(" ", "_")
            if any(x.get("id") == mid for x in db):
                continue

            bet = None
            regola = None

            if risultato == "0-0":
                if check_spread(scu, sop):
                    bet = "OVER 0.5"
                    regola = "R1"
            elif risultato == "1-0":
                if scu is not None and sop is not None:
                    if (scu > 0 and scu > sop and scu >= 0.75) or (scu < 0 and scu < sop and scu <= -0.75):
                        bet = "OVER 1.5"
                        regola = "R2"
            elif risultato == "0-1":
                if scu is not None and sop is not None:
                    if (scu > 0 and scu > sop and scu >= 0.75) or (scu < 0 and scu < sop and scu <= -0.75):
                        bet = "OVER 1.5"
                        regola = "R3"
            elif risultato == "1-1":
                if scu is not None and sop is not None:
                    if (scu > 0 and scu > sop and scu >= 1) or (scu < 0 and scu < sop and scu <= -1):
                        bet = "OVER 2.5"
                        regola = "R4"

            if bet:
                link = get_asian_match_link(tr)
                html = build_email(camp, sq_a, sq_b, minuto, risultato, bet, scu_raw, sop_raw, tcu_raw, top_raw, link)
                send_email(f"[{regola}] {sq_a} vs {sq_b} {risultato} {minuto}' {bet}", html)
                db.append({
                    "id": mid,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "campionato": camp,
                    "squadra_a": sq_a,
                    "squadra_b": sq_b,
                    "minuto": minuto,
                    "risultato_live": risultato,
                    "bet": bet,
                    "regola": regola,
                    "spread_cu": scu_raw,
                    "spread_op": sop_raw,
                    "total_cu": tcu_raw,
                    "total_op": top_raw,
                    "link_asian": link,
                    "esito": "PENDING"
                })
                found_now.append(mid)
        except Exception as e:
            continue

    save_db(db)
    return found_now

@app.route("/")
def home():
    db = load_db()
    return f"Bot 4 REGOLE ON - R1 0-0 OVER 0.5 | R2 1-0 OVER 1.5 | R3 0-1 OVER 1.5 | R4 1-1 OVER 2.5 - Tot:{len(db)}"

@app.route("/scan")
def scan():
    found = scan_livescore()
    return jsonify({"trovati": found, "tot_db": len(load_db())})

@app.route("/stats")
def stats():
    db = load_db()
    def cnt(r):
        return len([x for x in db if x.get("regola")==r])
    return jsonify({
        "totale": len(db),
        "R1_OVER_0.5": cnt("R1"),
        "R2_OVER_1.5": cnt("R2"),
        "R3_OVER_1.5": cnt("R3"),
        "R4_OVER_2.5": cnt("R4"),
        "dettaglio": db
    })

@app.route("/history")
def history():
    return jsonify(load_db())

@app.route("/test_mail")
def test_mail():
    html = build_email("TEST CAMPIONATO", "Team A", "Team B", 55, "0-0", "OVER 0.5 TEST R1", "-0.75", "-0.5", "2.5", "2.25", ASIAN_URL)
    send_email("[R1] TEST R1 - 0-0 OVER 0.5", html)
    return "ok R1 sent"

@app.route("/test_r2")
def test_r2():
    html = build_email("SERIE A TEST", "Juventus", "Inter", 55, "1-0", "OVER 1.5 TEST R2", "1.0", "0.5", "3.0", "2.75", ASIAN_URL)
    send_email("[R2] TEST R2 - 1-0 OVER 1.5", html)
    return "ok R2 sent"

@app.route("/test_r3")
def test_r3():
    html = build_email("PREMIER TEST", "Arsenal", "Chelsea", 58, "0-1", "OVER 1.5 TEST R3", "-0.75", "-0.25", "2.75", "2.5", ASIAN_URL)
    send_email("[R3] TEST R3 - 0-1 OVER 1.5", html)
    return "ok R3 sent"

@app.route("/test_r4")
def test_r4():
    html = build_email("BUNDESLIGA TEST", "Bayern", "Dortmund", 52, "1-1", "OVER 2.5 TEST R4", "-1.25", "-0.75", "4.0", "3.5", ASIAN_URL)
    send_email("[R4] TEST R4 - 1-1 OVER 2.5", html)
    return "ok R4 sent"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
