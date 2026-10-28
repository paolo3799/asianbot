import os, re, time, random, requests
from flask import Flask
from bs4 import BeautifulSoup
import sib_api_v3_sdk

app = Flask(__name__)

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
FROM_EMAIL = "paolo.zapp82@yahoo.com"
FROM_NAME = "AsianBot"
TO_EMAIL = "paolo.zapp82@yahoo.com"
inviate = set()

def send_email(subject, html):
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": TO_EMAIL}],
            sender={"name": FROM_NAME, "email": FROM_EMAIL},
            subject=subject,
            html_content=html
        )
        api_instance.send_transac_email(email)
        return True
    except Exception as e:
        print(f"Errore mail: {e}")
        return False

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://www.asianbetsoccer.com/",
    }

def parse_float(v):
    try:
        m = re.search(r'[-+]?\d*\.?\d+', str(v).replace(',','.'))
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
    return '<h1>AsianBot OK</h1><a href="/test">TEST MAIL</a> | <a href="/scan">SCAN LIVESCORE</a>'

@app.route("/test")
def test():
    ok = send_email("TEST BOT OK", "Bot funziona - yahoo")
    return f"Test inviato: {ok}"

@app.route("/scan")
def scan():
    url = "https://www.asianbetsoccer.com/livescore.html"
    try:
        r = requests.get(url, headers=get_headers(), timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find_all('tr')
        trovati = []
        for row in rows:
            try:
                cols = row.find_all('td')
                if len(cols) < 8: continue
                txt = row.get_text(" ", strip=True)
                
                # minuto
                mm = re.search(r"(\d+)'", txt)
                if not mm: continue
                minuto = int(mm.group(1))
                if not (50 <= minuto <= 60): continue
                
                # 0-0
                if "0-0" not in txt and "0 - 0" not in txt: continue
                
                # rossi - cerca se c'è rosso, se 0 salta
                # se trovi 2 numeri rossi >0 salta
                reds = 0
                # colonna rossi spesso contiene img o numero
                if len(cols) > 5:
                    red_txt = cols[5].get_text(strip=True)
                    nums = re.findall(r'\d+', red_txt)
                    reds = sum(int(x) for x in nums) if nums else 0
                if reds != 0: continue
                
                # CU OP
                cu_raw = cols[6].get_text(strip=True) if len(cols)>6 else ""
                op_raw = cols[7].get_text(strip=True) if len(cols)>7 else ""
                cu = parse_float(cu_raw.split('/')[0])
                op = parse_float(op_raw.split('/')[0])
                if not check_cu_op(cu, op): continue
                
                campionato = cols[1].get_text(strip=True) if len(cols)>1 else "N/A"
                squadre_txt = cols[2].get_text(" vs ", strip=True)
                link_tag = row.find('a', href=True)
                link_match = "https://www.asianbetsoccer.com" + link_tag['href'] if link_tag and link_tag['href'].startswith('/') else url
                
                match_id = f"{squadre_txt}-{minuto}"
                if match_id in inviate: continue
                inviate.add(match_id)
                
                html = f"""
                <b>CAMPIONATO:</b> {campionato}<br>
                <b>SQUADRE:</b> {squadre_txt}<br>
                <b>MINUTO:</b> {minuto}'<br>
                <b>RISULTATO:</b> 0-0<br>
                <b>BET:</b> OVER 0.5<br>
                <b>SPREAD CU:</b> {cu_raw}<br>
                <b>SPREAD OP:</b> {op_raw}<br>
                <b>Link:</b> <a href='{link_match}'>{link_match}</a>
                """
                send_email(f"OVER 0.5 - {squadre_txt} {minuto}'", html)
                trovati.append(squadre_txt)
            except Exception as e:
                print(e)
                continue
        return f"Scan fatto. Trovati: {trovati}"
    except Exception as e:
        return f"Errore scan: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
