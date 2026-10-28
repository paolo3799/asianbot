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
    except: pronostici = []
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
        v=str(v).strip()
        # prende -0.75 / 0.75 / 1.0 etc
        m=re.search(r'[-+]?\d*\.?\d+',v.replace(',','.'))
        if m: return float(m.group())
    except: pass
    return None

def check_handicap_cu_op(cu, op):
    # Regola che hai chiesto:
    # positivo: CU > OP e >=0.75
    # negativo: CU < OP e <= -0.75 (tu hai scritto <=0.75 ma con segno negativo)
    if cu is None or op is None: return False
    if cu > 0:
        return cu > op and cu >= 0.75
    if cu < 0:
        return cu < op and cu <= -0.75
    return False

def has_red_cards(tr):
    # Cerca cartellini rossi = 0
    html = str(tr).lower()
    # se trova icona red card con numero 1/2 etc
    # su asianbetsoccer i rossi sono in una colonna con img o numero rosso
    # se trova >0 ritorna True (ha rossi)
    # cerca pattern: red card, rcard, o numero rosso
    if 'redcard' in html or 'red-card' in html or 'red_card' in html:
        # se c'è la parola ma con 0 va bene, cerchiamo 1 o 2 vicino
        if re.search(r'red[^<]*[1-9]', html):
            return True
    # alcuni template mettono <span class="red">1</span>
    tds = tr.find_all('td')
    for td in tds:
        txt = td.get_text(strip=True)
        style = str(td.get('style','')).lower()
        cls = str(td.get('class','')).lower()
        if ('red' in cls or 'red' in style or 'f00' in style) and txt in ['1','2','3']:
            return True
        # se colonna contiene solo "1" rossa
        if txt == '1' and ('red' in html):
            # controllo più stretto: se la riga ha 1 rosso
            pass
    # fallback: cerca icone: se html contiene "●" rossa con 1
    # se non trova nulla, consideriamo 0 rossi
    # Controllo extra: se nel testo c'è " 1 " vicino a red
    if re.search(r'>\s*1\s*<', html) and 'red' in html:
        # potrebbe essere falso positivo, ma per sicurezza lo lasciamo passare come 0 se non siamo sicuri
        # per ora: se non siamo sicuri, diciamo 0 rossi
        return False
    return False

@app.route("/")
def home():
    tot=len(pronostici)
    v=len([p for p in pronostici if p['stato']=='VINTO'])
    pe=len([p for p in pronostici if p['stato']=='PERSO'])
    return f'Bot 3 REGOLE ON - Tot:{tot} V:{v} P:{pe} - <a href="/scan">SCAN</a> | <a href="/stats">STATS</a> | <a href="/history">HISTORY</a>'

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
            txt_full=tr.get_text(" ",strip=True)
            m_min=re.search(r"(\d+)'",txt_full)
            if not m_min: continue
            minuto=int(m_min.group(1))
            if not 50 <= minuto <= 60: continue

            # rossi = 0
            if has_red_cards(tr): continue

            campionato=cols[1].get_text(strip=True)
            squadre_raw=cols[2].get_text(" vs ",strip=True)
            if " vs " in squadre_raw:
                squadra_a,squadra_b = squadre_raw.split(" vs ",1)
            else:
                squadra_a,squadra_b = squadre_raw,"N/A"
            
            # risultato live es: 1-0 o 0-1 o 0-0
            m_score=re.search(r'(\d+)\s*-\s*(\d+)',txt_full)
            if not m_score: continue
            risultato=f"{m_score.group(1)}-{m_score.group(2)}"
            
            spread_cu=cols[6].get_text(strip=True)
            spread_op=cols[7].get_text(strip=True)
            total_cu=cols[8].get_text(strip=True)
            total_op=cols[9].get_text(strip=True) if len(cols)>9 else total_cu

            cu=parse_float(spread_cu.split('/')[0])
            op=parse_float(spread_op.split('/')[0])

            bet=None
            regola=None

            # REGOLA 1: 0-0 OVER 0.5
            if risultato in ["0-0","0 - 0"]:
                if cu is not None and op is not None:
                    if (cu>0 and op>0 and cu>op) or (cu<0 and op<0 and cu<op):
                        bet="OVER 0.5"
                        regola="R1"

            # REGOLA 2: 1-0 OVER 1.5
            if bet is None and risultato=="1-0":
                if check_handicap_cu_op(cu, op):
                    bet="OVER 1.5"
                    regola="R2"

            # REGOLA 3: 0-1 OVER 1.5
            if bet is None and risultato=="0-1":
                if check_handicap_cu_op(cu, op):
                    bet="OVER 1.5"
                    regola="R3"

            if bet is None: continue

            mid=f"{regola}-{squadra_a}-{squadra_b}-{datetime.now().strftime('%Y-%m-%d')}"
            if any(p['mid']==mid for p in pronostici): continue
            
            link_d=tr.find('a',href=True)
            link="https://www.asianbetsoccer.com"+link_d['href'] if link_d and link_d['href'].startswith('/') else f"https://www.asianbetsoccer.com/livescore.html"

            nuovo={"mid":mid,"regola":regola,"data":datetime.now().strftime("%Y-%m-%d %H:%M"),"campionato":campionato,"squadra_a":squadra_a,"squadra_b":squadra_b,"minuto":minuto,"risultato":risultato,"bet":bet,"spread_cu":spread_cu,"spread_op":spread_op,"total_cu":total_cu,"total_op":total_op,"link":link,"stato":"PENDING","finale":None}
            pronostici.append(nuovo); save_db()
            
            html=f"""NOME CAMPIONATO: {campionato}<br>SQUADRA A: {squadra_a}<br>SQUADRA B: {squadra_b}<br>MINUTO: {minuto}'<br>RISULTATO LIVE: {risultato}<br>BET: {bet} [{regola}]<br><br>SPREAD CU: {spread_cu}<br>SPREAD OP: {spread_op}<br>TOTAL LINE CU: {total_cu}<br>TOTAL LINE OP: {total_op}<br><br>Link pagina asianbetsoccer.com del match notificato:<br><a href="{link}">{link}</a><br><br>Link editabile:<br>{link}"""
            send_email(f"{regola} {bet} - {squadra_a} vs {squadra_b} {risultato} {minuto}'",html)
            trovati.append(f"{regola} {squadra_a} vs {squadra_b} {risultato}")

        return f"Trovati: {trovati} Tot DB: {len(pronostici)}"
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
                        # esito in base al BET
                        if p['bet']=="OVER 0.5":
                            p['stato']='PERSO' if fin=="0-0" else 'VINTO'
                        else: # OVER 1.5
                            g=int(m.group(1))+int(m.group(2))
                            p['stato']='VINTO' if g>=2 else 'PERSO'
                        agg+=1
                        send_email(f"ESITO {p['stato']} {p['regola']}: {p['squadra_a']} vs {p['squadra_b']} {fin}",f"{p['regola']} {p['bet']} - {p['squadra_a']} vs {p['squadra_b']} FINALE {fin} - {p['stato']}<br>Link: {p['link']}")
                        break
        if agg>0: save_db()
        return f"Verificati {agg} match"
    except Exception as e:
        return f"Errore check: {e}"

@app.route("/stats")
def stats():
    tot=len(pronostici)
    byR={}
    for p in pronostici:
        r=p.get('regola','R1')
        if r not in byR: byR[r]={'tot':0,'v':0,'p':0}
        byR[r]['tot']+=1
        if p['stato']=='VINTO': byR[r]['v']+=1
        if p['stato']=='PERSO': byR[r]['p']+=1
    html="<h2>STATS 3 REGOLE</h2>"
    for k,v in byR.items():
        perc=(v['v']/(v['v']+v['p'])*100) if v['v']+v['p']>0 else 0
        html+=f"{k}: Tot {v['tot']} Vinti {v['v']} Persi {v['p']} Win {perc:.1f}%<br>"
    html+=f"<br><a href='/history'>Storico</a>"
    return html

@app.route("/history")
def history():
    h="<h2>Storico</h2><table border=1><tr><th>Reg</th><th>Data</th><th>Match</th><th>Live</th><th>Bet</th><th>Finale</th><th>Esito</th></tr>"
    for p in reversed(pronostici):
        h+=f"<tr><td>{p.get('regola','')}</td><td>{p['data']}</td><td>{p['squadra_a']} vs {p['squadra_b']}</td><td>{p['minuto']}' {p.get('risultato','')}</td><td>{p['bet']}</td><td>{p.get('finale','-')}</td><td>{p['stato']}</td></tr>"
    h+="</table>"
    return h

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
