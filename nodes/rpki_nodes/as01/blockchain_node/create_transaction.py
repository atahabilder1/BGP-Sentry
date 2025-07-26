"""
Purpose:
    Creates a signed transaction from parsed BGP data and adds it to transaction_pool.json.
    The transaction includes transaction_id, sender_asn, ip_prefix, timestamp, trust_score,
    transaction_timestamp, previous_hash, signature, and an empty votes list.
    The public key is assumed to be pre-registered in shared_data/public_key_registry.json.

Calls:
    - transaction_pool.py: Calls add_transaction to add the transaction to the pool.
    - Internal: load_private_key, sign_transaction.

Location:
    - File: Located in blockchain_node directory (e.g., blockchain_node/create_transaction.py).
    - shared_data: Located four levels up from this script (../../../../shared_data),
      containing transaction_pool.json and public_key_registry.json.
    - private_key.pem: Located in blockchain_node directory (e.g., blockchain_node/private_key.pem).

Notes:
    - Uses a persistent private key from private_key.pem for signing (loaded from blockchain_node).
    - Assumes the corresponding public key is already in shared_data/public_key_registry.json.
    - Logs all operations to create_transaction.log and console for debugging.
    - Returns the transaction_id on success, None on failure.
"""

from pathlib import Path
import json
import uuid
from datetime import datetime, timezone
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

def load_private_key():
    """
    Load the private key from private_key.pem in the blockchain_node directory.
    Returns: private_key.
    """
    logger.info("Loading private key from private_key.pem")
    try:
        private_key_path = Path(__file__).parent /".."/ "private_key.pem"
        private_key_path = private_key_path.resolve()
        logger.debug("Private key path: %s", private_key_path)
        
        if not private_key_path.exists():
            logger.error("private_key.pem not found at %s", private_key_path)
            raise FileNotFoundError(f"private_key.pem not found at {private_key_path}")
        
        with open(private_key_path, 'rb') as f:
            pem = f.read()
        logger.debug("Private key PEM loaded")
        
        private_key = serialization.load_pem_private_key(
            pem,
            password=None,
            backend=default_backend()
        )
        logger.debug("Private key loaded successfully: private_key=%s", private_key)
        return private_key
    except Exception as e:
        logger.error("Failed to load private key: %s", str(e), exc_info=True)
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
    Returns: transaction_id if successful, None on failure.
    """
    logger.info("Starting create_transaction")
    
    if not parsed_data:
        logger.error("No parsed data provided")
        print("Error: No parsed data provided")
        return None

    logger.debug("Received parsed data: %s", json.dumps(parsed_data, indent=2))
    
    current_dir = Path(__file__).parent
    logger.debug("Current script directory: %s", current_dir)

    shared_data_dir = current_dir / ".." / ".." / ".." / ".."/ ".." / "shared_data"
    pool_path = shared_data_dir / "transaction_pool.json"

    pool_path = pool_path.resolve()
    logger.debug("Full path to transaction_pool.json: %s", pool_path)

    try:
        logger.info("Loading private key")
        private_key = load_private_key()

        transaction = {
            "transaction_id": str(uuid.uuid4()),
            "sender_asn": parsed_data["sender_asn"],
            "ip_prefix": parsed_data["ip_prefix"],
            "timestamp": parsed_data["timestamp"],
            "trust_score": parsed_data["trust_score"],
            "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
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