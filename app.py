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

ASIAN_URL = "https://www.asianbetsoccer.com/livescore.html"

# ---------- UTILS ----------
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

def send_email(subject, html_body):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}
    payload = {
        "sender": {"email": SENDER_EMAIL, "name": "Bot 3 Regole"},
        "to": [{"email": RECEIVER_EMAIL}],
        "subject": subject,
        "htmlContent": html_body
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"MAIL {subject} -> {r.status_code} {r.text[:200]}")
        return r.status_code < 400
    except Exception as e:
        print(f"MAIL ERROR: {e}")
        return False

def build_email(camp, sq_a, sq_b, minuto, risultato, bet, spread_cu, spread_op, total_cu, total_op, link_asian, link_bwin):
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
    {link_asian}<br><br>
    Link Bwin (ricerca diretta, se Bwin quota il match lo trovi subito):<br>
    <a href="{link_bwin}">{link_bwin}</a><br>
    """

# ---------- SCAN LOGIC ----------
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
        # Estrai minuto 50-60
        m_min = re.search(r"(\d+)\s*['′]", text_row)
        if not m_min:
            continue
        minuto = int(m_min.group(1))
        if not (50 <= minuto <= 60):
            continue

        # Estrai risultato tipo 0-0, 1-0, 0-1, 1-1
        m_res = re.search(r"(\d+)\s*-\s*(\d+)", text_row)
        if not m_res:
            continue
        gol_a = int(m_res.group(1))
        gol_b = int(m_res.group(2))
        risultato = f"{gol_a}-{gol_b}"

        # Rossi = 0 -> se nel row c'è icona rossa o testo (vedi allegato)
        # In asianbetsoccer rossi sono immagini / numeri rossi
        html_row = str(tr).lower()
        red_cards = 0
        # cerca tipo <span class="red"> o img red card
        if "red card" in html_row or "redcard" in html_row or "rcard" in html_row:
            # prova a contare
            reds_found = re.findall(r">\s*1\s*<.*red|red.*>\s*1", html_row)
            # fallback: se trova la parola rossa, conta occorrenze
            if html_row.count("red") > 2:
                red_cards = 1
        # Metodo più semplice: se nel testo c'è "0" rossi? Per sicurezza controlliamo colonne dedicate
        # Se nel row c'è un td con background rosso o con numero >0 vicino a risultato, lo consideriamo rosso
        # Per ora: se troviamo due numeri rossi, salta
        if "style" in html_row and "red" in html_row and re.search(r">\s*[12]\s*<", html_row):
            # euristica per evitare falsi positivi, controlla se c'è icona rossa
            if tr.find("span", style=lambda x: x and "red" in x.lower() if x else False):
                # se esiste ma è 0, è ok. Se è >0, salta
                pass
        
        # Controllo rosso finale: se nella riga c'è un immagine di cartellino rosso
        if tr.find("img", src=lambda x: x and "red" in x.lower() if x else False):
            red_cards = 1
        
        if red_cards != 0:
            continue

        # Estrazione squadre e campionato (euristica basata su ordine colonne asianbetsoccer)
        try:
            # asianbetsoccer structure: [0] league, [1] time, [2] teamA, [3] score, [4] teamB, ...
            # Proviamo a prendere testo pulito
            cols_text = [td.get_text(" ", strip=True) for td in tds]
            camp = cols_text[0] if cols_text[0] else "N/D"
            sq_a = cols_text[2] if len(cols_text) > 2 else "Squadra A"
            sq_b = cols_text[4] if len(cols_text) > 4 else "Squadra B"

            # SPREAD CU e OP: di solito colonne dopo squadre
            # Cerchiamo tutti i numeri float tipo -1, 0.75, 1.25 nelle colonne
            # Colonna CU riga A = primo spread CU trovato, Colonna OP riga A = primo spread OP trovato
            # Euristica: tds[5] = CU spread, tds[6]=OP spread, tds[7]=CU total, tds[8]=OP total
            spread_cu_raw = cols_text[5] if len(cols_text) > 5 else ""
            spread_op_raw = cols_text[6] if len(cols_text) > 6 else ""
            total_cu_raw = cols_text[7] if len(cols_text) > 7 else ""
            total_op_raw = cols_text[8] if len(cols_text) > 8 else ""

            spread_cu = parse_float(spread_cu_raw)
            spread_op = parse_float(spread_op_raw)
            total_cu = parse_float(total_cu_raw)
            total_op = parse_float(total_op_raw)

            # Se parsing fallisce, prova a cercare in tutta la riga
            if spread_cu is None:
                spread_cu = parse_float(text_row)
            if spread_cu is None or spread_op is None:
                floats = re.findall(r"[+-]?\d+(?:\.\d+)?", text_row)
                # prendi i primi 4 come CU, OP, CU total, OP total
                if len(floats) >= 4:
                    spread_cu = float(floats[0]) if spread_cu is None else spread_cu
                    spread_op = float(floats[1]) if spread_op is None else spread_op

            # Se ancora None, metti 0 per non rompere
            spread_cu_val = spread_cu if spread_cu is not None else 0.0
            spread_op_val = spread_op if spread_op is not None else 0.0

            # ID univoco per non ripetere
            match_id = f"{sq_a}-{sq_b}-{minuto}-{risultato}-{camp}".replace(" ", "_")
            if any(x.get("id") == match_id for x in db):
                continue

            bet = None
            regola = None

            # --- REGOLA 1: 0-0 50-60 ROSSI 0 ---
            if risultato == "0-0":
                bet = "OVER 1.5"
                regola = "R1"

            # --- REGOLA 2: 1-0 50-60 ROSSI 0 + CU>OP >=0.75 ---
            elif risultato == "1-0":
                if spread_cu_val is not None and spread_op_val is not None:
                    if (spread_cu_val - spread_op_val) >= 0.75 or (spread_cu_val > spread_op_val and spread_cu_val >= 0.75):
                        # compatibilità con logica vecchia CU>OP >=0.75
                        if spread_cu_val > spread_op_val:
                            bet = "OVER 1.5 [R2]"
                            regola = "R2"

            # --- REGOLA 3: 0-1 50-60 ROSSI 0 + CU>OP >=0.75 ---
            elif risultato == "0-1":
                if spread_cu_val is not None and spread_op_val is not None:
                    if spread_cu_val > spread_op_val:
                        diff = spread_cu_val - spread_op_val
                        if diff >= 0.75 or spread_cu_val >= 0.75:
                            bet = "OVER 1.5 [R3]"
                            regola = "R3"

            # --- REGOLA 4 NUOVA: 1-1 ---
            elif risultato == "1-1":
                # Condizione: CU riga A > OP riga A e >=1  OPPURE CU < OP e <= -1
                cond1 = (spread_cu_val > spread_op_val and spread_cu_val >= 1)
                cond2 = (spread_cu_val < spread_op_val and spread_cu_val <= -1)
                if cond1 or cond2:
                    bet = "OVER 2.5"
                    regola = "R4"

            if bet:
                link_asian = ASIAN_URL
                link_bwin = get_bwin_link(sq_a, sq_b)
                html_mail = build_email(camp, sq_a, sq_b, minuto, risultato, bet, spread_cu_raw, spread_op_raw, total_cu_raw, total_op_raw, link_asian, link_bwin)
                subject = f"[{regola}] {sq_a} vs {sq_b} {risultato} {minuto}' - {bet} - {camp}"
                send_email(subject, html_mail)

                entry = {
                    "id": match_id,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "campionato": camp,
                    "squadra_a": sq_a,
                    "squadra_b": sq_b,
                    "minuto": minuto,
                    "risultato_live": risultato,
                    "bet": bet,
                    "regola": regola,
                    "spread_cu": spread_cu_raw,
                    "spread_op": spread_op_raw,
                    "total_cu": total_cu_raw,
                    "total_op": total_op_raw,
                    "link_asian": link_asian,
                    "link_bwin": link_bwin,
                    "esito": "PENDING"
                }
                db.append(entry)
                found_now.append(entry)
        except Exception as e:
            print(f"PARSE ROW ERROR: {e}")
            continue

    save_db(db)
    return found_now

# ---------- ROUTES ----------
@app.route("/")
def home():
    db = load_db()
    v = len([x for x in db if x.get("esito") == "WIN"])
    p = len([x for x in db if x.get("esito") == "LOSE"])
    return f"Bot 4 REGOLE ON - Tot:{len(db)} V:{v} P:{p} - R4 1-1 OVER 2.5 attiva"

@app.route("/scan")
def scan():
    found = scan_livescore()
    return jsonify({"trovati": found, "tot_db": len(load_db())})

@app.route("/stats")
def stats():
    db = load_db()
    def cnt(reg, esito=None):
        fl = [x for x in db if x.get("regola")==reg]
        if esito:
            fl = [x for x in fl if x.get("esito")==esito]
        return len(fl)
    total = len(db)
    return jsonify({
        "tot": total,
        "R1": {"tot": cnt("R1"), "V": cnt("R1","WIN"), "P": cnt("R1","LOSE")},
        "R2": {"tot": cnt("R2"), "V": cnt("R2","WIN"), "P": cnt("R2","LOSE")},
        "R3": {"tot": cnt("R3"), "V": cnt("R3","WIN"), "P": cnt("R3","LOSE")},
        "R4": {"tot": cnt("R4"), "V": cnt("R4","WIN"), "P": cnt("R4","LOSE")},
    })

@app.route("/history")
def history():
    return jsonify(load_db())

@app.route("/check_results")
def check_results():
    # placeholder per controllo esiti finali - mantiene PENDING se non implementato
    return jsonify({"msg": "check_results OK", "tot": len(load_db())})

@app.route("/test_mail")
def test_mail():
    link_bwin = get_bwin_link("Team A Test", "Team B Test")
    html = build_email("CAMPIONATO TEST", "Team A", "Team B", 55, "1-1", "OVER 2.5 [TEST R4]", "-1.25", "-0.5", "2.75", "2.5", ASIAN_URL, link_bwin)
    send_email("TEST MAIL - Bot 4 REGOLE", html)
    return "Mail di test R4 inviata - controlla inbox e SPAM"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
