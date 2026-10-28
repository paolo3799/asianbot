ora ci vado a mettere per la centesima volta questo ok? 

import os,json,re,requests,urllib.parse
from flask import Flask,jsonify
from bs4 import BeautifulSoup as BS
from datetime import datetime as DT

app=Flask(__name__)
DB="/tmp/pronostici.json"
KEY=os.environ.get("BREVO_API_KEY","")
SND=os.environ.get("SENDER_EMAIL","paolo.zapp82@yahoo.com")
TO="paolo.zapp82@yahoo.com"

# lista + proxy per sbloccare Render
ORIG=[
 "https://live.nowgoal5.com/",
 "https://www.nowgoal5.com/",
 "https://live2.nowgoal5.com/",
 "https://www.nowgoal6.com/",
 "https://live.nowgoal6.com/"
]
H={"User-Agent":"Mozilla/5.0 Chrome/124.0","Accept":"text/html,application/xhtml+xml","Referer":"https://www.google.com/"}

def L():
 try:return json.load(open(DB)) if os.path.exists(DB) else []
 except:return[]
def S(d):
 try:json.dump(d,open(DB,"w"),ensure_ascii=False,indent=2)
 except:pass
def PF(s):
 m=re.search(r"[+-]?\d+(?:\.\d+)?",str(s).replace("−","-"))
 return float(m.group()) if m else None
def MAIL(sub,html):
 try:
  r=requests.post("https://api.brevo.com/v3/smtp/email",headers={"api-key":KEY,"Content-Type":"application/json"},json={"sender":{"email":SND},"to":[{"email":TO}],"subject":sub,"htmlContent":html},timeout=20)
  return r.status_code<400
 except:return False

def FETCH(url):
 # prova diretto
 try:
  t=requests.get(url,headers=H,timeout=15).text
  if len(t)>8000:return t
 except:pass
 # prova via proxy 1
 try:
  p="https://api.allorigins.win/raw?url="+urllib.parse.quote(url,safe='')
  t=requests.get(p,headers=H,timeout=15).text
  if len(t)>8000:return t
 except:pass
 # prova via proxy 2
 try:
  p="https://corsproxy.io/?"+urllib.parse.quote(url,safe='')
  t=requests.get(p,headers=H,timeout=15).text
  if len(t)>8000:return t
 except:pass
 return ""

def F():
 for u in ORIG:
  t=FETCH(u)
  if t and len(t)>8000:return t
 return ""

@app.route("/")
def home():return f"ON R1-R5 NOWGOAL+PROXY 49-75 Tot:{len(L())} {DT.now().strftime('%H:%M')}"

@app.route("/debug")
def dbg():
 h=F();return jsonify({"len":len(h),"ok":len(h)>5000,"preview":h[:500] if h else "empty"})

@app.route("/live")
def live():
 h=F();soup=BS(h,"html.parser");out=[]
 for tr in soup.find_all("tr"):
  txt=tr.get_text(" ",strip=True)
  mm=re.search(r"(\d+)\s*['’´′]",txt)
  mr=re.search(r"\d+\s*-\s*\d+",txt)
  if mm and mr and len(txt)>10:
   out.append(txt[:220])
 return jsonify({"count":len(out),"len":len(h),"live":out[:50]})

@app.route("/reset")
def reset():S([]);return jsonify({"reset":True})

@app.route("/stats")
def stats():return jsonify(L())

@app.route("/scan")
def scan():
 try:
  db=L();fnd=[];h=F()
  if not h or len(h)<5000:return jsonify({"trovati":[],"tot":len(db),"err":f"no html len {len(h)}"})
  soup=BS(h,"html.parser")
  for tr in soup.find_all("tr"):
   txt=tr.get_text(" ",strip=True)
   mm=re.search(r"(\d+)\s*['’´]",txt)
   mr=re.search(r"(\d+)\s*-\s*(\d+)",txt)
   if not(mm and mr):continue
   m=int(mm.group(1))
   if not(49<=m<=75):continue
   ris=f"{mr.group(1)}-{mr.group(2)}"
   cols=[td.get_text(" ",strip=True) for td in tr.find_all("td")]
   hc=None
   for c in cols:
    v=PF(c)
    if v is not None and abs(v)<=3 and v!=0 and ("/" in c or "." in c):
     hc=v;break
   if hc is None:continue
   a=cols[1][:25] if len(cols)>2 else "Home"
   b=cols[2][:25] if len(cols)>2 else "Away"
   mid=f"{a}-{b}-{m}-{ris}-{hc}".replace(" ","_")
   if any(x.get("id")==mid for x in db):continue
   bet=reg=None
   if ris=="0-0":bet="OVER 0.5";reg="R1"
   elif ris=="1-0" and abs(hc)>=0.5:bet="OVER 1.5";reg="R2"
   elif ris=="0-1" and abs(hc)>=0.5:bet="OVER 1.5";reg="R3"
   elif ris=="1-1" and abs(hc)>=0.75:bet="OVER 2.5";reg="R4"
   if bet:
    ok=MAIL(f"[{reg}] {a} vs {b} {ris} {m}' {bet}",f"{a} vs {b} {m}' {ris} {bet} HC:{hc}")
    if ok:
     db.append({"id":mid,"ora":DT.now().strftime("%H:%M"),"a":a,"b":b,"m":m,"ris":ris,"bet":bet,"reg":reg})
     fnd.append(f"{reg} {a}-{b} {ris} {m}'")
  S(db)
  return jsonify({"trovati":fnd,"tot":len(db),"range":"49-75","source":"nowgoal+proxy","len":len(h)})
 except Exception as e:
  return jsonify({"error":str(e),"trovati":[]})

@app.route("/test_all")
def tall():
 ok=MAIL("[TEST] Bot OK","[TEST] Bot funziona")
 return jsonify({"sent":ok})

if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
