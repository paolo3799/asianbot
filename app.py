from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot LIVE - OK", 200

@app.route('/debug')
def debug():
    return jsonify({"ok": True, "msg": "Deploy riuscito!"})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print(data)
    return jsonify({"ok": True})
