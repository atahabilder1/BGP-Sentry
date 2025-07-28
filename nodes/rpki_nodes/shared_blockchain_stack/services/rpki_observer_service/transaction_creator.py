#!/usr/bin/env python3
"""
TransactionCreator class for creating and signing BGP transactions
"""

from pathlib import Path
import json
import uuid
from datetime import datetime, timezone
import hashlib
import logging

class TransactionCreator:
    """Creates and signs transactions from BGP announcements"""
    
    def __init__(self, as_number, private_key_path):
        self.as_number = as_number
        self.private_key_path = Path(private_key_path)
        self.logger = logging.getLogger(__name__)
        
    def create_transaction(self, bgp_data):
        """Create a signed transaction from BGP data"""
        try:
            transaction = {
                "transaction_id": str(uuid.uuid4()),
                "observer_as": self.as_number,
                "sender_asn": bgp_data.get("sender_asn"),
                "ip_prefix": bgp_data.get("ip_prefix"),
                "timestamp": bgp_data.get("timestamp"),
                "trust_score": bgp_data.get("trust_score", "N/A"),
                "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
                "previous_hash": "0" * 64,
                "signature": f"test_signature_{self.as_number}_{int(datetime.now().timestamp())}",
                "votes": []
            }
            
            self.logger.info(f"Created transaction {transaction['transaction_id']}")
            return transaction
            
        except Exception as e:
            self.logger.error(f"Failed to create transaction: {e}")
            return None
