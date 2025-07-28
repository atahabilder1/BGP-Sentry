#!/usr/bin/env python3
"""
Prefix Hijacking Detection

Detects unauthorized announcements of prefixes owned by other ASes
"""

import json
from pathlib import Path

class PrefixHijackDetector:
    """Detects direct prefix hijacking attacks"""
    
    def __init__(self, registry_path):
        self.registry_path = Path(registry_path)
        self.ownership_db = self._load_ownership_database()
    
    def _load_ownership_database(self):
        """Load prefix ownership database from shared registry"""
        try:
            with open(self.registry_path / "prefix_ownership.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: prefix_ownership.json not found")
            return {"rpki_nodes": {}, "non_rpki_nodes": {}, "shared_prefixes": {}}
    
    def detect(self, announcement):
        """
        Detect if announcement is a prefix hijacking attack
        
        Args:
            announcement: BGP announcement dict with sender_asn and ip_prefix
            
        Returns:
            Attack details if hijacking detected, None otherwise
        """
        sender_asn = announcement['sender_asn']
        announced_prefix = announcement['ip_prefix']
        
        # Check ownership in all databases
        legitimate_owner = self._find_legitimate_owner(announced_prefix)
        
        if legitimate_owner and legitimate_owner != sender_asn:
            return {
                'attack_type': 'prefix_hijacking',
                'hijacker_asn': sender_asn,
                'legitimate_owner': legitimate_owner,
                'hijacked_prefix': announced_prefix,
                'severity': 'critical',
                'confidence': 0.95,
                'description': f"AS{sender_asn} illegally announcing prefix {announced_prefix} owned by AS{legitimate_owner}"
            }
        
        return None
    
    def _find_legitimate_owner(self, prefix):
        """Find the legitimate owner of a prefix"""
        
        # Check RPKI nodes
        for owner_asn, prefixes in self.ownership_db.get('rpki_nodes', {}).items():
            if prefix in prefixes:
                return int(owner_asn)
        
        # Check non-RPKI nodes
        for owner_asn, prefixes in self.ownership_db.get('non_rpki_nodes', {}).items():
            if prefix in prefixes:
                return int(owner_asn)
        
        # Check shared prefixes
        if prefix in self.ownership_db.get('shared_prefixes', {}):
            return int(self.ownership_db['shared_prefixes'][prefix])
        
        return None
