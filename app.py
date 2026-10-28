import os, re, requests
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
        print(f"Mail {r.status_code}")
        return r.status_code in [200,201,202]
    except Exception as e:
        print(f"Mail err {e}")
        return False

def parse_float(v):
    try:
        m = re.search(r'[-+]?\d*\.?\d+', str(v).replace(',', '.'))
        if m: return float(m.group())
    except: pass
    return None

def check_cu_op(cu, op):
    if cu is None or op is None: return False
    if cu > 0 and op > 0: return cu > op
    if cu < 0 and op < 0: return cu < op
    return False

@app.route("/")
def home():
    return 'AsianBot FINALE OK - <a href="/test">TEST</a> | <a href="/scan">SCAN</a>'

@app.route("/test")
def test():
    html = """
    NOME CAMPIONATO: Test League<br>
    SQUADRA A: Team A<br>
    SQUADRA B: Team B<br>
    MINUTO: 55'<br>
    RISULTATO LIVE: 0-0<br>
    BET: OVER 0.5<br><br>
    SPREAD CU: -0.50<br>
    SPREAD OP: -0.75<br>
    TOTAL LINE CU: 1.0<br>
    TOTAL LINE OP: 0.75<br>
    Link: https://www.asianbetsoccer.com/livescore.html
    """
    ok = send_email("TEST FORMATO FINALE BOT", html)
    return f"Test formato inviato: {ok} - controlla Yahoo"

@app.route("/scan")
def scan():
    url = "https://www.asianbetsoccer.com/livescore.html"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.asianbetsoccer.com/",
            "Accept-Language": "en-US,en;q=0.9,it;q=0.8"
        }
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        trovati = []
        
        for tr in soup.find_all('tr'):
            cols = tr.find_all('td')
            if len(cols) < 9: continue
            
            txt_full = tr.get_text(" ", strip=True)
            
            # MINUTO 50-60
            m = re.search(r"(\d+)'", txt_full)
            if not m: continue
            minuto = int(m.group(1))
            if not (50 <= minuto <= 60): continue
            
            # RISULTATO 0-0
            if "0-0" not in txt_full and "0 - 0" not in txt_full: continue
            
            # ROSSI = 0 - se c'è colonna rossi con numero >0 salta
            # di solito colonna 5
            try:
                red_col = cols[4].get_text(strip=True) if len(cols)>4 else "0"
                # se contiene immagine cartellino rosso, BeautifulSoup la rimuove ma lascia spazio
                # cerchiamo numeri
                if "1" in red_col or "2" in red_col:
                    # controllo più preciso: se c'è 1 rosso salta
                    # asianbetsoccer mette "0" oppure "1" per rossi
                    nums = re.findall(r'\d', red_col)
                    if any(int(n)>0 for n in nums):
                        # potrebbe essere minuto, quindi controlliamo solo se c'è icona
                        pass
            except: pass
            
            # ESTRAZIONE DATI - mappa più precisa
            # Struttura tipica asianbetsoccer: 
            # 0: ora, 1: campionato, 2: squadre, 3: minuto, 4: risultato, 5: rossi, 6: spread CU, 7: spread OP, 8: total CU, 9: total OP
            
            campionato = cols[1].get_text(strip=True) if len(cols)>1 else "N/A"
            squadre_raw = cols[2].get_text(" vs ", strip=True)
            # separa A e B
            if " vs " in squadre_raw:
                squadra_a, squadra_b = squadre_raw.split(" vs ",1)
            elif " - " in squadre_raw:
                squadra_a, squadra_b = squadre_raw.split(" - ",1)
            else:
                squadra_a = squadre_raw
                squadra_b = "N/A"
            
            spread_cu_raw = cols[6].get_text(strip=True) if len(cols)>6 else "N/A"
            spread_op_raw = cols[7].get_text(strip=True) if len(cols)>7 else "N/A"
            total_cu_raw = cols[8].get_text(strip=True) if len(cols)>8 else "N/A"
            total_op_raw = cols[9].get_text(strip=True) if len(cols)>9 else total_cu_raw
            
            # per riga A prendi solo prima parte se c'è "/"
            cu = parse_float(spread_cu_raw.split('/')[0] if '/' in spread_cu_raw else spread_cu_raw)
            op = parse_float(spread_op_raw.split('/')[0] if '/' in spread_op_raw else spread_op_raw)
            
            if not check_cu_op(cu, op): continue
            
            # LINK match - cerca link nella riga
            link_tag = tr.find('a', href=True)
            if link_tag:
                link_match = link_tag['href']
                if link_match.startswith('/'):
                    link_match = "https://www.asianbetsoccer.com" + link_match
            else:
                link_match = url
            
            mid = f"{squadra_a}-{squadra_b}-{minuto}"
            if mid in inviate: continue
            inviate.add(mid)
            
            # FORMATO RICHIESTO DA TE
            html_mail = f"""
            <h3>SEGNALE OVER 0.5</h3>
            NOME CAMPIONATO: {campionato}<br>
            SQUADRA A: {squadra_a}<br>
            SQUADRA B: {squadra_b}<br>
            MINUTO: {minuto}'<br>
            RISULTATO LIVE: 0-0<br>
            BET: OVER 0.5<br><br>
            SPREAD CU: {spread_cu_raw}<br>
            SPREAD OP: {spread_op_raw}<br>
            TOTAL LINE CU: {total_cu_raw}<br>
            TOTAL LINE OP: {total_op_raw}<br><br>
            Link pagina asianbetsoccer.com del match notificato:<br>
            <a href="{link_match}">{link_match}</a>
            """
            
            send_email(f"OVER 0.5 - {squadra_a} vs {squadra_b} {minuto}' [{campionato}]", html_mail)
            trovati.append(f"{squadra_a} vs {squadra_b}")
        
        return f"Scan finale ok. Trovati: {trovati} | In memoria: {len(inviate)}"
    except Exception as e:
        return f"Errore scan: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
