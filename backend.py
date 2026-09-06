from flask import Flask, request, jsonify
from flask_cors import CORS
from regexfinal import scan_text

app = Flask(__name__)
CORS(app)  # Enables cross-origin requests from the Chrome extension


@app.route('/analyze', methods=['POST'])
def analyze_text():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    url = data.get('url', 'unknown')

    print(f"\n[SCANNING] Payload from {url}")

    if not text:
        return jsonify({"status": "error", "message": "no text provided"}), 400

    result = scan_text(text)
    result["status"] = "success"
    # keep a 0-1 threat_score around for any older client code that expects it
    result["threat_score"] = result["risk_score"] / 100
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
