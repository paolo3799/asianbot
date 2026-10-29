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

def GET():
    try:
        r=requests.get(U, headers={'User-Agent':'Mozilla/5.0'}, timeout=6)
        h=r.text
        if 'sgcaptcha' in h or len(h)<1000:
            return ''
        return h
    except:
        return ''

@app.route('/')
def home():
    return f"ON V14 Tot:{len(L())}"

@app.route('/debug')
def dbg():
    try:
        r=requests.get(U, headers={'User-Agent':'Mozilla/5.0'}, timeout=6)
        return jsonify(ok=len(r.text)>2000, len=len(r.text), captcha='sgcaptcha' in r.text)
    except Exception as e:
        return jsonify(ok=False, err=str(e)[:80])

@app.route('/live')
def live():
    h=GET()
    if not h:
        return jsonify(count=0, msg='bloccato o vuoto')
    soup=BS(h,'html.parser')
    c=0
    for tr in soup.find_all('tr'):
        if re.search(r'\d+\s*-\s*\d+',tr.get_text()):
            c+=1
    return jsonify(count=c)

@app.route('/scan')
def scan():
    # QUESTO E' QUELLO CHE CHIAMA CRON-JOB.ORG - DEVE ESSERE PICCOLISSIMO
    try:
        h=GET()
        if not h:
            return jsonify(t=0, ok=1)  # risposta di 10 byte, non fallisce mai

        soup=BS(h,'html.parser')
        db=L()
        # qui la tua logica R1-R5, ma senza ritornare liste grandi
        # per ora ritorna solo il conteggio per non far fallire cron-job
        return jsonify(t=len(db), ok=1)
    except:
        return jsonify(t=0, ok=1)

@app.route('/reset')
def reset():
    S([])
    return jsonify(reset=True)

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
