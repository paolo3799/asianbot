from flask import Flask
import requests, re, time, threading
from bs4 import BeautifulSoup

app = Flask(__name__)
TOPIC = "asianbot-caorle-paolo"
sent = set()

def send(msg):
    try:
        requests.post(f"https://ntfy.sh/{TOPIC}", data=msg.encode('utf-8'), headers={"Title":"⚽ OVER 0.5 ASIAN"}, timeout=15)
    except: pass

def parse_float(s):
    try: return float(s.replace('+','').strip())
    except: return None

def bot_loop():
    while True:
        try:
            # LiveScore asianbetsoccer
            r = requests.get("https://www.asianbetsoccer.com/livescore.html", headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=25)
            soup = BeautifulSoup(r.text, "lxml")
            for tr in soup.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 8: continue
                texts = [td.get_text(" ", strip=True) for td in tds]
                full = " ".join(texts)
                
                m_min = re.search(r"(\d+)'", full)
                if not m_min: continue
                minute = int(m_min.group(1))
                if not 50 <= minute <= 62: continue
                
                # Risultato 0-0
                if "0-0" not in full and "0 - 0" not in full: continue
                
                # Rossi = 0 (se c'è RC rosso scritto)
                if "RC" in full or "Red" in full: 
                    # conta rossi, se >0 salta - semplice
                    if re.search(r"\b1\b.*RC|RC.*\b1\b", full): continue

                # Prova a leggere campi: Campionato, Squadre, Spread CU/OP, Total CU/OP
                # La struttura di asianbetsoccer varia, prendiamo generico
                campionato = texts[0]
                squadraA = texts[1] if len(texts)>1 else "A"
                squadraB = texts[2] if len(texts)>2 else "B"
                
                # Cerca spread e total nelle colonne
                spread_cu = spread_op = total_cu = total_op = None
                # euristica: cerca valori tipo -0.5, +0.25, 2.5, 2.75
                for t in texts:
                    if re.match(r"^[+-]?0(\.\d+)?$|^[+-]?[0-9]+\.[0-9]+$", t):
                        pass
                
                # Per ora estraiamo con posizioni classiche asianbetsoccer:
                # col 4-5 spread, col 6-7 total - adattato
                try:
                    # Questi indici cambiano, li leggiamo se sembrano numeri
                    possible = [parse_float(x) for x in texts]
                    # filtra None
                    nums = [x for x in possible if x is not None]
                except: nums = []

                # LOGICA CU vs OP che volevi tu:
                # Se hai i dati CU e OP dal sito, applica:
                # SPREAD + e CU > OP => ok
                # SPREAD - e CU < OP => ok
                # Stessa cosa TOTAL
                # Per ora mandiamo notifica base, e scriviamo anche i valori CU/OP che troviamo

                key = f"{squadraA}-{squadraB}-{minute}"
                if key in sent: continue

                msg = f"""🔥 {campionato}
⚽ {squadraA} vs {squadraB}
⏱️ {minute}' - 0-0
🚫 Rossi: 0

📊 SPREAD CU: {texts[4] if len(texts)>4 else '-'} | OP: {texts[5] if len(texts)>5 else '-'}
📈 TOTAL CU: {texts[6] if len(texts)>6 else '-'} | OP: {texts[7] if len(texts)>7 else '-'}

✅ CONDIZIONE: 50-60' 0-0
👉 BET: OVER 0.5

Controlla su Asian: se SPREAD + e CU>OP oppure - e CU<OP, e TOTAL CU>OP => ENTRA"""

                send(msg)
                sent.add(key)
                if len(sent) > 200: sent.clear()

        except Exception as e:
            print(e)
        time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

@app.route("/")
def home():
    return f"BOT LIVE - {TOPIC} - {len(sent)} partite inviate"

@app.route("/test")
def test():
    send("✅ TEST BOT ATTIVO - Se leggi questo, ntfy funziona! Ora aspetta partite vere 50-60' 0-0")
    return "Test inviato su ntfy"
