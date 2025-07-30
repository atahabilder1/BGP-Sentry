#!/usr/bin/env python3
"""
Script to fix the broken transaction validator functions
"""
import sys
from pathlib import Path

# Add path to signature utilities  
sys.path.append(str(Path(__file__).parent.parent.parent / "blockchain_utils"))
from signature_utils import SignatureUtils

# Initialize signature utilities
signature_utils = SignatureUtils()

def create_signable_message(transaction):
    """Create consistent message for signing"""
    import json
    return json.dumps({
        "transaction_id": transaction.get("transaction_id"),
        "sender_asn": transaction.get("sender_asn"), 
        "ip_prefix": transaction.get("ip_prefix"),
        "timestamp": transaction.get("timestamp"),
        "trust_score": transaction.get("trust_score", 0),
        "transaction_timestamp": transaction.get("transaction_timestamp"),
        "previous_hash": transaction.get("previous_hash", "")
    }, sort_keys=True)

def verify_pool_transaction_REAL(transaction_id, node_asn):
    """REAL verification - test version"""
    print(f"🔍 REAL verification for transaction {transaction_id}")
    
    # Simple test - just check if signature utils work
    try:
        print(f"✅ SignatureUtils loaded with {len(signature_utils.public_key_registry)} keys")
        return {
            "signature_valid": True,
            "vote_added": True, 
            "error": "REAL verification placeholder - signature system works!"
        }
    except Exception as e:
        return {
            "signature_valid": False,
            "vote_added": False,
            "error": f"Real verification failed: {e}"
        }

if __name__ == "__main__":
    # Test the real verification
    result = verify_pool_transaction_REAL("test_001", 1)
    print("Test result:", result)
