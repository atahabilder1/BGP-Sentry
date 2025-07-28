#!/usr/bin/env python3
"""
Route Leak Detection

Detects violations of BGP routing policies and business relationships
"""

import json
from pathlib import Path

class RouteLeakDetector:
    """Detects BGP route leak attacks"""
    
    def __init__(self, registry_path):
        self.registry_path = Path(registry_path)
        self.relationships = self._load_relationships()
    
    def _load_relationships(self):
        """Load AS relationship database"""
        try:
            with open(self.registry_path / "as_relationships.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"relationships": {}}
    
    def detect(self, announcement):
        """
        Detect route leak based on AS-path analysis
        
        Args:
            announcement: BGP announcement with as_path field
            
        Returns:
            Attack details if route leak detected, None otherwise
        """
        as_path = announcement.get('as_path', [])
        
        if len(as_path) < 3:
            return None  # Need at least 3 ASes to detect leak
        
        # Check for valley-free routing violations
        violation = self._check_valley_free_violation(as_path)
        
        if violation:
            return {
                'attack_type': 'route_leak',
                'leaking_as': violation['leaking_as'],
                'path_segment': violation['path_segment'],
                'violation_type': violation['violation_type'],
                'severity': 'medium',
                'confidence': 0.85,
                'description': f"AS{violation['leaking_as']} violated routing policy: {violation['violation_type']}"
            }
        
        return None
    
    def _check_valley_free_violation(self, as_path):
        """Check for valley-free routing violations"""
        relationships = self.relationships.get('relationships', {})
        
        for i in range(len(as_path) - 2):
            current_as = as_path[i]
            middle_as = as_path[i + 1]
            next_as = as_path[i + 2]
            
            # Get relationship types
            rel1 = self._get_relationship(current_as, middle_as, relationships)
            rel2 = self._get_relationship(middle_as, next_as, relationships)
            
            # Check for provider-to-peer leak (common violation)
            if rel1 == "customer-provider" and rel2 == "peer-peer":
                return {
                    'leaking_as': middle_as,
                    'path_segment': [current_as, middle_as, next_as],
                    'violation_type': 'provider_to_peer_leak'
                }
        
        return None
    
    def _get_relationship(self, as1, as2, relationships):
        """Get relationship between two ASes"""
        # Try both directions
        key1 = f"{as1}-{as2}"
        key2 = f"{as2}-{as1}"
        
        if key1 in relationships:
            return relationships[key1]
        elif key2 in relationships:
            # Reverse the relationship
            rel = relationships[key2]
            if rel == "customer-provider":
                return "provider-customer"
            elif rel == "provider-customer":
                return "customer-provider"
            else:
                return rel
        
        return "unknown"
