"""
Purpose:
    Creates a signed transaction from parsed BGP data, adds it to transaction_pool.json,
    and saves the public key to shared_data/public_keys/<sender_asn>.pem for verification.
    The transaction includes transaction_id, sender_asn, ip_prefix, timestamp, trust_score,
    transaction_timestamp, previous_hash, signature, and an empty votes list.

Calls:
    - transaction_pool.py: Calls add_transaction to add the transaction to the pool.
    - Internal: generate_key_pair, save_public_key, sign_transaction.

Location:
    - File: Located in blockchain_node directory (e.g., blockchain_node/create_transaction.py).
    - shared_data: Located three levels up from this script (../../../shared_data),
      containing transaction_pool.json and public_keys/<sender_asn>.pem.

Notes:
    - Generates a new RSA key pair for demo purposes (in practice, use persistent keys).
    - Logs all operations to create_transaction.log and console for debugging.
    - Returns the transaction_id on success, None on failure.
"""

from pathlib import Path
import json
import uuid
from datetime import datetime
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging
from transaction_pool import add_transaction

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("create_transaction.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_key_pair():
    """
    Generate an RSA private-public key pair for signing (for demo purposes).
    Returns: private_key, public_key.
    """
    logger.info("Generating RSA key pair")
    try:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        logger.debug("RSA key pair generated successfully: private_key=%s, public_key=%s", 
                     private_key, public_key)
        return private_key, public_key
    except Exception as e:
        logger.error("Failed to generate key pair: %s", str(e), exc_info=True)
        raise

def save_public_key(public_key, public_key_path):
    """
    Save the public key to a PEM file.
    """
    logger.info("Saving public key to %s", public_key_path)
    try:
        public_key_path.parent.mkdir(parents=True, exist_ok=True)
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        logger.debug("Public key PEM: %s", pem.decode())
        with open(public_key_path, 'wb') as f:
            f.write(pem)
        logger.debug("Public key saved successfully")
    except Exception as e:
        logger.error("Failed to save public key: %s", str(e), exc_info=True)
        raise

def sign_transaction(transaction_data, private_key):
    """
    Sign the transaction data using the private key.
    Returns: hex-encoded signature.
    """
    logger.info("Preparing to sign transaction: %s", json.dumps(transaction_data, indent=2))
    try:
        data_to_sign = json.dumps({
            "transaction_id": transaction_data["transaction_id"],
            "sender_asn": transaction_data["sender_asn"],
            "ip_prefix": transaction_data["ip_prefix"],
            "timestamp": transaction_data["timestamp"],
            "trust_score": transaction_data["trust_score"],
            "transaction_timestamp": transaction_data["transaction_timestamp"],
            "previous_hash": transaction_data["previous_hash"]
        }, sort_keys=True).encode()
        logger.debug("Transaction data serialized for signing: %s", data_to_sign.decode())

        data_hash = hashlib.sha256(data_to_sign).digest()
        logger.debug("Transaction data hash: %s", data_hash.hex())

        signature = private_key.sign(
            data_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        signature_hex = signature.hex()
        logger.debug("Transaction signed, signature length: %d bytes, signature: %s", 
                     len(signature_hex) // 2, signature_hex[:64] + "...")
        return signature_hex
    except Exception as e:
        logger.error("Failed to sign transaction: %s", str(e), exc_info=True)
        raise

def create_transaction(parsed_data):
    """
    Creates a signed transaction from parsed BGP data and writes it to transaction_pool.json.
    Args:
        parsed_data: dict with sender_asn, ip_prefix, timestamp, trust_score, prefix_length.
    Returns: transaction_id if successful, None otherwise.
    """
    logger.info("Starting create_transaction")
    
    if not parsed_data:
        logger.error("No parsed data provided")
        print("Error: No parsed data provided")
        return None

    logger.debug("Received parsed data: %s", json.dumps(parsed_data, indent=2))
    
    current_dir = Path(__file__).parent
    logger.debug("Current script directory: %s", current_dir)

    shared_data_dir = current_dir / ".." / ".." / ".." / "shared_data"
    pool_path = shared_data_dir / "transaction_pool.json"
    public_key_path = shared_data_dir / "public_keys" / f"{parsed_data['sender_asn']}.pem"

    pool_path = pool_path.resolve()
    public_key_path = public_key_path.resolve()
    logger.debug("Full path to transaction_pool.json: %s", pool_path)
    logger.debug("Full path to public_key.pem: %s", public_key_path)

    try:
        logger.info("Generating key pair for signing")
        private_key, public_key = generate_key_pair()
        
        logger.info("Saving public key")
        save_public_key(public_key, public_key_path)

        transaction = {
            "transaction_id": str(uuid.uuid4()),
            "sender_asn": parsed_data["sender_asn"],
            "ip_prefix": parsed_data["ip_prefix"],
            "timestamp": parsed_data["timestamp"],
            "trust_score": parsed_data["trust_score"],
            "transaction_timestamp": datetime.utcnow().isoformat() + "Z",
            "previous_hash": "0" * 64,
            "votes": []
        }
        logger.debug("Prepared transaction: %s", json.dumps(transaction, indent=2))

        logger.info("Signing transaction")
        transaction["signature"] = sign_transaction(transaction, private_key)
        logger.info("Transaction signed successfully")

        logger.info("Adding transaction to pool")
        if not add_transaction(transaction):
            logger.error("Failed to add transaction to pool")
            return None
        logger.info("Transaction %s added to transaction_pool.json", transaction["transaction_id"])
        return transaction["transaction_id"]

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return None

if __name__ == "__main__":
    logger.info("Starting create_transaction.py")
    dummy_data = {
        "sender_asn": 2,
        "ip_prefix": "203.0.113.0/24",
        "timestamp": "2025-07-24T14:00:00Z",
        "trust_score": "N/A",
        "prefix_length": 24
    }
    transaction_id = create_transaction(dummy_data)
    logger.info("Finished create_transaction.py")
    if transaction_id:
        logger.debug("Created transaction_id: %s", transaction_id)
    else:
        logger.error("Transaction creation failed")