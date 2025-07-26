"""
Purpose:
    Commits transactions with ≥3 votes from transaction_pool.json to a block in blockchain.json.
    Uses a file-based lock (blockchain_lock.json) to prevent race conditions and removes
    committed transactions from the pool.

Calls:
    - transaction_pool.py: Calls get_verified_transactions to retrieve transactions with ≥3 votes
      and remove_transactions to delete committed transactions.

Location:
    - File: Located in blockchain_node directory (e.g., blockchain_node/commit_to_blockchain.py).
    - shared_data: Located three levels up from this script (../../../shared_data),
      containing blockchain.json and blockchain_lock.json.

Notes:
    - Acquires a lock to ensure only one node writes to blockchain.json at a time.
    - Removes committed transactions from the pool to prevent reuse.
    - Logs all operations to commit_to_blockchain.log and console for debugging.
    - Returns block_id on success, None on failure.
"""

from pathlib import Path
import json
import uuid
from datetime import datetime
import hashlib
import time
import logging
from transaction_pool import get_verified_transactions, remove_transactions

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("commit_to_blockchain.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def acquire_lock(lock_path, node_asn, timeout=60):
    """
    Attempt to acquire a file-based lock for block writing.
    Args:
        lock_path: Path to the lock file.
        node_asn: ASN of the node attempting to acquire the lock.
        timeout: Maximum time to wait for the lock (seconds).
    Returns: True if lock acquired, False otherwise.
    """
    logger.info("Attempting to acquire lock at %s for node ASN %s", lock_path, node_asn)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug("Checking if lock file exists: %s", lock_path.exists())
            if not lock_path.exists():
                lock_data = {
                    "node_asn": node_asn,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                logger.debug("Creating lock file with data: %s", json.dumps(lock_data, indent=2))
                with open(lock_path, 'w') as file:
                    json.dump(lock_data, file, indent=4)
                logger.debug("Lock acquired by node ASN %s", node_asn)
                return True
            else:
                with open(lock_path, 'r') as file:
                    lock_data = json.load(file)
                logger.debug("Lock file content: %s", json.dumps(lock_data, indent=2))
                lock_time = datetime.fromisoformat(lock_data["timestamp"].rstrip("Z"))
                if (datetime.utcnow() - lock_time).total_seconds() > timeout:
                    logger.warning("Lock expired, overwriting with new lock for node ASN %s", node_asn)
                    lock_data = {
                        "node_asn": node_asn,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    with open(lock_path, 'w') as file:
                        json.dump(lock_data, file, indent=4)
                    logger.debug("Lock acquired by node ASN %s after expiration", node_asn)
                    return True
            time.sleep(1)
        except Exception as e:
            logger.error("Error acquiring lock: %s", str(e), exc_info=True)
            time.sleep(1)
    
    logger.error("Failed to acquire lock within %d seconds", timeout)
    return False

def release_lock(lock_path):
    """
    Release the file-based lock.
    Args:
        lock_path: Path to the lock file.
    Returns: True if released, False otherwise.
    """
    logger.info("Releasing lock at %s", lock_path)
    try:
        logger.debug("Checking if lock file exists: %s", lock_path.exists())
        if lock_path.exists():
            lock_path.unlink()
            logger.debug("Lock released successfully")
            return True
        logger.warning("Lock file not found at %s", lock_path)
        return False
    except Exception as e:
        logger.error("Error releasing lock: %s", str(e), exc_info=True)
        return False

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

def commit_to_blockchain(node_asn):
    """
    Create a block from verified transactions (≥3 votes) and append it to blockchain.json.
    Removes committed transactions from the pool.
    Args:
        node_asn: ASN of the node attempting to commit the block.
    Returns: block_id if successful, None otherwise.
    """
    logger.info("Starting commit_to_blockchain for node ASN %s", node_asn)
    
    current_dir = Path(__file__).parent
    logger.debug("Current script directory: %s", current_dir)

    shared_data_dir = current_dir / ".." / ".." / ".." / "shared_data"
    blockchain_path = shared_data_dir / "blockchain.json"
    lock_path = shared_data_dir / "blockchain_lock.json"
    blockchain_path = blockchain_path.resolve()
    lock_path = lock_path.resolve()
    logger.debug("Full path to blockchain.json: %s", blockchain_path)
    logger.debug("Full path to blockchain_lock.json: %s", lock_path)

    try:
        logger.info("Acquiring lock")
        if not acquire_lock(lock_path, node_asn):
            logger.error("Failed to acquire lock for block writing")
            print("Error: Failed to acquire lock for block writing")
            return None

        try:
            logger.info("Retrieving verified transactions")
            transactions = get_verified_transactions(min_votes=3)
            logger.debug("Retrieved %d verified transactions: %s", 
                         len(transactions), [tx["transaction_id"] for tx in transactions])
            if not transactions:
                logger.warning("No transactions with ≥3 votes to commit")
                print("Error: No transactions with ≥3 votes to commit")
                return None

            blockchain_data = {"blocks": []}
            previous_block_hash = "0" * 64
            logger.info("Checking blockchain.json")
            logger.debug("Checking if blockchain.json exists: %s", blockchain_path.exists())
            if blockchain_path.exists():
                logger.debug("blockchain.json exists at %s", blockchain_path)
                try:
                    with open(blockchain_path, 'r') as file:
                        blockchain_data = json.load(file)
                        logger.debug("blockchain.json content: %s", json.dumps(blockchain_data, indent=2))
                        if not isinstance(blockchain_data.get("blocks"), list):
                            logger.warning("'blocks' key in blockchain.json is not a list. Initializing new list.")
                            print("Error: 'blocks' key in blockchain.json is not a list. Initializing new list.")
                            blockchain_data["blocks"] = []
                        elif blockchain_data["blocks"]:
                            previous_block_hash = blockchain_data["blocks"][-1]["block_hash"]
                            logger.debug("Previous block hash: %s", previous_block_hash)
                except json.JSONDecodeError as e:
                    logger.error("Invalid JSON in blockchain.json: %s, document: %s", str(e), e.doc)
                    print("Error: Invalid JSON in blockchain.json. Initializing new file.")
                    blockchain_data["blocks"] = []
            else:
                logger.info("blockchain.json not found at %s. Creating new file.", blockchain_path)
                print(f"blockchain.json not found at {blockchain_path}. Creating new file.")

            block = {
                "block_id": str(uuid.uuid4()),
                "block_timestamp": datetime.utcnow().isoformat() + "Z",
                "transactions": transactions,
                "previous_block_hash": previous_block_hash
            }
            logger.debug("Prepared block: %s", 
                         json.dumps({k: v for k, v in block.items() if k != "block_hash"}, indent=2))

            logger.info("Computing block hash")
            block["block_hash"] = compute_block_hash(block)
            logger.info("Block hash computed successfully")

            logger.info("Appending block to blockchain_data")
            blockchain_data["blocks"].append(block)

            logger.info("Writing to blockchain.json")
            try:
                with open(blockchain_path, 'w') as file:
                    json.dump(blockchain_data, file, indent=4)
                logger.info("Block %s written to blockchain.json with %d transactions", 
                            block["block_id"], len(transactions))
                print(f"Block {block['block_id']} written to blockchain.json with {len(transactions)} transactions")
            except Exception as e:
                logger.error("Failed to write to blockchain.json: %s", str(e), exc_info=True)
                print(f"Error writing to blockchain.json: {str(e)}")
                return None

            transaction_ids = [tx["transaction_id"] for tx in transactions]
            logger.info("Removing %d committed transactions from pool: %s", 
                        len(transaction_ids), transaction_ids)
            if not remove_transactions(transaction_ids):
                logger.error("Failed to remove committed transactions from pool")
                print("Error: Failed to remove committed transactions from pool")
                return None

            return block["block_id"]

        finally:
            logger.info("Releasing lock")
            if not release_lock(lock_path):
                logger.error("Failed to release lock")

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        release_lock(lock_path)
        return None

if __name__ == "__main__":
    logger.info("Starting commit_to_blockchain.py")
    node_asn = input("Enter this node's ASN: ")
    try:
        node_asn = int(node_asn)
        block_id = commit_to_blockchain(node_asn)
        if block_id:
            logger.debug("Committed block_id: %s", block_id)
        else:
            logger.error("Block commitment failed")
    except ValueError:
        logger.error("Invalid node ASN: %s", node_asn)
        print("Error: Node ASN must be a number")
    logger.info("Finished commit_to_blockchain.py")