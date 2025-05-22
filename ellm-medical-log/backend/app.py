# Updated `app.py`

from flask import Flask, request, jsonify, render_template
from web3 import Web3
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
from eth_account import Account
from eth_account.messages import encode_defunct


# Import services
from services.ipfsService import ipfs_service
from services.blockchainService import blockchain_service

load_dotenv()  # Load environment variables

app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static')

# --- Helper Functions ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        # Add token verification logic if needed
        return f(*args, **kwargs)
    return decorated

# --- Blockchain Setup ---
w3 = Web3(Web3.HTTPProvider(os.getenv('BLOCKCHAIN_RPC_URL', 'http://127.0.0.1:7545')))
contract_address = os.getenv('CONTRACT_ADDRESS')

# Load Contract ABI
current_dir = os.path.dirname(os.path.abspath(__file__))
# with open(os.path.join(current_dir, '..', 'contracts', 'abi.json')) as f:
#     abi = json.load(f)

# In app.py, replace the ABI loading with:
with open(os.path.join(current_dir,  'artifacts', 'contracts', 'MedicalRecord.sol', 'MedicalRecord.json')) as f:
    contract_artifact = json.load(f)
    abi = contract_artifact['abi']

contract = w3.eth.contract(address=contract_address, abi=abi)

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/records/signed', methods=['POST'])
@token_required
def add_signed_record():
    try:
        payload = request.json
        data = payload.get("data")
        signature = payload.get("signature")
        sender_address = Web3.to_checksum_address(request.headers.get("X-User-Address"))

        if not data or not signature:
            return jsonify({"error": "Missing data or signature"}), 400

        # Recover signer from the signature
        message = json.dumps(data, separators=(",", ":"), sort_keys=False)
        message_encoded = encode_defunct(text=message)
        recovered_address = w3.eth.account.recover_message(message_encoded, signature=signature)

        if Web3.to_checksum_address(recovered_address) != sender_address:
            return jsonify({"error": f"Invalid signature\n{Web3.to_checksum_address(recovered_address)}\n{sender_address}"}), 403

        # Optional: Check role in contract (to enforce permissions)
        is_authorized = any([
            contract.functions.isDoctor(sender_address).call(),
            contract.functions.isNurse(sender_address).call(),
            contract.functions.isStaff(sender_address).call()
        ])
        if not is_authorized:
            return jsonify({'error': 'Unauthorized personnel'}), 403

        # Save to DB or IPFS metadata registry (not shown here)
        return jsonify({"message": "Record verified and saved (off-chain)"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# @app.route('/api/records/prepare_tx', methods=['POST'])
# @token_required
# def prepare_medical_record_tx():
#     try:
#         required_fields = ['patientAddress', 'condition', 'diagnosis', 'treatment', 'senderAddress']
#         data = request.json

#         if not all(field in data for field in required_fields):
#             return jsonify({'error': 'Missing required fields'}), 400

#         patient_address = Web3.to_checksum_address(data['patientAddress'])
#         sender_address = Web3.to_checksum_address(data['senderAddress'])

#         # Role check
#         is_doctor = contract.functions.isDoctor(sender_address).call()
#         is_nurse = contract.functions.isNurse(sender_address).call()
#         is_staff = contract.functions.isStaff(sender_address).call()

#         if not (is_doctor or is_nurse or is_staff):
#             return jsonify({'error': 'Unauthorized'}), 403

#         ipfs_hash = data.get('ipfsHash', '')

#         nonce = w3.eth.get_transaction_count(sender_address)

#         tx = contract.functions.addMedicalRecord(
#             patient_address,
#             data['condition'],
#             data['diagnosis'],
#             data['treatment'],
#             ipfs_hash
#         ).build_transaction({
#             'from': sender_address,
#             'nonce': nonce,
#             'gas': 500000,
#             'gasPrice': w3.to_wei('20', 'gwei')
#         })

#         tx['gas'] = Web3.to_hex(tx['gas'])
#         tx['gasPrice'] = Web3.to_hex(tx['gasPrice'])
#         tx['nonce'] = Web3.to_hex(tx['nonce'])

#         return jsonify(tx), 200

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


@app.route('/api/records/<address>', methods=['GET'])
@token_required
def get_records(address):
    try:
        caller_address = request.headers.get('X-User-Address')

        is_owner = caller_address.lower() == address.lower()
        is_authorized = (
            contract.functions.isDoctor(caller_address).call() or
            contract.functions.isNurse(caller_address).call() or
            contract.functions.isStaff(caller_address).call()
        )

        if not (is_owner or is_authorized):
            return jsonify({'error': 'Unauthorized access'}), 403

        records = contract.functions.getPatientRecords(address).call()

        return jsonify({'blockchain_records': records}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload_to_ipfs', methods=['POST'])
def upload_to_ipfs():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        ipfs_hash = ipfs_service.upload_file(file.read())
        return jsonify({
            'ipfsHash': ipfs_hash,
            'ipfs_url': f"https://ipfs.io/ipfs/{ipfs_hash}",
            'message': 'File uploaded to IPFS'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/admin/add_role', methods=['POST'])
@token_required
def add_role():
    try:
        sender_address = request.headers.get('X-User-Address')
        sender_address = Web3.to_checksum_address(sender_address)
        role = request.json.get('role')

        if not role:
            return jsonify({'error': 'Role is required'}), 400

        # Owner's address and private key from environment
        owner_address = os.getenv("OWNER_ADDRESS")
        private_key = os.getenv("PRIVATE_KEY")
        if not private_key or not owner_address:
            return jsonify({'error': 'Missing owner credentials'}), 500

        # Build transaction to assign role TO the sender_address, signed BY the owner
        tx = contract.functions.assignRole(sender_address, role.lower())

        nonce = w3.eth.get_transaction_count(owner_address)

        built_tx = tx.build_transaction({
            'from': owner_address,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': w3.to_wei('20', 'gwei')
        })

        signed_tx = w3.eth.account.sign_transaction(built_tx, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return jsonify({
            'message': f'{role.capitalize()} role assigned to {sender_address}',
            'transaction_hash': tx_hash.hex()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False') == 'True')
