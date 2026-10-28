import os, json, re, requests
from flask import Flask, jsonify
from datetime import datetime as DT

app = Flask(__name__)
DB='db.json'
KEY=os.environ.get('BREVO_KEY','')

def L():
    try:
        if os.path.exists(DB): return json.load(open(DB))
    except: pass
    return []
def S(d):
    try: json.dump(d,open(DB,'w'))
    except: pass

@app.route('/')
def home():
    return f"ON V7 OK Tot:{len(L())} {DT.now().strftime('%H:%M')}"

@app.route('/debug')
def dbg():
    try:
        r=requests.get('https://www.asianbetsoccer.com/livescore.html', headers={'User-Agent':'Mozilla/5.0'}, timeout=6)
        return jsonify({'len':len(r.text), 'ok': len(r.text)>1000, 'code': r.status_code})
    except Exception as e:
        return jsonify({'len':0, 'err': str(e)})

@app.route('/scan')
def scan(): return jsonify({'trovati':[], 'msg':'scan disattivato per far partire Render'})

@app.route('/test_mail')
def test_mail():
    try:
        import requests as req
        res=req.post('https://api.brevo.com/v3/smtp/email',
        headers={'api-key':KEY,'Content-Type':'application/json'},
        json={'sender':{'email':'bot@asianbot.com'},'to':[{'email':'paolo.zapp82@yahoo.com'}],'subject':'[TEST V7]','htmlContent':'Test ok'}, timeout=8)
        return jsonify({'sent': res.status_code<400, 'code': res.status_code})
    except Exception as e:
        return jsonify({'sent':False, 'err':str(e)})

@app.route('/reset')
def reset(): S([]); return jsonify({'reset':True})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))
