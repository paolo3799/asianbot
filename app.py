import os,json,re,requests
from flask import Flask,jsonify
from bs4 import BeautifulSoup as BS
from datetime import datetime
app=Flask(__name__)
DB="/tmp/pronostici.json"
KEY=os.environ.get("BREVO_API_KEY","")
SENDER=os.environ.get("SENDER_EMAIL","paolo.zapp82@yahoo.com")
TO="paolo.zapp82@yahoo.com"
URL="https://www.asianbetsoccer.com/livescore.html"
BWIN="https://www.bwin.it/it/sports/live/"
H={"User-Agent":"Mozilla/5.0 Chrome/124.0","Referer":"https://www.asianbetsoccer.com/"}
def load():
 try:
  return json.load(open(DB,encoding="utf-8")) if os.path.exists(DB) else []
 except: return []
def save(d):
 try: json.dump(d,open(DB,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
 except: pass
def pf(s):
 import re
 m=re.search(r"[+-]?\d+(?:\.\d+)?",str(s).replace("−","-"))
 return float(m.group()) if m else None
def mail(sub,html):
 try:
  r=requests.post("https://api.brevo.com/v3/smtp/email",headers={"api-key":KEY,"Content-Type":"application/json"},json={"sender":{"email":SENDER,"name":"Bot"},"to":[{"email":TO}],"subject":sub,"htmlContent":html},timeout=15)
  return r.status_code<400
 except: return False
def body(c,a,b,m,r,bet,sc,so,tc,to):
 return f"{c}<br>{a} vs {b} {m}' {r} {bet}<br>ASIAN:{URL}<br>BWIN:{BWIN}<br>CU:{sc} OP:{so} TCU:{tc} TOP:{to}"
def fetch():
 for u in [URL,f"https://api.allorigins.win/raw?url={URL}",f"https://corsproxy.io/?{URL}"]:
  try:
   t=requests.get(u,headers=H,timeout=20).text
   if len(t)>5000: return t
  except: pass
 return ""
@app.route("/")
def home(): return f"Bot ON Tot:{len(load())} {datetime.now().strftime('%H:%M:%S')}"
@app.route("/debug")
def dbg():
 h=fetch()
 return jsonify({"len":len(h),"ok":len(h)>5000})
@app.route("/scan")
def scan():
 try:
  db=load();found=[]
  h=fetch()
  if not h: return jsonify({"trovati":[],"tot_db":len(db),"err":"fetch vuoto"})
  soup=BS(h,"html.parser")
  for tr in soup.find_all("tr"):
   tds=tr.find_all("td")
   if len(tds)<6: continue
   txt=tr.get_text(" ",strip=True)
   mm=re.search(r"(\d+)\s*['′]",txt)
   if not mm: continue
   m=int(mm.group(1))
   if not 50<=m<=60: continue
   mr=re.search(r"(\d+)\s*-\s*(\d+)",txt)
   if not mr: continue
   ris=f"{mr.group(1)}-{mr.group(2)}"
   if tr.find("img",src=lambda x: x and "red" in x.lower() if x else False): continue
   cols=[td.get_text(" ",strip=True) for td in tds]
   camp=cols[0];a=cols[2] if len(cols)>2 else "A";b=cols[3] if len(cols)>3 else "B"
   scu=sop=None;scu_r=sop_r=tcu_r=top_r=""
   for i in range(len(cols)-1):
    cu=pf(cols[i]);op=pf(cols[i+1])
    if cu is None or op is None: continue
    if abs(cu)<=4 and abs(op)<=4:
     scu=cu;sop=op;scu_r=cols[i];sop_r=cols[i+1]
     if i+2 < len(cols): tcu_r=cols[i+2]
     if i+3 < len(cols): top_r=cols[i+3]
     break
   if scu is None: continue
   mid=f"{a}-{b}-{m}-{ris}".replace(" ","_")
   if any(x.get("id")==mid for x in db): continue
   bet=reg=None;cond=(scu>0 and scu>sop) or (scu<0 and scu<sop)
   if ris=="0-0" and cond: bet="OVER 0.5";reg="R1"
   elif ris=="1-0" and abs(scu)>=0.75 and cond: bet="OVER 1.5";reg="R2"
   elif ris=="0-1" and abs(scu)>=0.75 and cond: bet="OVER 1.5";reg="R3"
   elif ris=="1-1" and abs(scu)>=1 and cond: bet="OVER 2.5";reg="R4"
   if bet:
    mail(f"[{reg}] {a} vs {b} {ris} {m}' {bet}",body(camp,a,b,m,ris,bet,scu_r,sop_r,tcu_r,top_r))
    db.append({"id":mid,"ora":datetime.now().strftime("%H:%M:%S"),"a":a,"b":b,"m":m,"ris":ris,"bet":bet,"reg":reg})
    found.append(mid)
  save(db)
  return jsonify({"trovati":found,"tot_db":len(db)})
 except Exception as e:
  return jsonify({"error":str(e),"trovati":[],"tot_db":len(load())})
@app.route("/stats")
def stats(): return jsonify(load())
@app.route("/test_r3")
def t3():
 ok=mail("[R3] TEST 0-1 56' OVER 1.5",body("TEST","Genk U19","Salzburg U19",56,"0-1","OVER 1.5 TEST","0.75","0.5","1.5","1.25"))
 return jsonify({"sent":ok})
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
