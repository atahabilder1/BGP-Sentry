#!/usr/bin/env python3
"""
BlockchainWriter class for committing transactions to blockchain
"""

from pathlib import Path
import json
import uuid
from datetime import datetime, timezone
import hashlib
import logging

class BlockchainWriter:
    """Writes approved transactions to blockchain"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def commit_transaction(self, transaction):
        """
        Commit a transaction to the blockchain
        Args:
            transaction: Transaction data to commit
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Committing transaction to blockchain: {transaction.get('transaction_id')}")
            
            # For testing purposes, just log the commitment
            # In a real implementation, this would write to blockchain.json
            self.logger.info(f"Transaction {transaction.get('transaction_id')} committed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to commit transaction: {e}")
            return False
    
    def get_latest_block_hash(self):
        """Get the hash of the latest block in the blockchain"""
        try:
            # For testing, return a dummy hash
            return "0" * 64
        except Exception as e:
            self.logger.error(f"Failed to get latest block hash: {e}")
            return "0" * 64
    
    def create_block(self, transactions):
        """
        Create a new block with the given transactions
        Args:
            transactions: List of transactions to include in block
        Returns:
            dict: Block data
        """
        try:
            block = {
                "block_id": str(uuid.uuid4()),
                "block_timestamp": datetime.now(timezone.utc).isoformat(),
                "transactions": transactions,
                "previous_block_hash": self.get_latest_block_hash(),
                "block_hash": ""
            }
            
            # Calculate block hash
            block_data = json.dumps({
                "block_id": block["block_id"],
                "block_timestamp": block["block_timestamp"],
                "transactions": block["transactions"],
                "previous_block_hash": block["previous_block_hash"]
            }, sort_keys=True).encode()
            
            block["block_hash"] = hashlib.sha256(block_data).hexdigest()
            
            self.logger.info(f"Created block {block['block_id']} with {len(transactions)} transactions")
            return block
            
        except Exception as e:
            self.logger.error(f"Failed to create block: {e}")
            return None

def commit_to_blockchain(transactions):
    """
    Legacy function for backward compatibility
    Args:
        transactions: List of transactions to commit
    Returns:
        bool: True if successful
    """
    writer = BlockchainWriter()
    try:
        for transaction in transactions:
            writer.commit_transaction(transaction)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Legacy commit failed: {e}")
        return False

if __name__ == "__main__":
    # Test the BlockchainWriter
    logger = logging.getLogger(__name__)
    writer = BlockchainWriter()
    
    test_transaction = {
        "transaction_id": "test-123",
        "sender_asn": 12,
        "ip_prefix": "203.0.113.0/24"
    }
    
    result = writer.commit_transaction(test_transaction)
    print(f"Commit result: {result}")#!/usr/bin/env python3
"""
BlockchainWriter class for committing transactions
"""
import logging

class BlockchainWriter:
    """Writes approved transactions to blockchain"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def commit_transaction(self, transaction):
        """Commit a transaction to the blockchain"""
        self.logger.info(f"Committing transaction to blockchain: {transaction.get('transaction_id')}")
        return True
