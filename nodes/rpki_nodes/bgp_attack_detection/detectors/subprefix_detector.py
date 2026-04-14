#!/usr/bin/env python3
"""
Subprefix Hijacking Detection

Detects more-specific prefix announcements that hijack traffic
"""

import json
import ipaddress
from pathlib import Path

class SubprefixHijackDetector:
    """Detects subprefix (more-specific) hijacking attacks"""
    
    def __init__(self, registry_path):
        self.registry_path = Path(registry_path)
        self.ownership_db = self._load_ownership_database()
    
    def _load_ownership_database(self):
        """Load prefix ownership database"""
        try:
            with open(self.registry_path / "prefix_ownership.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"rpki_nodes": {}, "non_rpki_nodes": {}, "shared_prefixes": {}}
    
    def detect(self, announcement):
        """
        Detect subprefix hijacking attacks
        
        Args:
            announcement: BGP announcement dict
            
        Returns:
            Attack details if subprefix hijacking detected, None otherwise
        """
        sender_asn = announcement['sender_asn']
        announced_prefix = announcement['ip_prefix']
        
        try:
            announced_network = ipaddress.IPv4Network(announced_prefix)
        except ValueError:
            return None
        
        # Check if announced prefix is more specific than any owned prefix
        covering_prefix = self._find_covering_prefix(announced_network, sender_asn)
        
        if covering_prefix:
            return {
                'attack_type': 'subprefix_hijacking',
                'hijacker_asn': sender_asn,
                'legitimate_owner': covering_prefix['owner'],
                'hijacked_subprefix': announced_prefix,
                'parent_prefix': covering_prefix['prefix'],
                'severity': 'high',
                'confidence': 0.90,
                'description': f"AS{sender_asn} announcing more-specific {announced_prefix} of AS{covering_prefix['owner']}'s {covering_prefix['prefix']}"
            }
        
        return None
    
    def _find_covering_prefix(self, announced_network, sender_asn):
        """Find if announced network is covered by someone else's prefix"""
        
        all_prefixes = []
        
        # Collect all owned prefixes
        for node_type in ['rpki_nodes', 'non_rpki_nodes']:
            for owner_asn, prefixes in self.ownership_db.get(node_type, {}).items():
                owner_asn_int = int(owner_asn)
                if owner_asn_int == sender_asn:
                    continue  # Skip sender's own prefixes
                
                for prefix in prefixes:
                    all_prefixes.append({
                        'prefix': prefix,
                        'owner': owner_asn_int,
                        'network': ipaddress.IPv4Network(prefix)
                    })
        
        # Check if announced network is subnet of any owned prefix
        for prefix_info in all_prefixes:
            try:
                if announced_network.subnet_of(prefix_info['network']):
                    return prefix_info
            except ValueError:
                continue
        
        return None
