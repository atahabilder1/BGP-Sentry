"""
Purpose:
    Orchestrates the RPKI blockchain workflow for a node: parses BGP announcements,
    creates transactions, allows peer verification (≥3 votes), commits verified transactions
    to the blockchain, and verifies transactions in the blockchain (skipping self-initiated ones).
    Uses node_asn to identify the node and prevent self-verification.

Calls:
    - parse_bgp.py: Calls parse_bgp_announcement to parse BGP data.
    - create_transaction.py: Calls create_transaction to generate transactions.
    - transaction_pool.py: Calls get_verified_transactions to retrieve transactions.
    - commit_to_blockchain.py: Calls commit_to_blockchain to create blocks.
    - verify_transaction.py: Calls verify_pool_transaction and verify_blockchain_transaction.

Location:
    - File: Located in blockchain_node directory (e.g., blockchain_node/main.py).
    - shared_data: Located three levels up from this script (../../../shared_data),
      containing bgpd.json, trust_state.json, transaction_pool.json, blockchain.json,
      blockchain_lock.json, and public_keys/<sender_asn>.pem.

Notes:
    - Requires node_asn to identify the node.
    - Simulates peer verification by prompting for peer ASNs (in practice, peers run verify_transaction.py).
    - Logs all operations to main.log and console for debugging.
    - Ensures transactions have ≥3 votes before committing.
"""

import logging
from parse_bgp import parse_bgp_announcement
from create_transaction import create_transaction
from transaction_pool import get_verified_transactions, add_vote
from commit_to_blockchain import commit_to_blockchain
from nodes.rpki_nodes.shared_blockchain_stack.block_proposer.verify_transaction import verify_pool_transaction, verify_blockchain_transaction

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("main.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main(node_asn):
    """
    Orchestrates the blockchain workflow for an RPKI node.
    Args:
        node_asn: ASN of the node (to prevent self-verification).
    """
    logger.info("Starting main.py for node ASN: %s", node_asn)
    
    # Parse BGP announcement
    logger.info("Parsing BGP announcement")
    parsed_data = parse_bgp_announcement()
    if not parsed_data:
        logger.error("Failed to parse BGP announcement")
        print("Error: Failed to parse BGP announcement")
        return
    logger.debug("Parsed data: %s", json.dumps(parsed_data, indent=2))

    # Create transaction and add to pool
    logger.info("Creating transaction")
    transaction_id = create_transaction(parsed_data)
    if not transaction_id:
        logger.error("Failed to create transaction")
        print("Error: Failed to create transaction")
        return
    logger.debug("Created transaction_id: %s", transaction_id)

    # Simulate peer verification (in practice, other nodes run verify_transaction.py)
    logger.info("Simulating peer verification for transaction %s", transaction_id)
    print(f"Simulating verification for transaction {transaction_id} by peer nodes")
    peer_asns = []
    while len(peer_asns) < 3:
        try:
            peer_asn = int(input(f"Enter peer node ASN to verify transaction (need {3 - len(peer_asns)} more): "))
            if peer_asn == node_asn:
                logger.warning("Peer ASN %s matches node ASN, skipping", peer_asn)
                print(f"Error: Peer ASN {peer_asn} cannot match node ASN {node_asn}")
                continue
            if peer_asn in peer_asns:
                logger.warning("Peer ASN %s already used, skipping", peer_asn)
                print(f"Error: Peer ASN {peer_asn} already used")
                continue
            logger.info("Verifying transaction %s with peer ASN %s", transaction_id, peer_asn)
            result = verify_pool_transaction(transaction_id, peer_asn)
            logger.debug("Peer verification result for ASN %s: %s", peer_asn, json.dumps(result, indent=2))
            if result["signature_valid"] and result["vote_added"]:
                peer_asns.append(peer_asn)
                print(f"Peer ASN {peer_asn} verified and voted for transaction {transaction_id}")
            else:
                logger.warning("Verification failed for peer ASN %s: %s", peer_asn, result["error"])
                print(f"Error: Verification failed for peer ASN {peer_asn}: {result['error']}")
        except ValueError:
            logger.error("Invalid peer ASN entered")
            print("Error: Peer ASN must be a number")

    # Commit transactions to blockchain
    logger.info("Committing transactions to blockchain")
    transactions = get_verified_transactions(min_votes=3)
    logger.debug("Retrieved %d verified transactions: %s", 
                 len(transactions), [tx["transaction_id"] for tx in transactions])
    if not transactions:
        logger.warning("No transactions with ≥3 votes to commit")
        print("Warning: No transactions with ≥3 votes to commit")
    else:
        block_id = commit_to_blockchain(node_asn)
        if not block_id:
            logger.error("Failed to commit to blockchain")
            print("Error: Failed to commit to blockchain")
            return
        logger.debug("Committed block_id: %s", block_id)

    # Verify the transaction in the blockchain (if not initiated by this node)
    logger.info("Verifying transaction %s in blockchain", transaction_id)
    if parsed_data["sender_asn"] == node_asn:
        logger.warning("Skipping blockchain verification for transaction %s: initiated by this node (ASN %s)", 
                       transaction_id, node_asn)
        print(f"Skipping verification for transaction {transaction_id}: initiated by this node (ASN {node_asn})")
    else:
        result = verify_blockchain_transaction(transaction_id, node_asn)
        logger.debug("Blockchain verification result: %s", json.dumps(result, indent=2))
        print(f"Blockchain verification result: {result}")

    logger.info("Finished main.py")

if __name__ == "__main__":
    logger.info("Starting main.py")
    node_asn = input("Enter this node's ASN: ")
    try:
        node_asn = int(node_asn)
        main(node_asn)
    except ValueError:
        logger.error("Invalid node ASN: %s", node_asn)
        print("Error: Node ASN must be a number")
    logger.info("Finished main.py")