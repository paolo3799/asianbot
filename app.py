import os, re, time, random, requests
from flask import Flask
from bs4 import BeautifulSoup
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

app = Flask(__name__)

# --- CONFIG MAIL ---
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "xkeysib-TUA-CHIAVE-QUI")
FROM_EMAIL = "paolo.zapp82@yahoo.com"
FROM_NAME = "AsianBot"
TO_EMAIL = "paolo.zapp82@yahoo.com"

# --- MEMORIA PER NON RIMANDARE STESSA PARTITA ---
inviate = set()

def send_email(subject, html_content):
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": TO_EMAIL}],
            sender={"name": FROM_NAME, "email": FROM_EMAIL},
            subject=subject,
            html_content=html_content
        )
        api_instance.send_transac_email(send_smtp_email)
        print(f"MAIL INVIATA: {subject}")
        return True
    except ApiException as e:
        print(f"Errore Brevo: {e}")
        return False

def get_stealth_headers():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
    ]
    return {
        "User-Agent": random.choice(agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
        "Referer": "https://www.asianbetsoccer.com/",
        "Connection": "keep-alive",
    }

def parse_float(val):
    try:
        # pulisce +0.5 , -0.75 , 0.25 etc
        m = re.search(r'[-+]?\d*\.?\d+', str(val).replace(',', '.'))
        if m:
            return float(m.group())
    except:
        pass
    return None

def check_cu_op_logic(cu, op):
    """Tua regola corretta"""
    if cu is None or op is None:
        return False
    # entrambi positivi -> CU > OP
    if cu > 0 and op > 0:
        return cu > op
    # entrambi negativi -> CU < OP (es -0.75 < -0.5)
    if cu < 0 and op < 0:
        return cu < op
    return False

def scan_livescore():
    url = "https://www.asianbetsoccer.com/livescore.html"
    try:
        r = requests.get(url, headers=get_stealth_headers(), timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        
        # la pagina usa tabella, prendiamo tutte le righe
        # ogni match ha 2 righe (A e B) - noi prendiamo riga A
        # Adattato alla struttura reale vista negli screenshot
        
        matches_found = []
        # cerchiamo tabella livescore
        rows = soup.find_all('tr')
        i = 0
        while i < len(rows):
            row = rows[i]
            text = row.get_text(" ", strip=True)
            
            # cerca pattern minuto 50-60 , risultato 0-0
            # Esempio riga: 55' , 0-0 , red 0
            # dobbiamo estrarre dati
            try:
                cols = row.find_all(['td','th'])
                if len(cols) < 10:
                    i+=1
                    continue
                
                # PROVA A MAPPARE COLONNE - tu mandami HTML se non funziona
                # Mappa ipotetica da screenshot tuo:
                # [0] Time, [1] League, [2] Teams, [3] Minute, [4] Score, [5] RedCards, [6] Spread CU, [7] Spread OP, [8] Total CU, [9] Total OP, [10] Link
                
                # Per sicurezza leggiamo tutto il testo
                row_str = " | ".join([c.get_text(strip=True) for c in cols])
                
                # 1. MINUTO 50-60
                min_match = re.search(r"(\d{1,2})['’]|\b(\d{2})\s*min", text)
                minuto = int(min_match.group(1) or min_match.group(2)) if min_match else None
                if not minuto or not (50 <= minuto <= 60):
                    i+=1
                    continue
                
                # 2. RISULTATO 0-0
                if "0 - 0" not in text and "0-0" not in text and "0 : 0" not in text:
                    # cerca in colonna score
                    score_col = cols[4].get_text() if len(cols)>4 else text
                    if "0-0" not in score_col and "0 - 0" not in score_col:
                        i+=1
                        continue
                
                # 3. CARTELLINI ROSSI = 0
                # spesso colonna con 0 0 o icona rossa
                red_text = cols[5].get_text(strip=True) if len(cols)>5 else "0"
                reds = re.findall(r'\d+', red_text)
                total_reds = sum(int(x) for x in reds) if reds else 0
                if total_reds != 0:
                    i+=1
                    continue
                
                # 4. CU vs OP riga A (spread)
                # prendiamo questa riga come A e la prossima come B
                spread_cu_raw = cols[6].get_text(strip=True) if len(cols)>6 else ""
                spread_op_raw = cols[7].get_text(strip=True) if len(cols)>7 else ""
                
                # a volte CU e OP sono nella stessa cella tipo "0.5 / 0.25"
                # prendiamo primo valore (riga A)
                spread_cu = parse_float(spread_cu_raw.split("/")[0] if "/" in spread_cu_raw else spread_cu_raw)
                spread_op = parse_float(spread_op_raw.split("/")[0] if "/" in spread_op_raw else spread_op_raw)
                
                if not check_cu_op_logic(spread_cu, spread_op):
                    i+=1
                    continue
                
                # Se arriviamo qui, TUTTE LE REGOLE OK!
                campionato = cols[1].get_text(strip=True) if len(cols)>1 else "N/A"
                squadre_txt = cols[2].get_text(" vs ", strip=True) if len(cols)>2 else "A vs B"
                squadre = squadre_txt.split("vs")
                squadra_a = squadre[0].strip() if len(squadre)>0 else "Squadra A"
                squadra_b = squadre[1].strip() if len(squadre)>1 else "Squadra B"
                
                total_cu = cols[8].get_text(strip=True) if len(cols)>8 else "N/A"
                total_op = cols[9].get_text(strip=True) if len(cols)>9 else "N/A"
                
                # Link match
                link_tag = row.find('a', href=True)
                link_match = link_tag['href'] if link_tag else url
                if link_match.startswith("/"):
                    link_match = "https://www.asianbetsoccer.com" + link_match
                
                match_id = f"{squadra_a}-{squadra_b}-{minuto}"
                if match_id in inviate:
                    i+=1
                    continue
                inviate.add(match_id)
                
                subject = f"OVER 0.5 - {squadra_a} vs {squadra_b} {minuto}'"
                html = f"""
                <h2>SEGNALE ASIANBOT</h2>
                <b>CAMPIONATO:</b> {campionato}<br>
                <b>SQUADRA A:</b> {squadra_a}<br>
                <b>SQUADRA B:</b> {squadra_b}<br>
                <b>MINUTO:</b> {minuto}'<br>
                <b>RISULTATO LIVE:</b> 0-0<br>
                <b>BET:</b> OVER 0.5<br><br>
                <b>SPREAD CU:</b> {spread_cu_raw} ({spread_cu})<br>
                <b>SPREAD OP:</b> {spread_op_raw} ({spread_op})<br>
                <b>TOTAL LINE CU:</b> {total_cu}<br>
                <b>TOTAL LINE OP:</b> {total_op}<br><br>
                <b>Link:</b> <a href="{link_match}">{link_match}</a><br>
                <br>Regola: CU > OP se positivo, CU < OP se negativo - VERIFICATA
                """
                send_email(subject, html)
                matches_found.append(match_id)
                
            except Exception as e:
                print(f"Parse errore riga: {e}")
            i+=1
        
        return matches_found
    except Exception as e:
        print(f"Errore scan: {e}")
        return []

@app.route("/")
def home():
    return "AsianBot LIVE - <a href='/scan'>CLICCA PER SCANSIONARE ORA</a> | <a href='/test'>TEST MAIL</a>"

@app.route("/test")
def test():
    ok = send_email("TEST FINALE BOT PAOLO", "AsianBot LIVE - mail yahoo OK")
    return f"Test inviato: {ok}"

@app.route("/scan")
def scan():
    # delay random per non farsi scoprire
    time.sleep(random.uniform(1,3))
    found = scan_livescore()
    return f"Scansione finita. Match trovati e notificati: {found} - Totale in memoria: {len(inviate)}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
