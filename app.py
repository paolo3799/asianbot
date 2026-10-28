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
BWIN_BASE = "https://www.bwin.it/it/sports/live/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Referer":"https://www.asianbetsoccer.com/"}

def load_db():
    if not os.path.exists(DB_FILE): return []
    try: 
        with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
    except: return []
def save_db(d):
    with open(DB_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
def parse_float(s):
    m=re.search(r"[+-]?\d+(?:\.\d+)?",str(s).replace("−","-"))
    return float(m.group()) if m else None
def send_email(sub, html):
    try:
        requests.post("https://api.brevo.com/v3/smtp/email",
            headers={"api-key":BREVO_API_KEY,"Content-Type":"application/json"},
            json={"sender":{"email":SENDER_EMAIL,"name":"Bot 4 Regole"},"to":[{"email":RECEIVER_EMAIL}],"subject":sub,"htmlContent":html},timeout=15)
        return True
    except: return False
def build_email(camp,a,b,minuto,ris,bet,scu,sop,tcu,top):
    return f"""NOME CAMPIONATO: {camp}<br>SQUADRA A: {a}<br>SQUADRA B: {b}<br>MINUTO: {minuto}'<br>RISULTATO LIVE: {ris}<br>BET: {bet}<br><br>Link match:<br><a href="{ASIAN_URL}">{ASIAN_URL}</a><br><br>BWIN LIVE:<br><a href="{BWIN_BASE}">{BWIN_BASE}</a><br><br>SPREAD CU: {scu}<br>SPREAD OP: {sop}<br>TOTAL CU: {tcu}<br>TOTAL OP: {top}<br>"""
def fetch_page():
    for url in [ASIAN_URL, f"https://api.allorigins.win/raw?url={ASIAN_URL}", f"https://corsproxy.io/?{ASIAN_URL}"]:
        try:
            r=requests.get(url,headers=HEADERS,timeout=20)
            if len(r.text)>5000: return r.text
        except: continue
    return ""

def scan_livescore():
    db=load_db(); found=[]
    html=fetch_page()
    if not html: return found
    soup=BeautifulSoup(html,"html.parser")
    for tr in soup.find_all("tr"):
        tds=tr.find_all("td")
        if len(tds)<6: continue
        txt=tr.get_text(" ",strip=True)
        m_min=re.search(r"(\d+)\s*['′]",txt)
        if not m_min: continue
        minuto=int(m_min.group(1))
        if not (50<=minuto<=60): continue
        m_res=re.search(r"(\d+)\s*-\s*(\d+)",txt)
        if not m_res: continue
        ris=f"{m_res.group(1)}-{m_res.group(2)}"
        if tr.find("img",src=lambda x: x and "red" in x.lower() if x else False): continue
        cols=[td.get_text(" ",strip=True) for td in tds]
        camp=cols[0]; a=cols[2] if len(cols)>2 else "A"; b=cols[3] if len(cols)>3 else "B"
        scu=sop=None; scu_raw=sop_raw=tcu_raw=top_raw=""
        for i in range(len(cols)-1):
            cu=parse_float(cols[i]); op=parse_float(cols[i+1])
            if cu is None or op is None: continue
            if abs(cu)<=4 and abs(op)<=4:
                scu=cu; sop=op; scu_raw=cols[i]; sop_raw=cols[i+1]
                if i+2 < len(cols): tcu_raw=cols[i+2]
                if i+3 < len(cols): top_raw=cols[i+3]
                break
        mid=f"{a}-{b}-{minuto}-{ris}".replace(" ","_")
        if any(x.get("id")==mid for x in db): continue
        bet=regola=None
        # R1 0-0 OVER 0.5
        if ris=="0-0" and scu is not None and ((scu>0 and scu>sop) or (scu<0 and scu<sop)): bet="OVER 0.5"; regola="R1"
        # R2 1-0 OVER 1.5 CU>=0.75 e CU>OP
        elif ris=="1-0" and scu is not None and abs(scu)>=0.75 and ((scu>0 and scu>sop) or (scu<0 and scu<sop)): bet="OVER 1.5"; regola="R2"
        # R3 0-1 OVER 1.5 CU>=0.75 e CU>OP - QUELLA TUA DEL 56'
        elif ris=="0-1" and scu is not None and abs(scu)>=0.75 and ((scu>0 and scu>sop) or (scu<0 and scu<sop)): bet="OVER 1.5"; regola="R3"
        # R4 1-1 OVER 2.5 CU>=1
        elif ris=="1-1" and scu is not None and abs(scu)>=1 and ((scu>0 and scu>sop) or (scu<0 and scu<sop)): bet="OVER 2.5"; regola="R4"
        if bet:
            html_mail=build_email(camp,a,b,minuto,ris,bet,scu_raw,sop_raw,tcu_raw,top_raw)
            send_email(f"[{regola}] {a} vs {b} {ris} {minuto}' {bet}",html_mail)
            db.append({"id":mid,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"campionato":camp,"squadra_a":a,"squadra_b":b,"minuto":minuto,"risultato_live":ris,"bet":bet,"regola":regola,"spread_cu":scu_raw,"spread_op":sop_raw,"total_cu":tcu_raw,"total_op":top_raw,"esito":"PENDING"})
            found.append(mid)
    save_db(db)
    return found

@app.route("/")
def home(): return f"Bot 4 REGOLE PROXY ON - Tot:{len(load_db())} - {datetime.now().strftime('%H:%M:%S')} | Debug OK len=134k"
@app.route("/scan")
def scan():
    try:
        f=scan_livescore()
        return jsonify({"trovati":f,"tot_db":len(load_db())})
    except Exception as e:
        return jsonify({"error":str(e),"trovati":[],"tot_db":len(load_db())})
@app.route("/debug")
def debug():
    html=fetch_page()
    return jsonify({"len":len(html),"ok":len(html)>5000})
@app.route("/stats")
def stats(): return jsonify(load_db())
@app.route("/test_r3")
def t3():
    send_email("[R3] TEST 0-1 OVER 1.5 - 56'", build_email("UEFA Youth League TEST","Genk U19","Salzburg U19",56,"0-1","OVER 1.5 TEST R3","0.75","0.5","1.5","1.25"))
    return "mail R3 inviata - controlla"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
