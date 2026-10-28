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
 if not td: return False
 h=str(td).lower()
 return "red" in h or "ff0000" in h or "#f00" in h or "color:red" in h or "background:#f" in h
def MAIL(sub,html):
 try:
  r=requests.post("https://api.brevo.com/v3/smtp/email",headers={"api-key":KEY,"Content-Type":"application/json"},json={"sender":{"email":SND},"to":[{"email":TO}],"subject":sub,"htmlContent":html},timeout=20)
  return r.status_code<400
 except:return False
def F():
 for url in [U,f"https://api.allorigins.win/raw?url={U}",f"https://corsproxy.io/?{U}"]:
  try:
   t=requests.get(url,headers=H,timeout=20).text
   if len(t)>8000:return t
  except:pass
 return""

@app.route("/")
def home():return f"ON R1-R5 49-65 Tot:{len(L())} {DT.now().strftime('%H:%M')}"
@app.route("/debug")
def dbg():h=F();return jsonify({"len":len(h),"ok":len(h)>5000})
@app.route("/reset")
def reset():S([]);return jsonify({"reset":True})
@app.route("/stats")
def stats():return jsonify(L())

@app.route("/live")
def live():
 h=F(); soup=BS(h,"html.parser"); out=[]
 for tr in soup.find_all("tr"):
  tds=tr.find_all("td")
  if len(tds)<3:continue
  txt=tr.get_text(" ",strip=True)
  mm=re.search(r"(\d+)\s*['′]",txt)
  if not mm:continue
  m=int(mm.group(1))
  if 40<=m<=75:
   out.append(txt[:180])
 return jsonify({"live_40_75":out[:30],"count":len(out)})

@app.route("/scan")
def scan():
 try:
  db=L();fnd=[];h=F()
  if not h:return jsonify({"trovati":[],"tot":len(db),"err":"no html"})
  soup=BS(h,"html.parser")
  last_a="A";last_b="B";last_m=0;last_ris=""
  for tr in soup.find_all("tr"):
   tds=tr.find_all("td")
   if len(tds)<3:continue
   txt=tr.get_text(" ",strip=True)
   mm=re.search(r"(\d+)\s*['′]",txt)
   mr=re.search(r"(\d+)\s*-\s*(\d+)",txt)
   if mm and mr and ("ht" in txt.lower() or "ck" in txt.lower()):
    last_m=int(mm.group(1));last_ris=f"{mr.group(1)}-{mr.group(2)}"
    cols=[td.get_text(" ",strip=True) for td in tds]
    if len(cols)>=2:
     last_a=cols[0][:30];last_b=cols[1][:30] if len(cols)>1 else "B"
    continue
   if not(49<=last_m<=65):continue
   cols=[td.get_text(" ",strip=True) for td in tds]
   scu=sop=None;scu_r=sop_r="";red=False
   for i in range(len(cols)-1):
    cu=PF(cols[i]);op=PF(cols[i+1])
    if cu is None or op is None:continue
    if abs(cu)<=4 and abs(op)<=4 and cu!=0 and op!=0:
     scu=cu;sop=op;scu_r=cols[i];sop_r=cols[i+1]
     td_cu=tds[i] if i < len(tds) else None
     td_op=tds[i+1] if i+1 < len(tds) else None
     if RED(td_cu) or RED(td_op):red=True
     break
   if scu is None:continue
   mid=f"{last_a}-{last_b}-{last_m}-{last_ris}-{scu_r}".replace(" ","_")
   if any(x.get("id")==mid for x in db):continue
   bet=reg=None;cond=(scu>0 and scu>sop) or (scu<0 and scu<sop)
   if last_ris=="0-1" and scu!=sop and red:bet="OVER 1.5";reg="R5"
   elif last_ris=="0-0" and cond:bet="OVER 0.5";reg="R1"
   elif last_ris=="1-0" and abs(scu)>=0.75 and cond:bet="OVER 1.5";reg="R2"
   elif last_ris=="0-1" and abs(scu)>=0.75 and cond:bet="OVER 1.5";reg="R3"
   elif last_ris=="1-1" and abs(scu)>=1 and cond:bet="OVER 2.5";reg="R4"
   if bet:
    ok=MAIL(f"[{reg}] {last_a} vs {last_b} {last_ris} {last_m}' {bet}",f"{last_a} vs {last_b} {last_m}' {last_ris} {bet} CU:{scu_r} OP:{sop_r} RED:{red}")
    if ok:
     db.append({"id":mid,"ora":DT.now().strftime("%H:%M"),"a":last_a,"b":last_b,"m":last_m,"ris":last_ris,"bet":bet,"reg":reg})
     fnd.append(f"{reg} {last_a}-{last_b} {last_ris} {last_m}'")
  S(db);return jsonify({"trovati":fnd,"tot":len(db),"range":"49-65"})
 except Exception as e:return jsonify({"error":str(e),"trovati":[]})

@app.route("/test_all")
def tall():
 r1=MAIL("[R1] TEST 0-0 49-65","TEST R1");r3=MAIL("[R3] TEST 0-1 49-65","TEST R3");r5=MAIL("[R5] TEST 0-1 RED 49-65","TEST R5")
 return jsonify({"r1":r1,"r3":r3,"r5":r5})

if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
