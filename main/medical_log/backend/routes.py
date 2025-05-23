# Updated `medical_log_bp.py`

from flask import Blueprint, request, jsonify, render_template
from web3 import Web3
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
from eth_account import Account
from eth_account.messages import encode_defunct
import time
import requests
import logging

# Import services
from .services.ipfsService import ipfs_service
from .services.blockchainService import blockchain_service

logging.basicConfig(level=logging.INFO)

load_dotenv()  # Load environment variables

medical_log_bp = Blueprint(
    'medical_log',
    __name__,
    url_prefix='/medical_log',
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
print(current_dir)

# In medical_log_bp.py, replace the ABI loading with:
with open(os.path.join(current_dir,  'artifacts', 'contracts', 'MedicalRecord.sol', 'MedicalRecord.json')) as f:
    contract_artifact = json.load(f)
    abi = contract_artifact['abi']

contract = w3.eth.contract(address=contract_address, abi=abi)

# --- Routes ---
@medical_log_bp.route('/')
def index():
    return render_template('index.html')

@medical_log_bp.route('/api/records/signed', methods=['POST'])
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
        
        owner_address = os.getenv("OWNER_ADDRESS")
        private_key = os.getenv("PRIVATE_KEY")

        tx = contract.functions.addMedicalRecord(
            Web3.to_checksum_address(data["patientAddress"]),
            data["condition"],
            data["diagnosis"],
            data["treatment"],
            data["ipfsHash"]
        )
        
        built_tx = tx.build_transaction({
            "from": owner_address,
            "nonce": w3.eth.get_transaction_count(owner_address),
            "gas": 3000000,
            "gasPrice": Web3.to_wei("20", "gwei")
        })

        signed_tx = w3.eth.account.sign_transaction(built_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)

        return jsonify({ "status": "success", "tx_hash": tx_hash.hex() })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@medical_log_bp.route('/api/patient/<patient_address>/records', methods=['GET'])
def get_patient_records(patient_address):
    IPFS_GATEWAY = "https://ipfs.io/ipfs/"
    try:
        viewer_address = request.args.get('viewer')
        if not viewer_address:
            return jsonify({"error": "Missing viewer address"}), 400

        # Fetch records from smart contract (get IPFS hashes and timestamps)
        raw_records = contract.functions.getPatientRecords(
            Web3.to_checksum_address(patient_address)
        ).call({'from': Web3.to_checksum_address(viewer_address)})

        logging.info(raw_records)

        full_records = []
        for r in raw_records:
            condition = r[0]
            diagnosis = r[1]
            treatment = r[2]
            ipfs_hash = r[3]
            timestamp = r[4]

            try:
                # Fetch the record JSON from IPFS
                ipfs_url = f"{IPFS_GATEWAY}{ipfs_hash}"
                response = requests.get(ipfs_url)
                response.raise_for_status()
                # record_data = response.json()

                # Add IPFS metadata
                # record_data['condition'] = condition
                # record_data['diagnosis'] = diagnosis
                # record_data['treatment'] = treatment
                # record_data['ipfsHash'] = ipfs_hash
                # record_data['timestamp'] = timestamp
                record_data = {
                    "condition": condition,
                    "diagnosis": diagnosis,
                    "treatment": treatment,
                    "ipfsHash": ipfs_hash,
                    "timestamp": timestamp,
                    "fileUrl": ipfs_url  # Provide URL to front-end to fetch/display
                }

                full_records.medical_log_bpend(record_data)

            except Exception as e:
                full_records.medical_log_bpend({
                    "error": f"Failed to fetch from IPFS: {str(e)}",
                    "ipfsHash": ipfs_hash,
                    "timestamp": timestamp
                })

        full_records.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
        return jsonify(full_records)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# In-memory storage (replace with DB for production)
patient_authorizations = {}

@medical_log_bp.route('/api/patient/authorize', methods=['POST'])
@token_required
def authorize_access():
    try:
        payload = request.json
        data = payload.get("data")
        signature = payload.get("signature")
        sender_address = Web3.to_checksum_address(request.headers.get("X-User-Address"))

        if not data or not signature:
            return jsonify({"error": "Missing data or signature"}), 400

        # message = json.dumps(data)
        # message_hash = Web3.keccak(text=message)
        # recovered_address = w3.eth.account.recover_message(
        #     encode_defunct(message_hash), signature=signature
        # )

        message = json.dumps(data, separators=(",", ":"), sort_keys=False)
        message_encoded = encode_defunct(text=message)
        recovered_address = w3.eth.account.recover_message(message_encoded, signature=signature)

        if Web3.to_checksum_address(recovered_address) != sender_address:
            return jsonify({"error": "Invalid signature"}), 403

        # Store in memory (or database)
        patient_authorizations[sender_address] = {
            "signature": signature,
            "message": data,
            "timestamp": time.time()
        }

        return jsonify({"message": "Authorization stored"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# @medical_log_bp.route('/api/records/<address>', methods=['GET'])
# @token_required
# def get_records(address):
#     try:
#         caller_address = request.headers.get('X-User-Address')

#         is_owner = caller_address.lower() == address.lower()
#         is_authorized = (
#             contract.functions.isDoctor(caller_address).call() or
#             contract.functions.isNurse(caller_address).call() or
#             contract.functions.isStaff(caller_address).call()
#         )

#         if not (is_owner or is_authorized):
#             return jsonify({'error': 'Unauthorized access'}), 403

#         records = contract.functions.getPatientRecords(address).call()

#         return jsonify({'blockchain_records': records}), 200

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@medical_log_bp.route('/api/records/<address>', methods=['GET'])
@token_required
def get_records(address):
    try:
        caller_address = Web3.to_checksum_address(request.headers.get('X-User-Address'))
        patient_address = Web3.to_checksum_address(address)

        is_owner = caller_address.lower() == patient_address.lower()
        is_authorized = (
            contract.functions.isDoctor(caller_address).call() or
            contract.functions.isNurse(caller_address).call() or
            contract.functions.isStaff(caller_address).call()
        )

        # Check if patient has signed authorization
        patient_auth = patient_authorizations.get(patient_address)
        valid_signature = False
        if patient_auth:
            message = json.dumps(patient_auth["message"])
            message_hash = Web3.keccak(text=message)
            recovered = w3.eth.account.recover_message(encode_defunct(message_hash), signature=patient_auth["signature"])
            valid_signature = (Web3.to_checksum_address(recovered) == patient_address)

        if not (is_owner or (is_authorized and valid_signature)):
            return jsonify({'error': 'Unauthorized access'}), 403

        records = contract.functions.getPatientRecords(address).call()

        return jsonify({'blockchain_records': records}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@medical_log_bp.route('/api/upload_to_ipfs', methods=['POST'])
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
    
@medical_log_bp.route('/api/save_record_to_ipfs', methods=['POST'])
def save_record_to_ipfs():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Missing JSON body'}), 400

        # Convert to bytes
        json_bytes = json.dumps(json_data).encode('utf-8')

        # Upload the JSON to IPFS
        ipfs_hash = ipfs_service.upload_file(json_bytes)

        return jsonify({
            'ipfsHash': ipfs_hash,
            'ipfs_url': f"https://ipfs.io/ipfs/{ipfs_hash}",
            'message': 'Metadata uploaded to IPFS'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
@medical_log_bp.route('/api/admin/add_role', methods=['POST'])
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
    medical_log_bp.run(debug=os.getenv('FLASK_DEBUG', 'False') == 'True')
