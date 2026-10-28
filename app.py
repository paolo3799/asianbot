import os, re, json, requests
from flask import Flask
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
FROM_EMAIL = "paolo.zapp82@yahoo.com"
TO_EMAIL = "paolo.zapp82@yahoo.com"
FILE_DB = "pronostici.json"

pronostici = []
def load_db():
    global pronostici
    try:
        if os.path.exists(FILE_DB):
            with open(FILE_DB, 'r') as f:
                pronostici = json.load(f)
    except: 
        pronostici = []
def save_db():
    try:
        with open(FILE_DB, 'w') as f:
            json.dump(pronostici, f, indent=2)
    except: pass
load_db()

def send_email(s,h):
    try:
        requests.post("https://api.brevo.com/v3/smtp/email",
        headers={"api-key":BREVO_API_KEY,"Content-Type":"application/json"},
        json={"sender":{"name":"AsianBot","email":FROM_EMAIL},"to":[{"email":TO_EMAIL}],"subject":s,"htmlContent":h},timeout=15)
    except: pass

def parse_float(v):
    try:
        m=re.search(r'[-+]?\d*\.?\d+',str(v).replace(',','.'))
        if m: return float(m.group())
    except: pass
    return None
def check_cu_op(cu,op):
    if cu is None or op is None: return False
    if cu>0 and op>0: return cu>op
    if cu<0 and op<0: return cu<op
    return False

@app.route("/")
def home():
    tot=len(pronostici)
    v=len([p for p in pronostici if p['stato']=='VINTO'])
    pe=len([p for p in pronostici if p['stato']=='PERSO'])
    return f'Bot ON - Tot:{tot} Vinti:{v} Persi:{pe} - <a href="/scan">SCAN</a> | <a href="/stats">STATS</a> | <a href="/history">HISTORY</a> | <a href="/check_results">CHECK</a>'

@app.route("/scan")
def scan():
    url="https://www.asianbetsoccer.com/livescore.html"
    try:
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=20)
        soup=BeautifulSoup(r.text,'html.parser')
        trovati=[]
        for tr in soup.find_all('tr'):
            cols=tr.find_all('td')
            if len(cols)<9: continue
            txt=tr.get_text(" ",strip=True)
            m=re.search(r"(\d+)'",txt)
            if not m: continue
            minuto=int(m.group(1))
            if not 50<=minuto<=60: continue
            if "0-0" not in txt and "0 - 0" not in txt: continue
            
            campionato=cols[1].get_text(strip=True)
            squadre_raw=cols[2].get_text(" vs ",strip=True)
            squadra_a,squadra_b = (squadre_raw.split(" vs ",1) if " vs " in squadre_raw else [squadre_raw,"N/A"])
            spread_cu=cols[6].get_text(strip=True)
            spread_op=cols[7].get_text(strip=True)
            total_cu=cols[8].get_text(strip=True)
            total_op=cols[9].get_text(strip=True) if len(cols)>9 else total_cu
            
            cu=parse_float(spread_cu.split('/')[0])
            op=parse_float(spread_op.split('/')[0])
            if not check_cu_op(cu,op): continue
            
            mid=f"{squadra_a}-{squadra_b}-{datetime.now().strftime('%Y-%m-%d')}"
            if any(p['mid']==mid for p in pronostici): continue
            
            link_d=tr.find('a',href=True)
            link="https://www.asianbetsoccer.com"+link_d['href'] if link_d and link_d['href'].startswith('/') else f"https://www.asianbetsoccer.com/livescore.html#{squadra_a.replace(' ','%20')}-vs-{squadra_b.replace(' ','%20')}"
            
            nuovo={"mid":mid,"data":datetime.now().strftime("%Y-%m-%d %H:%M"),"campionato":campionato,"squadra_a":squadra_a,"squadra_b":squadra_b,"minuto":minuto,"spread_cu":spread_cu,"spread_op":spread_op,"total_cu":total_cu,"total_op":total_op,"link":link,"stato":"PENDING","finale":None}
            pronostici.append(nuovo); save_db()
            
            html=f"""NOME CAMPIONATO: {campionato}<br>SQUADRA A: {squadra_a}<br>SQUADRA B: {squadra_b}<br>MINUTO: {minuto}'<br>RISULTATO LIVE: 0-0<br>BET: OVER 0.5<br><br>SPREAD CU: {spread_cu}<br>SPREAD OP: {spread_op}<br>TOTAL LINE CU: {total_cu}<br>TOTAL LINE OP: {total_op}<br><br>Link match notificato:<br><a href="{link}">{link}</a><br><br>Link editabile:<br>{link}"""
            send_email(f"OVER 0.5 - {squadra_a} vs {squadra_b} {minuto}'",html)
            trovati.append(f"{squadra_a} vs {squadra_b}")
        return f"Trovati: {trovati} Tot: {len(pronostici)}"
    except Exception as e:
        return f"Errore: {e}"

@app.route("/check_results")
def check_results():
    url="https://www.asianbetsoccer.com/lastgame.html"
    try:
        r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=20)
        soup=BeautifulSoup(r.text,'html.parser')
        agg=0
        for p in pronostici:
            if p['stato']!='PENDING': continue
            for tr in soup.find_all('tr'):
                t=tr.get_text(" ",strip=True).lower()
                if p['squadra_a'].lower()[:6] in t and p['squadra_b'].lower()[:6] in t:
                    m=re.search(r'(\d+)\s*-\s*(\d+)',tr.get_text())
                    if m:
                        fin=f"{m.group(1)}-{m.group(2)}"
                        p['finale']=fin
                        p['stato']='PERSO' if fin=="0-0" else 'VINTO'
                        agg+=1
                        send_email(f"ESITO {p['stato']}: {p['squadra_a']} vs {p['squadra_b']} {fin}",f"{p['squadra_a']} vs {p['squadra_b']} FINALE {fin} - {p['stato']}<br>Link: {p['link']}")
                        break
        if agg>0: save_db()
        return f"Verificati {agg} match su lastgame.html"
    except Exception as e:
        return f"Errore check: {e}"

@app.route("/stats")
def stats():
    tot=len(pronostici); v=len([p for p in pronostici if p['stato']=='VINTO']); pe=len([p for p in pronostici if p['stato']=='PERSO']); pen=len([p for p in pronostici if p['stato']=='PENDING'])
    perc=(v/(v+pe)*100) if v+pe>0 else 0
    return f"<h2>STATS</h2>Tot:{tot}<br>Vinti:{v}<br>Persi:{pe}<br>Pending:{pen}<br>Win:{perc:.1f}%<br><br><a href='/history'>Storico</a>"

@app.route("/history")
def history():
    h="<h2>Storico</h2><table border=1><tr><th>Data</th><th>Match</th><th>Min</th><th>Finale</th><th>Esito</th></tr>"
    for p in reversed(pronostici):
        h+=f"<tr><td>{p['data']}</td><td>{p['squadra_a']} vs {p['squadra_b']}</td><td>{p['minuto']}'</td><td>{p.get('finale','-')}</td><td>{p['stato']}</td></tr>"
    h+="</table>"
    return h

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
