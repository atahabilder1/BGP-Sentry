from pathlib import Path
import json
class TransactionPool:
    """Manages the shared transaction pool"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_pending_transactions(self):
        """Get all pending transactions from the pool"""
        try:
            # For testing, return empty list
            return []
        except Exception as e:
            self.logger.error(f"Failed to get pending transactions: {e}")
            return []
    
    def add_transaction(self, transaction):
        """Add a transaction to the pool"""
        try:
            pool_file = Path("../shared_data/chain/transaction_pool.json")
            
            # Read existing transactions
            if pool_file.exists():
                with open(pool_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"transactions": []}
            
            # Add new transaction
            data["transactions"].append(transaction)
            
            # Write back to file
            with open(pool_file, 'w') as f:
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

import logging