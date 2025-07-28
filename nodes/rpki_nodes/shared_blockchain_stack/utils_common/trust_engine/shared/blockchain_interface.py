#!/usr/bin/env python3
"""
Blockchain Interface for Trust Engines
"""

import json
from datetime import datetime, timezone
from pathlib import Path

class BlockchainInterface:
    """Interface to blockchain data for trust engines"""
    
    def __init__(self):
        self.blockchain_file = Path("../shared_data/chain/blockchain.json")
        self.transaction_file = Path("../shared_data/chain/transaction_pool.json")
        
        # Load blockchain data
        self.blockchain_data = self._load_blockchain_data()
    
    def _load_blockchain_data(self):
        """Load blockchain data from files"""
        data = {
            'violations': [],
            'trust_scores': {},
            'evaluations': [],
            'transactions': []
        }
        
        # Load from transaction pool
        try:
            if self.transaction_file.exists():
                with open(self.transaction_file, 'r') as f:
                    tx_data = json.load(f)
                    data['transactions'] = tx_data.get('transactions', [])
                    
                    # Extract violations from transactions
                    for tx in data['transactions']:
                        if 'validation_result' in tx:
                            result = tx['validation_result']
                            if 'detection_results' in result:
                                detection = result['detection_results']
                                if not detection.get('legitimate', True):
                                    for attack in detection.get('attacks_detected', []):
                                        violation = {
                                            'as_number': attack.get('hijacker_asn', tx.get('sender_asn')),
                                            'attack_type': attack.get('attack_type'),
                                            'timestamp': tx.get('timestamp'),
                                            'prefix': attack.get('hijacked_prefix')
                                        }
                                        data['violations'].append(violation)
        except Exception as e:
            print(f"Warning: Could not load blockchain data: {e}")
        
        return data
    
    def get_last_evaluation_time(self, as_number):
        """Get last evaluation time for AS from blockchain"""
        evaluations = self.blockchain_data.get('evaluations', [])
        
        as_evaluations = [e for e in evaluations if e.get('as_number') == as_number]
        
        if as_evaluations:
            # Get most recent evaluation
            latest = max(as_evaluations, key=lambda x: x.get('timestamp', ''))
            timestamp_str = latest.get('timestamp')
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        return None
