import os, json, re, requests
from flask import Flask, jsonify
from datetime import datetime as DT
from bs4 import BeautifulSoup as BS

app = Flask(__name__)
DB='db.json'
TO='paolo.zapp82@yahoo.com'
U='https://www.asianbetsoccer.com/livescore.html'
KEY=os.environ.get('BREVO_KEY','')

def L():
    try: return json.load(open(DB))
    except: return []
def S(d): json.dump(d, open(DB,'w'))
def PF(s):
    m=re.search(r'\+?-?\d+(?:\.\d+)?',str(s).replace('--','-'))
    return float(m.group()) if m else None
def RED(td): return 'red' in str(td).lower()
def MAIL(sub,html):
    try:
        r=requests.post('https://api.brevo.com/v3/smtp/email',
        headers={'api-key':KEY,'Content-Type':'application/json'},
        json={'sender':{'email':'bot@asianbot.com'},'to':[{'email':TO}],'subject':sub,'htmlContent':html},timeout=10)
        return r.status_code<400
    except: return False

def GET():
    try:
        r=requests.get(U, headers={'User-Agent':'Mozilla/5.0 Chrome/124'}, timeout=7)
        h=r.text
        if 'sgcaptcha' in h or len(h)<2000: return ''
        return h
    except: return ''

@app.route('/')
def home(): return f"ON V15 R1-R5 Tot:{len(L())} {DT.now().strftime('%H:%M')}"

@app.route('/debug')
def dbg():
    try:
        r=requests.get(U, headers={'User-Agent':'Mozilla/5.0'}, timeout=6)
        return jsonify(len=len(r.text), captcha='sgcaptcha' in r.text, ok=len(r.text)>5000)
    except Exception as e: return jsonify(err=str(e)[:100])

@app.route('/scan')
def scan():
    try:
        h=GET()
        db=L(); fnd=0
        if h:
            soup=BS(h,'html.parser')
            last_a='A'; last_b='B'; last_m=0; last_ris=''
            for tr in soup.find_all('tr'):
                tds=tr.find_all('td')
                if len(tds)<3: continue
                txt=tr.get_text(' ',strip=True)
                mm=re.search(r'(\d+)\s*\[',txt); mr=re.search(r'(\d+)\s*-\s*(\d+)',txt)
                if mm and mr:
                    last_m=int(mm.group(1)); last_ris=f"{mr.group(1)}-{mr.group(2)}"
                cols=[td.get_text(' ',strip=True) for td in tds]
                if len(cols)>=2 and not mm:
                    last_a=cols[0][:30]; last_b=cols[1][:30]
                if not(40<=last_m<=75): continue
                scu=sop=None; scu_r=''; red=False
                for i in range(len(cols)-1):
                    cu=PF(cols[i]); op=PF(cols[i+1])
                    if cu is None or op is None: continue
                    if abs(cu)<=4 and abs(op)<=4 and cu!=0:
                        scu=cu; sop=op; scu_r=cols[i]
                        if RED(tds[i]): red=True
                        break
                if scu is None: continue
                mid=f"{last_a}-{last_b}-{last_m}-{last_ris}-{scu_r}".replace(' ','_')
                if any(x.get('id')==mid for x in db): continue
                cond=(scu>0 and scu<sop) or (scu<0 and sop<0 and abs(scu)>abs(sop))
                bet=None; reg=None
                if last_ris=='0-1' and scu<sop and red: bet='OVER 1.5'; reg='R5'
                elif last_ris=='0-0' and cond: bet='OVER 0.5'; reg='R1'
                elif last_ris=='1-0' and abs(scu)>0.75 and cond: bet='OVER 1.5'; reg='R2'
                elif last_ris=='0-1' and abs(scu)>0.75 and cond: bet='OVER 1.5'; reg='R3'
                elif last_ris=='1-1' and abs(scu)==1 and cond: bet='OVER 2.5'; reg='R4'
                if bet and MAIL(f"[{reg}] {last_a} vs {last_b} ({last_ris}) {bet} {last_m}'", f"{bet} {last_m}'"):
                    db.append({'id':mid}); fnd+=1
            S(db)
        # RISPOSTA MINI per cron-job.org - 15 byte, mai piu "output troppo grande"
        return jsonify(t=fnd, tot=len(db), ok=1)
    except:
        return jsonify(t=0, ok=1)

@app.route('/reset')
def reset(): S([]); return jsonify(reset=True)

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
