import os, json, re
from flask import Flask, jsonify
from datetime import datetime as DT
import requests
from bs4 import BeautifulSoup as BS

app = Flask(__name__)
DB="db.json"
TO="paolo.zapp82@yahoo.com"
U="https://www.asianbetsoccer.com/livescore.html"
BASE="https://www.asianbetsoccer.com"
H={"User-Agent":"Mozilla/5.0 Chrome/124.0","Referer":BASE+"/"}
KEY=os.environ.get("BREVO_KEY","")

def L():
    try: return json.load(open(DB)) if os.path.exists(DB) else []
    except: return []
def S(d):
    try: json.dump(d,open(DB,"w"),ensure_ascii=False,indent=2)
    except: pass
def PF(s):
    m=re.search(r"\+?-?\d+(?:\.\d+)?",str(s).replace("--","-"))
    return float(m.group()) if m else None
def RED(td):
    if not td: return False
    h=str(td).lower()
    return "red" in h or "ff0000" in h or "color:red" in h
def MAIL(sub,html):
    try:
        r=requests.post("https://api.brevo.com/v3/smtp/email",
        headers={"api-key":KEY,"Content-Type":"application/json"},
        json={"sender":{"email":"bot@asianbot.com"},"to":[{"email":TO}],"subject":sub,"htmlContent":html},timeout=15)
        return r.status_code<400
    except: return False

def F():
    # 1) scarica pagina base
    try: html=requests.get(U,headers=H,timeout=20).text
    except: return ""
    combined=html
    soup=BS(html,"html.parser")
    # 2) cerca tutti i js che sembrano dati live e scaricali anche
    for script in soup.find_all("script",src=True):
        src=script["src"]
        if any(k in src.lower() for k in ["live","score","odd","data","match"]):
            if src.startswith("/"): src=BASE+src
            elif not src.startswith("http"): src=BASE+"/"+src
            try:
                js=requests.get(src,headers=H,timeout=15).text
                if len(js)>1000: combined+="\n"+js
            except: pass
    # prova anche file comuni di asianbetsoccer
    for extra in ["/js/livescore.js","/js/data.js","/livescore_data.js","/data/live.js"]:
        try:
            js=requests.get(BASE+extra,headers=H,timeout=10).text
            if len(js)>2000: combined+="\n"+js
        except: pass
    return combined

@app.route("/")
def home(): return f"ON R1-R5 40-75 Tot:{len(L())} {DT.now().strftime('%H:%M')}"

@app.route("/debug")
def dbg():
    h=F()
    # mostra un pezzo dove ci sono risultati
    m=re.findall(r"\d+\s*-\s*\d+",h)
    return jsonify({"len":len(h),"ok":len(h)>5000,"scores_found":len(m),"snippet":h[3000:6000]})

@app.route("/live")
def live():
    h=F()
    if not h: return jsonify({"count":0,"len":0,"err":"no html"})
    soup=BS(h,"html.parser")
    out=[]
    # cerca ovunque pattern tipo "TeamA 1-0 TeamB 45'"
    for tr in soup.find_all("tr"):
        txt=tr.get_text(" ",strip=True)
        if re.search(r"\d+\s*-\s*\d+",txt) and len(txt)<250:
            out.append(txt[:200])
    if len(out)<5:
        # fallback regex su tutto il file combinato
        for line in h.split("\n"):
            if re.search(r"\d+\s*-\s*\d+",line) and len(line)<300 and "Asian" not in line:
                out.append(line.strip()[:200])
    return jsonify({"live":out[:80],"count":len(out),"len":len(h)})

@app.route("/scan")
def scan():
    try:
        db=L();fnd=[];h=F()
        if not h: return jsonify({"trovati":[],"tot":len(db),"err":"no html"})
        soup=BS(h,"html.parser")
        last_a="A";last_b="B";last_m=0;last_ris=""
        for tr in soup.find_all("tr"):
            tds=tr.find_all("td")
            if len(tds)<3: continue
            txt=tr.get_text(" ",strip=True)
            mm=re.search(r"(\d+)\s*\[",txt); mr=re.search(r"(\d+)\s*-\s*(\d+)",txt)
            if mm and mr:
                last_m=int(mm.group(1)); last_ris=f"{mr.group(1)}-{mr.group(2)}"
            cols=[td.get_text(" ",strip=True) for td in tds]
            if len(cols)>=2:
                last_a=cols[0][:30];last_b=cols[1][:30]
                if mm: continue
            if not(40<=last_m<=75): continue
            scu=sop=None;scu_r=sop_r="";red=False
            for i in range(len(cols)-1):
                cu=PF(cols[i]);op=PF(cols[i+1])
                if cu is None or op is None: continue
                if abs(cu)<=4 and abs(op)<=4 and cu!=0 and op!=0:
                    scu=cu;sop=op;scu_r=cols[i];sop_r=cols[i+1]
                    if RED(tds[i]) or RED(tds[i+1]): red=True
                    break
            if scu is None: continue
            mid=f"{last_a}-{last_b}-[{last_m}]-{last_ris}-{scu_r}".replace(" ","_")
            if any(x.get("id")==mid for x in db): continue
            bet=None;reg=None
            cond=(scu>0 and scu<sop) or (scu<0 and sop<0 and abs(scu)>abs(sop))
            if last_ris=="0-1" and scu<sop and red: bet="OVER 1.5";reg="R5"
            elif last_ris=="0-0" and cond: bet="OVER 0.5";reg="R1"
            elif last_ris=="1-0" and abs(scu)>0.75 and cond: bet="OVER 1.5";reg="R2"
            elif last_ris=="0-1" and abs(scu)>0.75 and cond: bet="OVER 1.5";reg="R3"
            elif last_ris=="1-1" and abs(scu)==1 and cond: bet="OVER 2.5";reg="R4"
            if bet:
                subj=f"[{reg}] {last_a} vs {last_b} ({last_ris}) {bet} {last_m}'"
                html=f"{last_a} vs {last_b} {last_m}' {last_ris} {bet}<br>{scu_r} vs {sop_r} red={red}"
                if MAIL(subj,html):
                    db.append({"id":mid,"ora":DT.now().strftime("%H:%M"),"a":last_a,"b":last_b,"m":last_m,"ris":last_ris,"bet":bet,"reg":reg})
                    fnd.append({"reg":reg,"match":f"{last_a} vs {last_b}","bet":bet})
        S(db)
        return jsonify({"trovati":fnd,"tot":len(db),"len":len(h)})
    except Exception as e:
        return jsonify({"error":str(e),"trovati":[]})

@app.route("/reset")
def reset(): S([]); return jsonify({"reset":True})
@app.route("/stats")
def stats(): return jsonify(L())
@app.route("/test_mail")
def test_mail(): return jsonify({"sent":MAIL("[TEST] Bot OK","Test riuscito")})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
