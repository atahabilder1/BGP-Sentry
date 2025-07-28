#!/usr/bin/env python3
"""
BGPMonitor class for monitoring BGP announcements
"""

from pathlib import Path
import json
import logging

class BGPMonitor:
    """Monitor BGP announcements from bgpd.json"""
    
    def __init__(self, network_stack_path="../network_stack"):
        self.network_stack_path = Path(network_stack_path)
        self.bgpd_path = self.network_stack_path / "bgpd.json"
        self.logger = logging.getLogger(__name__)
        
    def get_latest_announcements(self):
        """Get latest BGP announcements"""
        try:
            if not self.bgpd_path.exists():
                return []
                
            with open(self.bgpd_path, 'r') as f:
                data = json.load(f)
                
            return data.get('bgp_announcements', [])
        except Exception as e:
            self.logger.error(f"Error reading BGP announcements: {e}")
            return []
