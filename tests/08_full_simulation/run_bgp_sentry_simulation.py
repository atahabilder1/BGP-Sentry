#!/usr/bin/env python3
"""
Enhanced BGP-Sentry Full Simulation with Real Cryptographic Signatures
"""

import sys
import os
import time
import json
import uuid
from pathlib import Path
from datetime import datetime

# Add paths for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root / "nodes/rpki_nodes/rpki_verification_interface"))
sys.path.insert(0, str(project_root / "nodes/rpki_nodes/bgp_attack_detection"))
sys.path.insert(0, str(project_root / "nodes/rpki_nodes/trust_score_interface"))
sys.path.insert(0, str(project_root / "nodes/rpki_nodes/staking_amount_interface"))
sys.path.insert(0, str(project_root / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"))
sys.path.insert(0, str(project_root / "trust_engine"))

# Import signature system
from transaction_signer import TransactionSigner
from signature_utils import SignatureUtils

# Import existing components
from verifier import is_as_verified, get_all_unverified_ases
from attack_detector_fixed import BGPSecurityAnalyzer
from trust_engine_interface import TrustEngineInterface
from staking_amountchecker import StakingAmountChecker
from main_trust_coordinator_fixed import TrustCoordinator

class BlockchainWriter:
    """Writes signed transactions to blockchain"""
    
    def __init__(self):
        self.blockchain_path = project_root / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/chain/blockchain.json"
        
    def write_transaction(self, signed_transaction):
        """Write a signed transaction to blockchain"""
        try:
            # Load existing blockchain
            if self.blockchain_path.exists():
                with open(self.blockchain_path, 'r') as f:
                    blockchain = json.load(f)
            else:
                blockchain = []
            
            # Create new block with transaction
            block = {
                "index": len(blockchain),
                "timestamp": int(time.time()),
                "previous_hash": blockchain[-1].get("hash", "0" * 64) if blockchain else "0" * 64,
                "transactions": [signed_transaction],
                "hash": self._calculate_block_hash(signed_transaction)
            }
            
            blockchain.append(block)
            
            # Write back to file
            with open(self.blockchain_path, 'w') as f:
                json.dump(blockchain, f, indent=2)
                
            print(f"   💾 Transaction written to blockchain (Block {block['index']})")
            return True
            
        except Exception as e:
            print(f"   ❌ Blockchain write failed: {e}")
            return False
    
    def _calculate_block_hash(self, transaction):
        """Calculate block hash"""
        import hashlib
        data = json.dumps(transaction, sort_keys=True).encode()
        return hashlib.sha256(data).hexdigest()

def main():
    print("🚀 BGP-Sentry Enhanced Simulation with Real Signatures")
    print("=" * 70)
    
    # Initialize components
    print("🔧 Initializing Systems...")
    analyzer = BGPSecurityAnalyzer()
    trust_interface = TrustEngineInterface()
    staking_checker = StakingAmountChecker()
    blockchain_writer = BlockchainWriter()
    signature_utils = SignatureUtils()
    
    print(f"✅ All systems initialized")
    print(f"🔐 Signature system loaded with {len(signature_utils.public_key_registry)} AS keys")
    
    # Test announcements from different AS types
    test_announcements = [
        {'as_number': 1, 'prefix': '192.0.2.0/24', 'description': 'RPKI-valid AS (should pass)'},
        {'as_number': 2, 'prefix': '203.0.113.0/24', 'description': 'Non-RPKI AS (good behavior)'},
        {'as_number': 4, 'prefix': '192.0.2.0/24', 'description': 'Non-RPKI AS (prefix hijack attempt)'},
    ]
    
    print(f"\n📡 Simulating BGP Announcements with Real Signatures:")
    print("-" * 50)
    
    results = []
    
    for announcement in test_announcements:
        print(f"\n🔍 Testing: AS{announcement['as_number']:02d} announces {announcement['prefix']}")
        print(f"   Scenario: {announcement['description']}")
        
        # Create transaction data
        transaction_data = {
            "transaction_id": str(uuid.uuid4()),
            "sender_asn": announcement['as_number'],
            "ip_prefix": announcement['prefix'],
            "timestamp": int(time.time()),
            "trust_score": 75,  # Default
            "transaction_timestamp": int(time.time()),
            "previous_hash": ""
        }
        
        # Check RPKI status
        if is_as_verified(announcement['as_number']):
            print(f"   ✅ RPKI-valid AS → Automatically approved")
            
            # Sign transaction for RPKI AS
            try:
                signer = TransactionSigner(announcement['as_number'])
                signed_transaction = signer.sign_transaction(transaction_data.copy())
                print(f"   🔐 Transaction signed: {signed_transaction['signature'][:32]}...")
                
                # Write to blockchain
                blockchain_writer.write_transaction(signed_transaction)
                results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'RPKI valid', 'signed': True})
                
            except Exception as e:
                print(f"   ❌ Signing failed: {e}")
                results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'RPKI valid', 'signed': False})
            continue
        
        # Check economic eligibility for non-RPKI
        eligibility = staking_checker.check_participation_eligibility(announcement['as_number'])
        
        if not eligibility['can_participate']:
            print(f"   ❌ Economic eligibility failed: {eligibility['reason']}")
            results.append({'as': announcement['as_number'], 'result': 'rejected', 'reason': 'insufficient stake', 'signed': False})
            continue
        
        print(f"   ✅ Economic eligibility passed: {eligibility['current_stake']:.3f} ETH staked")
        
        # Attack detection
        detection_result = analyzer.analyze_announcement(announcement)
        
        if detection_result['legitimate']:
            print(f"   ✅ Attack detection: Clean announcement")
            
            # Sign and write legitimate transaction
            try:
                signer = TransactionSigner(announcement['as_number'])
                signed_transaction = signer.sign_transaction(transaction_data.copy())
                print(f"   🔐 Transaction signed: {signed_transaction['signature'][:32]}...")
                
                # Write to blockchain
                blockchain_writer.write_transaction(signed_transaction)
                results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'clean', 'signed': True})
                
            except Exception as e:
                print(f"   ❌ Signing failed: {e}")
                results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'clean', 'signed': False})
                
        else:
            attacks = detection_result['attacks_detected']
            print(f"   🚨 Attack detection: {len(attacks)} attack(s) detected")
            for attack in attacks:
                print(f"      - {attack.get('type', 'unknown')} attack")
            results.append({'as': announcement['as_number'], 'result': 'rejected', 'reason': 'attack detected', 'signed': False})
    
    # Enhanced simulation summary
    print(f"\n" + "=" * 70)
    print(f"📋 ENHANCED SIMULATION SUMMARY")
    print(f"=" * 70)
    
    approved = sum(1 for r in results if r['result'] == 'approved')
    rejected = sum(1 for r in results if r['result'] == 'rejected')
    signed = sum(1 for r in results if r.get('signed', False))
    
    print(f"📊 Results: {approved} approved, {rejected} rejected out of {len(results)} announcements")
    print(f"🔐 Cryptographic Security: {signed} transactions signed with real RSA signatures")
    
    print(f"\n📈 Detailed Results:")
    for result in results:
        status_icon = "✅" if result['result'] == 'approved' else "❌"
        signature_icon = "🔐" if result.get('signed', False) else "🚫"
        print(f"   {status_icon} AS{result['as']:02d}: {result['result'].upper()} ({result['reason']}) {signature_icon}")
    
    print(f"\n🎯 Enhanced Security Features:")
    print(f"   • Real RSA signatures: {signed} transactions cryptographically secured")
    print(f"   • Blockchain storage: Signed transactions written to permanent ledger")
    print(f"   • Signature verification: Each transaction verifiable with AS public keys")
    print(f"   • Attack prevention: {len([r for r in results if r['reason'] == 'attack detected'])} attacks blocked")
    
    print(f"\n🎉 Enhanced Simulation Complete!")
    print(f"📁 Blockchain data: ~/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/shared_data/chain/blockchain.json")

if __name__ == "__main__":
    main()
