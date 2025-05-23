# not being used right now
from flask import Flask, request, jsonify
from flask_cors import CORS
from eth_account.messages import encode_defunct
from eth_account import Account
import jwt
import time
import os

app = Flask(__name__)
CORS(app)

# Secret for JWT (keep it safe in real apps)
SECRET_KEY = os.environ.get("JWT_SECRET", "dev_secret_key")

# Simulated nonce store
nonces = {}

@app.route('/get_nonce', methods=['POST'])
def get_nonce():
    data = request.get_json()
    address = data.get("address")
    if not address:
        return jsonify({"error": "Address required"}), 400
    nonce = f"Login nonce: {int(time.time())}"
    nonces[address.lower()] = nonce
    return jsonify({"nonce": nonce})

@app.route('/verify_signature', methods=['POST'])
def verify_signature():
    data = request.get_json()
    address = data.get("address", "").lower()
    signature = data.get("signature")

    if address not in nonces:
        return jsonify({"error": "Nonce not found"}), 400

    message = encode_defunct(text=nonces[address])
    try:
        recovered_address = Account.recover_message(message, signature=signature)
        if recovered_address.lower() == address:
            # Issue JWT
            payload = {
                "sub": address,
                "exp": time.time() + 86400  # Expires in 1 day
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            return jsonify({"token": token})
        else:
            return jsonify({"error": "Signature mismatch"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
