import os, json, re
from flask import Flask, jsonify
from datetime import datetime as DT
import requests
from bs4 import BeautifulSoup as BS

app = Flask(__name__)

DB="db.json"
TO="paolo.zapp82@yahoo.com"
U="https://www.asianbetsoccer.com/livescore.html"
H={"User-Agent":"Mozilla/5.0 Chrome/124.0","Referer":U}
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
    for url in [U,f"https://api.allorigins.win/raw?url={U}",f"https://corsproxy.io/?{U}"]:
        try:
            t=requests.get(url,headers=H,timeout=20).text
            if len(t)>8000: return t
        except: pass
    return ""

@app.route("/")
def home(): return f"ON R1-R5 49-75 Tot:{len(L())} {DT.now().strftime('%H:%M')}"

@app.route("/debug")
def dbg():
    h=F()
    return jsonify({"len":len(h),"ok":len(h)>5000})

@app.route("/live")
def live():
    h=F();soup=BS(h,"html.parser");out=[]
    for tr in soup.find_all("tr"):
        txt=tr.get_text(" ",strip=True)
        if re.search(r"\d+:\s*\[",txt):
            out.append(txt[:180])
    return jsonify({"live":out[:40],"count":len(out),"len":len(h)})

@app.route("/reset")
def reset(): S([]); return jsonify({"reset":True})

@app.route("/stats")
def stats(): return jsonify(L())

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
            mm=re.search(r"(\d+)\s*\[",txt)
            mr=re.search(r"(\d+)\s*-\s*(\d+)",txt)
            if mm and mr:
                last_m=int(mm.group(1))
                last_ris=f"{mr.group(1)}-{mr.group(2)}"
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
            
            # --- LE 5 REGOLE COMPLETE ---
            if last_ris=="0-1" and scu<sop and red:
                bet="OVER 1.5";reg="R5"
            elif last_ris=="0-0" and cond:
                bet="OVER 0.5";reg="R1"
            elif last_ris=="1-0" and abs(scu)>0.75 and cond:
                bet="OVER 1.5";reg="R2"
            elif last_ris=="0-1" and abs(scu)>0.75 and cond:
                bet="OVER 1.5";reg="R3"
            elif last_ris=="1-1" and abs(scu)==1 and cond:
                bet="OVER 2.5";reg="R4"

            if bet:
                subj=f"[{reg}] {last_a} vs {last_b} ({last_ris}) {bet} {last_m}'"
                html=f"{last_a} vs {last_b} {last_m}' {last_ris} {bet}<br>{scu_r} vs {sop_r} red={red}"
                if MAIL(subj,html):
                    db.append({"id":mid,"ora":DT.now().strftime("%H:%M"),"a":last_a,"b":last_b,"m":last_m,"ris":last_ris,"bet":bet,"reg":reg})
                    fnd.append({"reg":reg,"match":f"{last_a} vs {last_b}","bet":bet})
        S(db)
        return jsonify({"trovati":fnd,"tot":len(db),"range":"40-75"})
    except Exception as e:
        return jsonify({"error":str(e),"trovati":[]})

@app.route("/test_mail")
def test_mail():
    r=MAIL("[TEST] Bot OK","Test invio riuscito")
    return jsonify({"sent":r})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
