"""
Purpose:
    Manages the transaction pool in transaction_pool.json, allowing transactions to be added,
    votes to be recorded, verified transactions (≥3 votes) to be retrieved, and committed
    transactions to be removed. Ensures transactions are queued for peer verification before
    block inclusion.

Calls:
    - None (standalone module, called by create_transaction.py, commit_to_blockchain.py,
      verify_transaction.py).

Location:
    - File: Located in blockchain_node directory (e.g., blockchain_node/transaction_pool.py).
    - shared_data: Located four levels up from this script (../../../../shared_data),
      containing transaction_pool.json.

Notes:
    - Transactions include a votes list for peer verification.
    - Logs all operations to transaction_pool.log and console for debugging.
    - Handles file access with error checking to avoid race conditions.
"""

from pathlib import Path
import json
import logging
from datetime import datetime, timezone
import uuid

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("transaction_pool.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def add_transaction(transaction):
    """
    Add a transaction to transaction_pool.json.
    Args:
        transaction: dict with transaction data.
    Returns: True if successful, False otherwise.
    """
    logger.info("Starting add_transaction for transaction_id: %s", transaction.get("transaction_id", "unknown"))
    
    current_dir = Path(__file__).parent
    logger.debug("Current script directory: %s", current_dir)

    shared_data_dir = current_dir / ".." / ".." / ".." / ".." / "shared_data"
    pool_path = shared_data_dir / "transaction_pool.json"
    pool_path = pool_path.resolve()
    logger.debug("Full path to transaction_pool.json: %s", pool_path)

    try:
        pool_data = {"transactions": []}
        logger.info("Checking transaction_pool.json")
        logger.debug("Checking if transaction_pool.json exists: %s", pool_path.exists())
        if pool_path.exists():
            logger.debug("transaction_pool.json exists at %s", pool_path)
            try:
                with open(pool_path, 'r') as file:
                    pool_data = json.load(file)
                    logger.debug("transaction_pool.json content: %s", json.dumps(pool_data, indent=2))
                    if not isinstance(pool_data.get("transactions"), list):
                        logger.warning("'transactions' key in transaction_pool.json is not a list. Initializing new list.")
                        pool_data["transactions"] = []
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in transaction_pool.json: %s, document: %s", str(e), e.doc)
                print("Error: Invalid JSON in transaction_pool.json. Initializing new file.")
                pool_data["transactions"] = []
        else:
            logger.info("transaction_pool.json not found at %s. Creating new file.", pool_path)
            print(f"transaction_pool.json not found at {pool_path}. Creating new file.")

        logger.info("Appending transaction to transaction_pool")
        pool_data["transactions"].append(transaction)
        logger.debug("Transaction added: %s", json.dumps(transaction, indent=2))

        logger.info("Writing to transaction_pool.json")
        try:
            pool_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pool_path, 'w') as file:
                json.dump(pool_data, file, indent=4)
            logger.info("Transaction %s added to transaction_pool.json", transaction.get("transaction_id", "unknown"))
            print(f"Transaction {transaction.get('transaction_id', 'unknown')} added to transaction_pool.json")
            return True
        except Exception as e:
            logger.error("Failed to write to transaction_pool.json: %s", str(e), exc_info=True)
            print(f"Error writing to transaction_pool.json: {str(e)}")
            return False

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return False

def add_vote(transaction_id, voter_asn):
    """
    Add a vote for a transaction by a peer node.
    Args:
        transaction_id: ID of the transaction to vote for.
        voter_asn: ASN of the voting node.
    Returns: True if vote added, False otherwise.
    """
    logger.info("Starting add_vote for transaction_id: %s, voter_asn: %s", transaction_id, voter_asn)
    
    current_dir = Path(__file__).parent
    shared_data_dir = current_dir / ".." / ".." / ".." / ".." / "shared_data"
    pool_path = shared_data_dir / "transaction_pool.json"
    pool_path = pool_path.resolve()
    logger.debug("Full path to transaction_pool.json: %s", pool_path)

    try:
        if not pool_path.exists():
            logger.error("transaction_pool.json not found at %s", pool_path)
            print(f"Error: transaction_pool.json not found at {pool_path}")
            return False

        logger.info("Reading transaction_pool.json")
        with open(pool_path, 'r') as file:
            pool_data = json.load(file)
        logger.debug("transaction_pool.json content: %s", json.dumps(pool_data, indent=2))

        if not isinstance(pool_data.get("transactions"), list):
            logger.error("'transactions' key in transaction_pool.json is not a list")
            print("Error: 'transactions' key in transaction_pool.json is not a list")
            return False

        transaction_found = False
        for tx in pool_data["transactions"]:
            if tx.get("transaction_id") == transaction_id:
                if "votes" not in tx:
                    tx["votes"] = []
                if voter_asn not in tx["votes"]:
                    tx["votes"].append(voter_asn)
                    logger.debug("Added vote from ASN %s to transaction %s: votes=%s", 
                                 voter_asn, transaction_id, tx["votes"])
                    transaction_found = True
                else:
                    logger.warning("ASN %s already voted for transaction %s", voter_asn, transaction_id)
                    print(f"Warning: ASN {voter_asn} already voted for transaction {transaction_id}")
                    return False
                break

        if not transaction_found:
            logger.error("Transaction %s not found in transaction_pool.json", transaction_id)
            print(f"Error: Transaction {transaction_id} not found")
            return False

        logger.info("Writing updated transaction_pool.json")
        try:
            with open(pool_path, 'w') as file:
                json.dump(pool_data, file, indent=4)
            logger.info("Vote from ASN %s added for transaction %s, total votes: %d", 
                        voter_asn, transaction_id, len(tx["votes"]))
            print(f"Vote from ASN {voter_asn} added for transaction {transaction_id}")
            return True
        except Exception as e:
            logger.error("Failed to write to transaction_pool.json: %s", str(e), exc_info=True)
            print(f"Error writing to transaction_pool.json: {str(e)}")
            return False

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return False

def get_verified_transactions(min_votes=3):
    """
    Retrieve transactions with at least min_votes votes from transaction_pool.json.
    Returns: list of transactions.
    """
    logger.info("Starting get_verified_transactions with min_votes: %d", min_votes)
    
    current_dir = Path(__file__).parent
    shared_data_dir = current_dir / ".." / ".." / ".." / ".." / "shared_data"
    pool_path = shared_data_dir / "transaction_pool.json"
    pool_path = pool_path.resolve()
    logger.debug("Full path to transaction_pool.json: %s", pool_path)

    try:
        pool_data = {"transactions": []}
        logger.info("Checking transaction_pool.json")
        logger.debug("Checking if transaction_pool.json exists: %s", pool_path.exists())
        if pool_path.exists():
            logger.debug("transaction_pool.json exists at %s", pool_path)
            try:
                with open(pool_path, 'r') as file:
                    pool_data = json.load(file)
                    logger.debug("transaction_pool.json content: %s", json.dumps(pool_data, indent=2))
                    if not isinstance(pool_data.get("transactions"), list):
                        logger.warning("'transactions' key in transaction_pool.json is not a list. Returning empty list.")
                        pool_data["transactions"] = []
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in transaction_pool.json: %s, document: %s", str(e), e.doc)
                print("Error: Invalid JSON in transaction_pool.json. Returning empty list.")
                pool_data["transactions"] = []
        else:
            logger.info("transaction_pool.json not found at %s. Returning empty list.", pool_path)
            print(f"transaction_pool.json not found at {pool_path}. Returning empty list.")

        verified_transactions = [
            tx for tx in pool_data["transactions"]
            if len(tx.get("votes", [])) >= min_votes
        ]
        logger.debug("Retrieved %d verified transactions with >= %d votes: %s", 
                     len(verified_transactions), min_votes, 
                     [tx["transaction_id"] for tx in verified_transactions])

        return verified_transactions

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return []

def remove_transactions(transaction_ids):
    """
    Remove specified transactions from transaction_pool.json.
    Args:
        transaction_ids: list of transaction IDs to remove.
    Returns: True if successful, False otherwise.
    """
    logger.info("Starting remove_transactions for %d transaction IDs: %s", 
                len(transaction_ids), transaction_ids)
    
    current_dir = Path(__file__).parent
    shared_data_dir = current_dir / ".." / ".." / ".." / ".." / "shared_data"
    pool_path = shared_data_dir / "transaction_pool.json"
    pool_path = pool_path.resolve()
    logger.debug("Full path to transaction_pool.json: %s", pool_path)

    try:
        if not pool_path.exists():
            logger.error("transaction_pool.json not found at %s", pool_path)
            print(f"Error: transaction_pool.json not found at {pool_path}")
            return False

        logger.info("Reading transaction_pool.json")
        with open(pool_path, 'r') as file:
            pool_data = json.load(file)
        logger.debug("transaction_pool.json content: %s", json.dumps(pool_data, indent=2))

        if not isinstance(pool_data.get("transactions"), list):
            logger.error("'transactions' key in transaction_pool.json is not a list")
            print("Error: 'transactions' key in transaction_pool.json is not a list")
            return False

        initial_count = len(pool_data["transactions"])
        pool_data["transactions"] = [
            tx for tx in pool_data["transactions"]
            if tx.get("transaction_id") not in transaction_ids
        ]
        removed_count = initial_count - len(pool_data["transactions"])
        logger.debug("Removed %d transactions from pool, remaining: %d", 
                     removed_count, len(pool_data["transactions"]))

        logger.info("Writing updated transaction_pool.json")
        try:
            with open(pool_path, 'w') as file:
                json.dump(pool_data, file, indent=4)
            logger.info("Removed %d transactions from transaction_pool.json", removed_count)
            print(f"Removed {removed_count} transactions from transaction_pool.json")
            return True
        except Exception as e:
            logger.error("Failed to write to transaction_pool.json: %s", str(e), exc_info=True)
            print(f"Error writing to transaction_pool.json: {str(e)}")
            return False

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting transaction_pool.py")
    dummy_transaction = {
        "transaction_id": str(uuid.uuid4()),
        "sender_asn": 2,
        "ip_prefix": "203.0.113.0/24",
        "timestamp": "2025-07-24T14:00:00Z",
        "trust_score": "N/A",
        "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
        "previous_hash": "0" * 64,
        "signature": "dummy_signature",
        "votes": []
    }
    add_transaction(dummy_transaction)
    add_vote(dummy_transaction["transaction_id"], 3)
    transactions = get_verified_transactions(min_votes=1)
    logger.info("Retrieved transactions: %s", [tx["transaction_id"] for tx in transactions])
    remove_transactions([dummy_transaction["transaction_id"]])
    logger.info("Finished transaction_pool.py")