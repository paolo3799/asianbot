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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.asianbetsoccer.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
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
        s=str(s).replace("−","-").replace("–","-")
        m=re.search(r"[+-]?\d+(?:\.\d+)?",s)
        return float(m.group()) if m else None
    except: return None

def send_email(sub, html):
    try:
        r=requests.post("https://api.brevo.com/v3/smtp/email",
            headers={"api-key":BREVO_API_KEY,"Content-Type":"application/json"},
            json={"sender":{"email":SENDER_EMAIL,"name":"Bot 4 Regole"},"to":[{"email":RECEIVER_EMAIL}],"subject":sub,"htmlContent":html},timeout=20)
        return r.status_code<400
    except: return False

def build_email(camp,a,b,minuto,ris,bet,scu,sop,tcu,top,link):
    return f"""NOME CAMPIONATO: {camp}<br>SQUADRA A: {a}<br>SQUADRA B: {b}<br>MINUTO: {minuto}'<br>RISULTATO LIVE: {ris}<br>BET: {bet}<br><br>Link: <a href="{link}">{link}</a><br><br><a href="{BWIN_BASE}">{BWIN_BASE}</a><br><br>TOTAL CU: {tcu}<br>TOTAL OP: {top}<br>SPREAD CU: {scu}<br>SPREAD OP: {sop}<br>"""

def check_spread(cu,op):
    if cu is None or op is None: return False
    if cu>0 and cu>op: return True
    if cu<0 and cu<op: return True
    return False

def scan_livescore():
    db=load_db(); found=[]
    try:
        resp=requests.get(ASIAN_URL,headers=HEADERS,timeout=30)
        soup=BeautifulSoup(resp.text,"html.parser")
        rows=soup.find_all("tr")
    except Exception as e:
        print(f"FETCH ERR {e}"); return found

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
        if "red" in txt.lower() and "card" in txt.lower(): continue
        if tr.find("img",src=lambda x: x and "red" in x.lower() if x else False): continue
        
        # PRENDE TUTTI I NUMERI NELLA RIGA - NON SOLO COLONNA 5/6
        cols=[td.get_text(" ",strip=True) for td in tds]
        camp=cols[0] if len(cols)>0 else "N/D"
        sq_a=cols[2] if len(cols)>2 else "A"
        sq_b=cols[3] if len(cols)>3 else "B"
        # cerca in tutta la riga tutti i float
        all_numbers=[]
        for c in cols:
            f=parse_float(c)
            if f is not None: all_numbers.append((f,c))
        # per spread cerchiamo coppie CU/OP in cols
        # su asianbetsoccer i numeri sono tipo: 0.75 0.5 1.5 1.75 etc
        # prendiamo il primo che rispetta regola
        scu=None; sop=None; scu_raw=""; sop_raw=""
        tcu_raw=""; top_raw=""
        # cerca due numeri consecutivi che sono spread (0.25 step)
        for i in range(len(cols)-1):
            cu=parse_float(cols[i]); op=parse_float(cols[i+1])
            if cu is None or op is None: continue
            if abs(cu)<=3 and abs(op)<=3: # spread
                scu=cu; sop=op; scu_raw=cols[i]; sop_raw=cols[i+1]
                # total sta dopo
                if i+2 < len(cols): tcu_raw=cols[i+2]
                if i+3 < len(cols): top_raw=cols[i+3]
                break
        
        mid=f"{sq_a}-{sq_b}-{minuto}-{risultato}".replace(" ","_")
        if any(x.get("id")==mid for x in db): continue

        bet=None; regola=None
        if risultato=="0-0":
            if check_spread(scu,sop): bet="OVER 0.5"; regola="R1"
        elif risultato=="1-0":
            if scu is not None and sop is not None:
                if (scu>0 and scu>sop and scu>=0.75) or (scu<0 and scu<sop and scu<=-0.75):
                    bet="OVER 1.5"; regola="R2"
        elif risultato=="0-1":
            if scu is not None and sop is not None:
                if (scu>0 and scu>sop and scu>=0.75) or (scu<0 and scu<sop and scu<=-0.75):
                    bet="OVER 1.5"; regola="R3"
        elif risultato=="1-1":
            if scu is not None and sop is not None:
                if (scu>0 and scu>sop and scu>=1) or (scu<0 and scu<sop and scu<=-1):
                    bet="OVER 2.5"; regola="R4"

        if bet:
            link=ASIAN_URL
            html=build_email(camp,sq_a,sq_b,minuto,risultato,bet,scu_raw,sop_raw,tcu_raw,top_raw,link)
            send_email(f"[{regola}] {sq_a} vs {sq_b} {risultato} {minuto}' {bet}",html)
            db.append({"id":mid,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"campionato":camp,"squadra_a":sq_a,"squadra_b":sq_b,"minuto":minuto,"risultato_live":risultato,"bet":bet,"regola":regola,"spread_cu":scu_raw,"spread_op":sop_raw,"total_cu":tcu_raw,"total_op":top_raw,"link_asian":link,"esito":"PENDING"})
            found.append(mid)

    save_db(db)
    return found

@app.route("/")
def home(): return f"Bot 4 REGOLE FIX - Tot:{len(load_db())} - {datetime.now().strftime('%H:%M:%S')}"
@app.route("/scan")
def scan(): f=scan_livescore(); return jsonify({"trovati":f,"tot_db":len(load_db())})
@app.route("/debug")
def debug():
    try:
        r=requests.get(ASIAN_URL,headers=HEADERS,timeout=20)
        soup=BeautifulSoup(r.text,"html.parser")
        rows=soup.find_all("tr")
        sample=[]
        for tr in rows[:5]:
            tds=tr.find_all("td")
            sample.append({"tds":len(tds),"txt":tr.get_text(" ",strip=True)[:300]})
        return jsonify({"status":r.status_code,"len":len(r.text),"rows":len(rows),"sample":sample})
    except Exception as e:
        return jsonify({"error":str(e)})
@app.route("/stats")
def stats():
    db=load_db()
    return jsonify({"totale":len(db),"db":db})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
