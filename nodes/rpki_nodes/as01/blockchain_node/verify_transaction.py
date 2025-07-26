"""
Purpose:
    Verifies transactions in transaction_pool.json or blockchain.json. For pool transactions,
    verifies the signature and adds a vote if valid (skips self-initiated transactions).
    For blockchain transactions, verifies the signature and block chain integrity.
    Uses public keys from shared_data/public_keys/<sender_asn>.pem.

Calls:
    - transaction_pool.py: Calls add_vote to record votes for pool transactions.
    - Internal: load_public_key, compute_transaction_hash, compute_block_hash,
      verify_transaction_signature.

Location:
    - File: Located in blockchain_node directory (e.g., blockchain_node/verify_transaction.py).
    - shared_data: Located three levels up from this script (../../../shared_data),
      containing transaction_pool.json, blockchain.json, and public_keys/<sender_asn>.pem.

Notes:
    - Skips verification of transactions where sender_asn matches node_asn.
    - Adds votes to transaction_pool.json for valid pool transactions.
    - Logs all operations to verify_transaction.log and console for debugging.
    - Returns verification results as a dictionary.
"""

from pathlib import Path
import json
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import logging
from transaction_pool import add_vote

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("verify_transaction.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_public_key(public_key_path):
    """
    Load the public key from a PEM file.
    Returns: public_key object.
    """
    logger.info("Loading public key from %s", public_key_path)
    try:
        logger.debug("Checking if public key file exists: %s", public_key_path.exists())
        with open(public_key_path, 'rb') as f:
            pem = f.read()
        logger.debug("Public key PEM: %s", pem.decode())
        public_key = serialization.load_pem_public_key(pem, backend=default_backend())
        logger.debug("Public key loaded successfully: %s", public_key)
        return public_key
    except Exception as e:
        logger.error("Failed to load public key: %s", str(e), exc_info=True)
        raise

def compute_transaction_hash(transaction):
    """
    Compute SHA-256 hash of a transaction (excluding signature and votes).
    Returns: hex-encoded hash.
    """
    logger.info("Computing hash for transaction: %s", 
                json.dumps({k: v for k, v in transaction.items() if k not in ["signature", "votes"]}, indent=2))
    try:
        data_to_hash = json.dumps({
            "transaction_id": transaction["transaction_id"],
            "sender_asn": transaction["sender_asn"],
            "ip_prefix": transaction["ip_prefix"],
            "timestamp": transaction["timestamp"],
            "trust_score": transaction["trust_score"],
            "transaction_timestamp": transaction["transaction_timestamp"],
            "previous_hash": transaction["previous_hash"]
        }, sort_keys=True).encode()
        logger.debug("Transaction data serialized for hashing: %s", data_to_hash.decode())
        transaction_hash = hashlib.sha256(data_to_hash).hexdigest()
        logger.debug("Computed transaction hash: %s", transaction_hash)
        return transaction_hash
    except Exception as e:
        logger.error("Failed to compute transaction hash: %s", str(e), exc_info=True)
        raise

def compute_block_hash(block):
    """
    Compute SHA-256 hash of a block (excluding block_hash).
    Returns: hex-encoded hash.
    """
    logger.info("Computing hash for block: %s", 
                json.dumps({k: v for k, v in block.items() if k != "block_hash"}, indent=2))
    try:
        data_to_hash = json.dumps({
            "block_id": block["block_id"],
            "block_timestamp": block["block_timestamp"],
            "transactions": block["transactions"],
            "previous_block_hash": block["previous_block_hash"]
        }, sort_keys=True).encode()
        logger.debug("Block data serialized for hashing: %s", data_to_hash.decode())
        block_hash = hashlib.sha256(data_to_hash).hexdigest()
        logger.debug("Computed block hash: %s", block_hash)
        return block_hash
    except Exception as e:
        logger.error("Failed to compute block hash: %s", str(e), exc_info=True)
        raise

def verify_transaction_signature(transaction, public_key):
    """
    Verify the signature of a transaction.
    Returns: True if valid, False otherwise.
    """
    logger.info("Verifying signature for transaction: %s", 
                json.dumps({k: v for k, v in transaction.items() if k != "signature"}, indent=2))
    try:
        data_to_verify = json.dumps({
            "transaction_id": transaction["transaction_id"],
            "sender_asn": transaction["sender_asn"],
            "ip_prefix": transaction["ip_prefix"],
            "timestamp": transaction["timestamp"],
            "trust_score": transaction["trust_score"],
            "transaction_timestamp": transaction["transaction_timestamp"],
            "previous_hash": transaction["previous_hash"]
        }, sort_keys=True).encode()
        logger.debug("Transaction data serialized for verification: %s", data_to_verify.decode())

        data_hash = hashlib.sha256(data_to_verify).digest()
        logger.debug("Transaction data hash: %s", data_hash.hex())

        signature = bytes.fromhex(transaction["signature"])
        logger.debug("Signature to verify: %s", signature.hex()[:64] + "...")
        public_key.verify(
            signature,
            data_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        logger.debug("Signature verification successful")
        return True
    except InvalidSignature:
        logger.warning("Signature verification failed: Invalid signature")
        return False
    except Exception as e:
        logger.error("Failed to verify signature: %s", str(e), exc_info=True)
        return False

def verify_pool_transaction(transaction_id, node_asn):
    """
    Verify a transaction in transaction_pool.json and add a vote if valid.
    Skips verification if sender_asn matches node_asn.
    Args:
        transaction_id: ID of the transaction to verify.
        node_asn: ASN of the verifying node.
    Returns: dict with verification results (signature_valid, vote_added).
    """
    logger.info("Starting verify_pool_transaction for transaction_id: %s, node_asn: %s", 
                transaction_id, node_asn)
    
    current_dir = Path(__file__).parent
    logger.debug("Current script directory: %s", current_dir)

    shared_data_dir = current_dir / ".." / ".." / ".." / "shared_data"
    pool_path = shared_data_dir / "transaction_pool.json"
    pool_path = pool_path.resolve()
    logger.debug("Full path to transaction_pool.json: %s", pool_path)

    try:
        if not pool_path.exists():
            logger.error("transaction_pool.json not found at %s", pool_path)
            print(f"Error: transaction_pool.json not found at {pool_path}")
            return {"signature_valid": False, "vote_added": False, "error": "transaction_pool.json not found"}

        logger.info("Reading transaction_pool.json")
        with open(pool_path, 'r') as file:
            pool_data = json.load(file)
        logger.debug("transaction_pool.json content: %s", json.dumps(pool_data, indent=2))

        if not isinstance(pool_data.get("transactions"), list):
            logger.error("'transactions' key in transaction_pool.json is not a list")
            print("Error: 'transactions' key in transaction_pool.json is not a list")
            return {"signature_valid": False, "vote_added": False, "error": "Invalid transaction_pool.json structure"}

        target_transaction = None
        for tx in pool_data["transactions"]:
            if tx.get("transaction_id") == transaction_id:
                target_transaction = tx
                break
        if not target_transaction:
            logger.error("Transaction %s not found in transaction_pool.json", transaction_id)
            print(f"Error: Transaction {transaction_id} not found")
            return {"signature_valid": False, "vote_added": False, "error": "Transaction not found"}

        logger.debug("Found transaction: %s", json.dumps(target_transaction, indent=2))

        if target_transaction["sender_asn"] == node_asn:
            logger.warning("Skipping verification: transaction %s initiated by this node (ASN %s)", 
                           transaction_id, node_asn)
            print(f"Error: Cannot verify transaction {transaction_id} initiated by this node (ASN {node_asn})")
            return {"signature_valid": False, "vote_added": False, 
                    "error": "Self-verification not allowed"}

        public_key_path = shared_data_dir / "public_keys" / f"{target_transaction['sender_asn']}.pem"
        public_key_path = public_key_path.resolve()
        logger.debug("Public key path for ASN %s: %s", target_transaction["sender_asn"], public_key_path)

        if not public_key_path.exists():
            logger.error("Public key for ASN %s not found at %s", 
                         target_transaction["sender_asn"], public_key_path)
            print(f"Error: Public key for ASN {target_transaction['sender_asn']} not found")
            return {"signature_valid": False, "vote_added": False, "error": "Public key not found"}

        logger.info("Loading public key")
        public_key = load_public_key(public_key_path)

        logger.info("Verifying transaction signature")
        signature_valid = verify_transaction_signature(target_transaction, public_key)
        if not signature_valid:
            logger.warning("Signature verification failed for transaction %s", transaction_id)
            print(f"Error: Signature verification failed for transaction {transaction_id}")
            return {"signature_valid": False, "vote_added": False, "error": "Invalid signature"}

        logger.info("Adding vote from node ASN %s", node_asn)
        vote_added = add_vote(transaction_id, node_asn)
        if not vote_added:
            logger.warning("Failed to add vote for transaction %s", transaction_id)
            print(f"Error: Failed to add vote for transaction {transaction_id}")

        logger.info("Pool verification complete: signature_valid=%s, vote_added=%s", 
                    signature_valid, vote_added)
        print(f"Verification for transaction {transaction_id} in pool:")
        print(f"  Signature Valid: {signature_valid}")
        print(f"  Vote Added: {vote_added}")

        return {
            "signature_valid": signature_valid,
            "vote_added": vote_added,
            "error": None
        }

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return {"signature_valid": False, "vote_added": False, "error": str(e)}

def verify_blockchain_transaction(transaction_id, node_asn):
    """
    Verify a transaction’s signature and block chain integrity in blockchain.json.
    Skips verification if sender_asn matches node_asn.
    Args:
        transaction_id: ID of the transaction to verify.
        node_asn: ASN of the verifying node.
    Returns: dict with verification results (signature_valid, chain_valid, block_id).
    """
    logger.info("Starting verify_blockchain_transaction for transaction_id: %s, node_asn: %s", 
                transaction_id, node_asn)
    
    current_dir = Path(__file__).parent
    logger.debug("Current script directory: %s", current_dir)

    shared_data_dir = current_dir / ".." / ".." / ".." / "shared_data"
    blockchain_path = shared_data_dir / "blockchain.json"
    blockchain_path = blockchain_path.resolve()
    logger.debug("Full path to blockchain.json: %s", blockchain_path)

    try:
        logger.debug("Checking if blockchain.json exists: %s", blockchain_path.exists())
        if not blockchain_path.exists():
            logger.error("blockchain.json not found at %s", blockchain_path)
            print(f"Error: blockchain.json not found at {blockchain_path}")
            return {"signature_valid": False, "chain_valid": False, "block_id": None, 
                    "error": "blockchain.json not found"}

        logger.info("Reading blockchain.json")
        with open(blockchain_path, 'r') as file:
            blockchain_data = json.load(file)
        logger.debug("blockchain.json content: %s", json.dumps(blockchain_data, indent=2))

        if not isinstance(blockchain_data.get("blocks"), list):
            logger.error("'blocks' key in blockchain.json is not a list")
            print("Error: 'blocks' key in blockchain.json is not a list")
            return {"signature_valid": False, "chain_valid": False, "block_id": None, 
                    "error": "Invalid blockchain.json structure"}

        blocks = blockchain_data["blocks"]
        logger.debug("Number of blocks: %d", len(blocks))
        if not blocks:
            logger.error("No blocks found in blockchain.json")
            print("Error: No blocks found in blockchain.json")
            return {"signature_valid": False, "chain_valid": False, "block_id": None, 
                    "error": "No blocks found"}

        target_transaction = None
        target_block_id = None
        target_block_index = None
        for i, block in enumerate(blocks):
            for tx in block.get("transactions", []):
                if tx.get("transaction_id") == transaction_id:
                    target_transaction = tx
                    target_block_id = block["block_id"]
                    target_block_index = i
                    break
            if target_transaction:
                break
        if not target_transaction:
            logger.error("Transaction %s not found in blockchain.json", transaction_id)
            print(f"Error: Transaction {transaction_id} not found")
            return {"signature_valid": False, "chain_valid": False, "block_id": None, 
                    "error": "Transaction not found"}

        logger.debug("Found transaction in block %s at index %d: %s", 
                     target_block_id, target_block_index, json.dumps(target_transaction, indent=2))

        if target_transaction["sender_asn"] == node_asn:
            logger.warning("Skipping verification: transaction %s initiated by this node (ASN %s)", 
                           transaction_id, node_asn)
            print(f"Error: Cannot verify transaction {transaction_id} initiated by this node (ASN {node_asn})")
            return {"signature_valid": False, "chain_valid": False, "block_id": target_block_id, 
                    "error": "Self-verification not allowed"}

        public_key_path = shared_data_dir / "public_keys" / f"{target_transaction['sender_asn']}.pem"
        public_key_path = public_key_path.resolve()
        logger.debug("Public key path for ASN %s: %s", target_transaction["sender_asn"], public_key_path)

        if not public_key_path.exists():
            logger.error("Public key for ASN %s not found at %s", 
                         target_transaction["sender_asn"], public_key_path)
            print(f"Error: Public key for ASN {target_transaction['sender_asn']} not found")
            return {"signature_valid": False, "chain_valid": False, "block_id": target_block_id, 
                    "error": "Public key not found"}

        logger.info("Loading public key")
        public_key = load_public_key(public_key_path)

        logger.info("Verifying transaction signature")
        signature_valid = verify_transaction_signature(target_transaction, public_key)
        if not signature_valid:
            print(f"Error: Signature verification failed for transaction {transaction_id}")

        logger.info("Verifying block chain integrity")
        chain_valid = True
        if target_block_index > 0:
            expected_previous_hash = compute_block_hash(blocks[target_block_index - 1])
            logger.debug("Expected previous block hash: %s", expected_previous_hash)
            if blocks[target_block_index]["previous_block_hash"] != expected_previous_hash:
                logger.warning("Chain integrity check failed: previous_block_hash mismatch in block %s", 
                               target_block_id)
                print(f"Error: Chain integrity check failed for block {target_block_id}")
                chain_valid = False
        elif blocks[target_block_index]["previous_block_hash"] != "0" * 64:
            logger.warning("Chain integrity check failed: first block has non-zero previous_block_hash")
            print(f"Error: Chain integrity check failed for block {target_block_id}")
            chain_valid = False

        logger.info("Verifying block hash")
        computed_block_hash = compute_block_hash(blocks[target_block_index])
        logger.debug("Computed block hash: %s, stored hash: %s", 
                     computed_block_hash, blocks[target_block_index]["block_hash"])
        if computed_block_hash != blocks[target_block_index]["block_hash"]:
            logger.warning("Block hash verification failed for block %s", target_block_id)
            print(f"Error: Block hash verification failed for block {target_block_id}")
            chain_valid = False

        logger.info("Blockchain verification complete: signature_valid=%s, chain_valid=%s, block_id=%s", 
                    signature_valid, chain_valid, target_block_id)
        print(f"Verification for transaction {transaction_id} in block {target_block_id}:")
        print(f"  Signature Valid: {signature_valid}")
        print(f"  Chain Valid: {chain_valid}")

        return {
            "signature_valid": signature_valid,
            "chain_valid": chain_valid,
            "block_id": target_block_id,
            "error": None
        }

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return {"signature_valid": False, "chain_valid": False, "block_id": None, "error": str(e)}

if __name__ == "__main__":
    logger.info("Starting verify_transaction.py")
    transaction_id = input("Enter transaction ID to verify: ")
    node_asn = input("Enter this node's ASN: ")
    try:
        node_asn = int(node_asn)
        # Try verifying in pool first
        result = verify_pool_transaction(transaction_id, node_asn)
        if result["error"] == "Transaction not found":
            # If not in pool, try blockchain
            result = verify_blockchain_transaction(transaction_id, node_asn)
        logger.debug("Verification result: %s", json.dumps(result, indent=2))
    except ValueError:
        logger.error("Invalid node ASN: %s", node_asn)
        print("Error: Node ASN must be a number")
    logger.info("Finished verify_transaction.py")