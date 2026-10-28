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
        print(f"Mail {r.status_code}")
        return r.status_code in [200,201,202]
    except Exception as e:
        print(f"Mail err {e}")
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
    return 'AsianBot FINALE OK - <a href="/test">TEST MAIL</a> | <a href="/scan">SCAN LIVESCORE</a>'

@app.route("/test")
def test():
    # Dati test con link editabile
    campionato = "Test League"
    squadra_a = "Team A"
    squadra_b = "Team B"
    minuto = 55
    spread_cu_raw = "-0.50"
    spread_op_raw = "-0.75"
    total_cu_raw = "1.0"
    total_op_raw = "0.75"
    
    link_diretto = "https://www.asianbetsoccer.com/livescore.html#Team%20A-vs-Team%20B"
    link_editabile = link_diretto
    link_google = "https://www.google.com/search?q=Team%20A+vs+Team%20B+live"

    html = f"""
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
    <a href="{link_diretto}">{link_diretto}</a><br><br>
    Link editabile (copia e incolla):<br>
    {link_editabile}<br><br>
    Verifica rapida:<br>
    <a href="{link_google}">{link_google}</a>
    """
    ok = send_email("TEST FORMATO FINALE BOT - Link Editabile", html)
    return f"Test inviato: {ok} - Controlla Yahoo, ora hai link blu + link testo copiabile"

@app.route("/scan")
def scan():
    url = "https://www.asianbetsoccer.com/livescore.html"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.asianbetsoccer.com/",
            "Accept-Language": "en-US,en;q=0.9,it;q=0.8"
        }
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        trovati = []
        
        for tr in soup.find_all('tr'):
            cols = tr.find_all('td')
            if len(cols) < 9: 
                continue
            
            txt_full = tr.get_text(" ", strip=True)
            
            m = re.search(r"(\d+)'", txt_full)
            if not m: 
                continue
            minuto = int(m.group(1))
            if not (50 <= minuto <= 60): 
                continue
            
            if "0-0" not in txt_full and "0 - 0" not in txt_full: 
                continue
            
            campionato = cols[1].get_text(strip=True) if len(cols)>1 else "N/A"
            squadre_raw = cols[2].get_text(" vs ", strip=True)
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
            
            cu = parse_float(spread_cu_raw.split('/')[0] if '/' in spread_cu_raw else spread_cu_raw)
            op = parse_float(spread_op_raw.split('/')[0] if '/' in spread_op_raw else spread_op_raw)
            
            if not check_cu_op(cu, op): 
                continue
            
            # LINK DIRETTO AL MATCH NOTIFICATO - EDITABILE
            link_tag = tr.find('a', href=True)
            if link_tag and link_tag['href'] not in ['#', '']:
                link_match = link_tag['href']
                if link_match.startswith('/'):
                    link_match = "https://www.asianbetsoccer.com" + link_match
                link_diretto = link_match
            else:
                squadra_a_url = squadra_a.replace(' ', '%20')
                squadra_b_url = squadra_b.replace(' ', '%20')
                link_diretto = f"https://www.asianbetsoccer.com/livescore.html#{squadra_a_url}-vs-{squadra_b_url}"
            
            squadra_a_url = squadra_a.replace(' ', '%20')
            squadra_b_url = squadra_b.replace(' ', '%20')
            link_google = f"https://www.google.com/search?q={squadra_a_url}+vs+{squadra_b_url}+live+score"
            
            mid = f"{squadra_a}-{squadra_b}-{minuto}"
            if mid in inviate: 
                continue
            inviate.add(mid)
            
            html_mail = f"""
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
            <a href="{link_diretto}">{link_diretto}</a><br><br>
            Link editabile (copia e incolla):<br>
            {link_diretto}<br><br>
            Verifica rapida:<br>
            <a href="{link_google}">{link_google}</a>
            """
            
            send_email(f"OVER 0.5 - {squadra_a} vs {squadra_b} {minuto}' [{campionato}]", html_mail)
            trovati.append(f"{squadra_a} vs {squadra_b}")
        
        return f"Scan finale ok. Trovati: {trovati} | In memoria: {len(inviate)}"
    except Exception as e:
        return f"Errore scan: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
