#!/usr/bin/env python3
"""
Transaction signing utilities for BGP announcements
"""
import json
import logging
from pathlib import Path
from signature_utils import SignatureUtils

class TransactionSigner:
    """Signs BGP transactions with AS private keys"""
    
    def __init__(self, as_number):
        self.as_number = as_number
        self.signature_utils = SignatureUtils()
        self.logger = logging.getLogger(__name__)
        
    def sign_transaction(self, transaction_data):
        """Sign a transaction with the AS's private key"""
        try:
            # Find private key file
            private_key_path = self._get_private_key_path()
            self.logger.info(f"Signing transaction for AS{self.as_number:02d}")
            
            # Create transaction message to sign (must match validator format)
            message = self._create_signable_message(transaction_data)
            
            # Sign the message
            signature = self.signature_utils.sign_message(message, private_key_path)
            
            if signature:
                transaction_data["signature"] = signature
                self.logger.info(f"✅ Transaction signed successfully for AS{self.as_number:02d}")
                return transaction_data
            else:
                raise Exception("Failed to create signature")
                
        except Exception as e:
            self.logger.error(f"Transaction signing failed for AS{self.as_number:02d}: {e}")
            raise Exception(f"Transaction signing failed: {e}")
    
    def _get_private_key_path(self):
        """Find the private key file for this AS - CORRECTED PATH"""
        # Correct path: go up to rpki_nodes, then down to specific AS
        rpki_nodes_path = Path(__file__).parent.parent.parent
        as_path = rpki_nodes_path / f"as{self.as_number:02d}"
        private_key_path = as_path / "blockchain_node" / "private_key.pem"
        
        self.logger.debug(f"Looking for private key at: {private_key_path}")
        
        if private_key_path.exists():
            return private_key_path
        
        # If not found, try absolute path
        abs_path = Path(f"/home/anik/code/BGP-Sentry/nodes/rpki_nodes/as{self.as_number:02d}/blockchain_node/private_key.pem")
        if abs_path.exists():
            return abs_path
            
        raise Exception(f"Private key not found for AS{self.as_number:02d}. Tried: {private_key_path} and {abs_path}")
    
    def _create_signable_message(self, transaction_data):
        """Create consistent message format for signing (matches validator)"""
        signable_data = {
            "transaction_id": transaction_data.get("transaction_id"),
            "sender_asn": transaction_data.get("sender_asn"),
            "ip_prefix": transaction_data.get("ip_prefix"),
            "timestamp": transaction_data.get("timestamp"),
            "trust_score": transaction_data.get("trust_score", 0),
            "transaction_timestamp": transaction_data.get("transaction_timestamp"),
            "previous_hash": transaction_data.get("previous_hash", "")
        }
        
        return json.dumps(signable_data, sort_keys=True)

if __name__ == "__main__":
    # Test the signer
    print("🧪 Testing FIXED Transaction Signer...")
    
    # Test with AS01
    signer = TransactionSigner(1)
    
    test_transaction = {
        "transaction_id": "test_signed_001",
        "sender_asn": 1,
        "ip_prefix": "192.0.2.0/24",
        "timestamp": 1234567890,
        "trust_score": 75,
        "transaction_timestamp": 1234567890,
        "previous_hash": ""
    }
    
    try:
        signed_tx = signer.sign_transaction(test_transaction.copy())
        print(f"✅ Signing successful!")
        print(f"   Signature: {signed_tx['signature'][:32]}...")
        print(f"   Transaction ID: {signed_tx['transaction_id']}")
        print("✅ Transaction signing system ready!")
        
    except Exception as e:
        print(f"❌ Signing failed: {e}")
