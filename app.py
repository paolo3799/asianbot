import os,json,re,requests
from flask import Flask,jsonify
from bs4 import BeautifulSoup as BS
from datetime import datetime as DT
app=Flask(__name__)
DB="/tmp/pronostici.json"
KEY=os.environ.get("BREVO_API_KEY","")
SND=os.environ.get("SENDER_EMAIL","paolo.zapp82@yahoo.com")
TO="paolo.zapp82@yahoo.com"
U="https://www.asianbetsoccer.com/livescore.html"
H={"User-Agent":"Mozilla/5.0 Chrome/124.0","Referer":U}
def L():
 try:return json.load(open(DB)) if os.path.exists(DB) else []
 except:return[]
def S(d):
 try:json.dump(d,open(DB,"w"),ensure_ascii=False,indent=2)
 except:pass
def PF(s):
 m=re.search(r"[+-]?\d+(?:\.\d+)?",str(s).replace("−","-"))
 return float(m.group()) if m else None
def RED(td):
 h=str(td).lower()
 return "red" in h or "ff0000" in h or "#f00" in h
def MAIL(sub,html):
 try:
  r=requests.post("https://api.brevo.com/v3/smtp/email",headers={"api-key":KEY,"Content-Type":"application/json"},json={"sender":{"email":SND},"to":[{"email":TO}],"subject":sub,"htmlContent":html},timeout=15)
  return r.status_code<400
 except:return False
def F():
 for u in [U,f"https://api.allorigins.win/raw?url={U}",f"https://corsproxy.io/?{U}"]:
  try:
   t=requests.get(u,headers=H,timeout=20).text
   if len(t)>5000:return t
  except:pass
 return""
@app.route("/")
def home():return f"ON R5 Tot:{len(L())} {DT.now().strftime('%H:%M')}"
@app.route("/debug")
def dbg():h=F();return jsonify({"len":len(h),"ok":len(h)>5000})
@app.route("/scan")
def scan():
 try:
  db=L();fnd=[];h=F()
  if not h:return jsonify({"trovati":[],"tot":len(db)})
  soup=BS(h,"html.parser")
  for tr in soup.find_all("tr"):
   tds=tr.find_all("td")
   if len(tds)<6:continue
   txt=tr.get_text(" ",strip=True)
   mm=re.search(r"(\d+)\s*['′]",txt)
   if not mm:continue
   m=int(mm.group(1))
   if not(m==50 or 50<=m<=60):continue
   mr=re.search(r"(\d+)\s*-\s*(\d+)",txt)
   if not mr:continue
   ris=f"{mr.group(1)}-{mr.group(2)}"
   if tr.find("img",src=lambda x:x and "red" in x.lower() if x else False):continue
   cols=[td.get_text(" ",strip=True) for td in tds]
   camp=cols[0];a=cols[2] if len(cols)>2 else"A";b=cols[3] if len(cols)>3 else"B"
   scu=sop=None;scu_td=None;scu_r=sop_r="";red=False
   for i in range(len(cols)-1):
    cu=PF(cols[i]);op=PF(cols[i+1])
    if cu is None or op is None:continue
    if abs(cu)<=4 and abs(op)<=4:
     scu=cu;sop=op;scu_td=tds[i] if i<len(tds) else None;scu_r=cols[i];sop_r=cols[i+1]
     if scu_td and RED(scu_td):red=True
     break
   if scu is None:continue
   mid=f"{a}-{b}-{m}-{ris}-{scu_r}".replace(" ","_")
   if any(x.get("id")==mid for x in db):continue
   bet=reg=None;cond=(scu>0 and scu>sop) or (scu<0 and scu<sop)
   if m==50 and ris=="0-1" and scu!=sop and red:bet="OVER 1.5";reg="R5"
   elif ris=="0-0" and cond:bet="OVER 0.5";reg="R1"
   elif ris=="1-0" and abs(scu)>=0.75 and cond:bet="OVER 1.5";reg="R2"
   elif ris=="0-1" and abs(scu)>=0.75 and cond:bet="OVER 1.5";reg="R3"
   elif ris=="1-1" and abs(scu)>=1 and cond:bet="OVER 2.5";reg="R4"
   if bet:
    MAIL(f"[{reg}] {a} vs {b} {ris} {m}' {bet}",f"{camp}<br>{a} vs {b} {m}' {ris} {bet}<br>CU:{scu_r} OP:{sop_r} RED:{red}")
    db.append({"id":mid,"ora":DT.now().strftime("%H:%M"),"a":a,"b":b,"m":m,"ris":ris,"bet":bet,"reg":reg})
    fnd.append(mid)
  S(db);return jsonify({"trovati":fnd,"tot":len(db),"r5":True})
 except Exception as e:return jsonify({"error":str(e),"trovati":[]})
@app.route("/stats")
def stats():return jsonify(L())
@app.route("/test_r5")
def t5():ok=MAIL("[R5] TEST 0-1 50' RED","Turkey TEST 0-1 50' SPREAD ROSSO");return jsonify({"sent":ok})
@app.route("/test_r3")
def t3():ok=MAIL("[R3] TEST 0-1 56'","TEST R3");return jsonify({"sent":ok})
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
