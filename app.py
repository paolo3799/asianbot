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

@app.route("/scan")
def scan():
    try:
        db=L();fnd=[];h=F()
        if not h: return jsonify({"trovati":[],"tot":len(db),"err":"no html"})
        soup=BS(h,"html.parser")
        last_a="A";last_b="B";last_m=0;last_ris=""
        for tr in soup.find_all("tr"):
            tds=tr.find_all("td")
            if len(tds)<3
