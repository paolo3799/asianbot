import os, json, re, requests
from flask import Flask, jsonify
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
DB_FILE = "pronostici.json"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "paolo.zapp82@yahoo.com")
RECEIVER_EMAIL = "paolo.zapp82@yahoo.com"
ASIAN_URL = "https://www.asianbetsoccer.com/livescore.html"
# PROXY per bypassare blocco Render
PROXY_URL = f"https://api.allorigins.win/raw?url={ASIAN_URL}"
BWIN_BASE = "https://www.bwin.it/it/sports/live/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

def load_db():
    if not os.path.exists(DB_FILE): return []
    try:
        with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return []
def save_db(d):
    with open(DB_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
def parse_float(s):
    try:
        m=re.search(r"[+-]?\d+(?:\.\d+)?",str(s).replace("−","-"))
        return float(m.group()) if m else None
    except: return None

def send_email(sub, html):
    try:
        r=requests.post("https://api.brevo.com/v3/smtp/email",
            headers={"api-key":BREVO_API_KEY,"Content-Type":"application/json"},
            json={"sender":{"email":SENDER_EMAIL,"name":"Bot"},"to":[{"email":RECEIVER_EMAIL}],"subject":sub,"htmlContent":html},timeout=20)
        return r.status_code<400
    except: return False

def build_email(camp,a,b,minuto,ris,bet,scu,sop,tcu,top,link):
    return f"""CAMP: {camp}<br>{a} vs {b}<br>MIN: {minuto}'<br>RIS: {ris}<br>BET: {bet}<br><br>Link: <a href="{link}">{link}</a><br><br>BWIN: <a href="{BWIN_BASE}">{BWIN_BASE}</a><br><br>CU:{scu} OP:{sop} TOTAL CU:{tcu} OP:{top}"""

def check_spread(cu,op):
    if cu is None or op is None: return False
    return (cu>0 and cu>op) or (cu<0 and cu<op)

def fetch_page():
    # 1. prova diretto
    try:
        r=requests.get(ASIAN_URL,headers=HEADERS,timeout=15)
        if len(r.text)>5000: return r.text
    except: pass
    # 2. prova via proxy (bypassa blocco Render)
    try:
        r=requests.get(PROXY_URL,headers=HEADERS,timeout=25)
        if len(r.text)>1000: return r.text
    except Exception as e:
        print(f"PROXY ERR {e}")
    return ""

def scan_livescore():
    db=load_db(); found=[]
    html=fetch_page()
    if not html: 
        print("FETCH VUOTO - BLOCCATO")
        return found
    soup=BeautifulSoup(html,"html.parser")
    rows=soup.find_all("tr")
    for tr in rows:
        tds=tr.find_all("td")
        if len(tds)<6: continue
        txt=tr.get_text(" ",strip=True)
        m_min=re.search(r"(\d+)\s*['′]",txt)
        if not m_min: continue
        minuto=int(m_min.group(1))
        if not (50<=minuto<=60): continue
        m_res=re.search(r"(\d+)\s*-\s*(\d+)",txt)
        if not m_res: continue
        risultato=f"{m_res.group(1)}-{m_res.group(2)}"
        if tr.find("img",src=lambda x: x and "red" in x.lower() if x else False): continue
        
        cols=[td.get_text(" ",strip=True) for td in tds]
        camp=cols[0] if len(cols)>0 else "N/D"
        sq_a=cols[2] if len(cols)>2 else "A"
        sq_b=cols[3] if len(cols)>3 else "B"

        scu=sop=None; scu_raw=sop_raw=tcu_raw=top_raw=""
        for i in range(len(cols)-1):
            cu=parse_float(cols[i]); op=parse_float(cols[i+1])
            if cu is None or op is None: continue
            if abs(cu)<=3 and abs(op)<=3:
                scu=cu; sop=op; scu_raw=cols[i]; sop_raw=cols[i+1]
                if i+2 < len(cols): tcu_raw=cols[i+2]
                if i+3 < len(cols): top_raw=cols[i+3]
                break
        
        mid=f"{sq_a}-{sq_b}-{minuto}-{risultato}".replace(" ","_")
        if any(x.get("id")==mid for x in db): continue

        bet=regola=None
        if risultato=="0-0" and check_spread(scu,sop): bet="OVER 0.5"; regola="R1"
        elif risultato=="1-0" and scu is not None and scu>=0.75 and scu>sop: bet="OVER 1.5"; regola="R2"
        elif risultato=="0-1" and scu is not None and scu>=0.75 and scu>sop: bet="OVER 1.5"; regola="R3"
        elif risultato=="1-1" and scu is not None and scu>=1 and scu>sop: bet="OVER 2.5"; regola="R4"
        # gestisce anche handicap negativi
        elif risultato=="1-0" and scu is not None and scu<=-0.75 and scu<sop: bet="OVER 1.5"; regola="R2"
        elif risultato=="0-1" and scu is not None and scu<=-0.75 and scu<sop: bet="OVER 1.5"; regola="R3"
        elif risultato=="1-1" and scu is not None and scu<=-1 and scu<sop: bet="OVER 2.5"; regola="R4"

        if bet:
            html_mail=build_email(camp,sq_a,sq_b,minuto,risultato,bet,scu_raw,sop_raw,tcu_raw,top_raw,ASIAN_URL)
            send_email(f"[{regola}] {sq_a} vs {sq_b} {risultato} {minuto}' {bet}",html_mail)
            db.append({"id":mid,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"campionato":camp,"squadra_a":sq_a,"squadra_b":sq_b,"minuto":minuto,"risultato_live":risultato,"bet":bet,"regola":regola,"spread_cu":scu_raw,"spread_op":sop_raw,"total_cu":tcu_raw,"total_op":top_raw,"link_asian":ASIAN_URL,"esito":"PENDING"})
            found.append(mid)
    save_db(db)
    return found

@app.route("/")
def home(): return f"Bot 4 REGOLE PROXY ON - Tot:{len(load_db())} - {datetime.now().strftime('%H:%M:%S')}"
@app.route("/scan")
def scan(): f=scan_livescore(); return jsonify({"trovati":f,"tot_db":len(load_db())})
@app.route("/debug")
def debug():
    html=fetch_page()
    soup=BeautifulSoup(html,"html.parser")
    return jsonify({"len":len(html),"rows":len(soup.find_all("tr")),"preview":html[:800]})
@app.route("/stats")
def stats(): return jsonify(load_db())

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
