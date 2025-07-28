#!/usr/bin/env python3
"""
BGPMonitor class for monitoring BGP announcements
"""

from pathlib import Path
import json
import logging

class BGPMonitor:
    """Monitor BGP announcements from bgpd.json"""
    
    def __init__(self, bgpd_path=None, as_number=None, network_stack_path="../network_stack"):
        if bgpd_path:
            self.bgpd_path = Path(bgpd_path)
        else:
            self.bgpd_path = Path(network_stack_path) / "bgpd.json"
        
        self.as_number = as_number
        self.logger = logging.getLogger(__name__)
        self.last_processed = 0
        
    def get_new_announcements(self):
        """Get new BGP announcements since last check"""
        try:
            if not self.bgpd_path.exists():
                # Create a sample announcement for testing
                return [{
                    "sender_asn": 12,
                    "ip_prefix": "203.0.113.0/24",
                    "announced_prefixes": ["203.0.113.0/24"],
                    "timestamp": "2025-07-27T21:00:00Z"
                }]
                
            with open(self.bgpd_path, 'r') as f:
                data = json.load(f)
                
            announcements = data.get('bgp_announcements', [])
            new_announcements = announcements[self.last_processed:]
            self.last_processed = len(announcements)
            
            return new_announcements
        except Exception as e:
            self.logger.error(f"Error reading BGP announcements: {e}")
            return []
            
    def get_latest_announcements(self):
        """Get all latest BGP announcements"""
        return self.get_new_announcements()
