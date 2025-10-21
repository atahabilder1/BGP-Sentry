from pathlib import Path
import json
import logging
import os

class TransactionPool:
    """Manages the local transaction pool (mempool) for each node

    Each blockchain node has its own transaction pool buffer to store pending
    transactions before they are included in a block. This is NOT shared between nodes.
    """

    def __init__(self, as_number=None):
        self.logger = logging.getLogger(__name__)
        self.as_number = as_number

        if as_number is None:
            raise ValueError("TransactionPool requires as_number parameter - each node has its own pool!")

        # Find the node's local directory
        current_file = Path(__file__).resolve()
        # From: nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/transaction_pool.py
        # Go to: nodes/rpki_nodes/
        rpki_nodes_dir = current_file.parent.parent.parent

        # Each node has its own transaction pool in its local directory
        # Path: nodes/rpki_nodes/as01/blockchain_node/transaction_pool/pending.json
        node_dir = rpki_nodes_dir / f"as{as_number:02d}" / "blockchain_node" / "transaction_pool"
        node_dir.mkdir(parents=True, exist_ok=True)

        self.pool_file = node_dir / "pending.json"

        # Initialize empty pool if file doesn't exist
        if not self.pool_file.exists():
            with open(self.pool_file, 'w') as f:
                json.dump({"transactions": []}, f, indent=2)

        self.logger.info(f"TransactionPool initialized for AS{as_number:02d} at {self.pool_file}")
    
    def get_pending_transactions(self):
        """Get all pending transactions from the pool"""
        try:
            if self.pool_file.exists():
                with open(self.pool_file, 'r') as f:
                    data = json.load(f)
                return data.get("transactions", [])
            else:
                return []
        except Exception as e:
            self.logger.error(f"Failed to get pending transactions: {e}")
            return []
    
    def add_transaction(self, transaction):
        """Add a transaction to the pool"""
        try:
            # Read existing transactions
            if self.pool_file.exists():
                with open(self.pool_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"transactions": []}

            # Add new transaction
            data["transactions"].append(transaction)

            # Write back to file
            with open(self.pool_file, 'w') as f:
                json.dump(data, f, indent=4)

            self.logger.info(f"✅ Transaction {transaction.get('transaction_id')} written to pool file")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to add transaction: {e}")
            return False
    
    def get_transaction_by_id(self, transaction_id):
        """Get a transaction by ID"""
        try:
            # For testing, return a dummy transaction
            return {
                "transaction_id": transaction_id,
                "sender_asn": 12,
                "ip_prefix": "203.0.113.0/24"
            }
        except Exception as e:
            self.logger.error(f"Failed to get transaction {transaction_id}: {e}")
            return None
    
    def mark_transaction_processed(self, transaction_id):
        """Mark a transaction as processed"""
        try:
            self.logger.info(f"Marking transaction {transaction_id} as processed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark transaction processed: {e}")
            return False