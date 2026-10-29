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
    try:
        if os.path.exists(DB): return json.load(open(DB))
    except: pass
    return []
def S(d):
    try: json.dump(d,open(DB,'w'))
    except: pass
def PF(s):
    m=re.search(r'\+?-?\d+(?:\.\d+)?',str(s).replace('--','-'))
    return float(m.group()) if m else None
def RED(td): return 'red' in str(td).lower() or 'ff0000' in str(td).lower()
def MAIL(sub,html):
    try:
        r=requests.post('https://api.brevo.com/v3/smtp/email',
        headers={'api-key':KEY,'Content-Type':'application/json'},
        json={'sender':{'email':'bot@asianbot.com'},'to':[{'email':TO}],'subject':sub,'htmlContent':html},timeout=10)
        return r.status_code<400
    except: return False

def GET(url):
    proxies = [
        f'https://api.allorigins.win/raw?url={url}',
        f'https://corsproxy.io/?{url}',
    ]
    for p in proxies:
        try:
            t = requests.get(p, headers={'User-Agent':'Mozilla/5.0 Chrome/124'}, timeout=6).text
            if len(t) > 2000:
                return t
        except: pass
    try:
        return requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=5).text
    except: return ''

def F(): return GET(U)

@app.route('/')
def home(): return f"ON V9 R1-R5 Tot:{len(L())} {DT.now().strftime('%H:%M')}"

@app.route('/debug')
def dbg():
    try:
        h=F()
        return jsonify({'len':len(h),'ok':len(h)>2000,'first':h[:250]})
    except Exception as e:
        return jsonify({'len':0,'ok':False,'err':str(e)})

@app.route('/live')
def live():
    try:
        h=F()
        if len(h)<800: return jsonify({'count':0,'len':len(h),'err':'bloccato'})
        soup=BS(h,'html.parser')
        out=[]
        for tr in soup.find_all('tr'):
            txt=tr.get_text(' ',strip=True)
            if re.search(r'\d+\s*-\s*\d+',txt) and 10<len(txt)<250:
                out.append(txt[:180])
        return jsonify({'count':len(out),'len':len(h),'live':out[:60]})
    except Exception as e:
        return jsonify({'count':0,'err':str(e)})

@app.route('/scan')
def scan():
    db=L(); fnd=[]; h=F()
    if len(h)<800: return jsonify({'trovati':[],'tot':len(db),'len':len(h),'err':'bloccato - riprovo'})
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
        if len(cols)>=2:
            last_a=cols[0][:30]; last_b=cols[1][:30]
            if mm: continue
        if not(40<=last_m<=75): continue
        scu=sop=None; scu_r=''; red=False
        for i in range(len(cols)-1):
            cu=PF(cols[i]); op=PF(cols[i+1])
            if cu is None or op is None: continue
            if abs(cu)<=4 and abs(op)<=4 and cu!=0 and op!=0:
                scu=cu; sop=op; scu_r=cols[i]
                if RED(tds[i]) or RED(tds[i+1]): red=True
                break
        if scu is None: continue
        mid=f"{last_a}-{last_b}-{last_m}-{last_ris}-{scu_r}".replace(' ','_')
        if any(x.get('id')==mid for x in db): continue
        bet=None; reg=None
        cond=(scu>0 and scu<sop) or (scu<0 and sop<0 and abs(scu)>abs(sop))
        if last_ris=='0-1' and scu<sop and red: bet='OVER 1.5'; reg='R5'
        elif last_ris=='0-0' and cond: bet='OVER 0.5'; reg='R1'
        elif last_ris=='1-0' and abs(scu)>0.75 and cond: bet='OVER 1.5'; reg='R2'
        elif last_ris=='0-1' and abs(scu)>0.75 and cond: bet='OVER 1.5'; reg='R3'
        elif last_ris=='1-1' and abs(scu)==1 and cond: bet='OVER 2.5'; reg='R4'
        if bet:
            if MAIL(f"[{reg}] {last_a} vs {last_b} ({last_ris}) {bet} {last_m}'", f"{last_a} vs {last_b} {last_m}' {last_ris} {bet}"):
                db.append({'id':mid,'ora':DT.now().strftime('%H:%M'),'a':last_a,'b':last_b,'m':last_m,'ris':last_ris,'bet':bet,'reg':reg})
                fnd.append({'reg':reg,'match':f"{last_a} vs {last_b}"})
    S(db)
    return jsonify({'trovati':fnd,'tot':len(db),'len':len(h)})

@app.route('/reset')
def reset(): S([]); return jsonify({'reset':True})
@app.route('/stats')
def stats(): return jsonify(L())
@app.route('/test_mail')
def test_mail(): return jsonify({'sent':MAIL('[TEST V9]','ok')})

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
