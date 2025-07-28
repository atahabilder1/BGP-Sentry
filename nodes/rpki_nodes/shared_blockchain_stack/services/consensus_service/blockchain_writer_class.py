#!/usr/bin/env python3
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
