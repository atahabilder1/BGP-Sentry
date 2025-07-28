# =============================================================================
# File: adaptive_trust_engine/historical_analyzer.py
# Location: trust_engine/adaptive_trust_engine/historical_analyzer.py
# Called by: behavioral_metrics.py
# Calls: shared/blockchain_interface.py
# Input: AS number
# Output: Historical behavior data
# =============================================================================

from datetime import datetime, timedelta
from ..shared.blockchain_interface import BlockchainInterface

class HistoricalAnalyzer:
    """
    Analyzes historical BGP behavior data from blockchain
    Provides data for behavioral metric calculations
    """
    
    def __init__(self):
        self.blockchain = BlockchainInterface()
        
    def get_historical_data(self, as_number):
        """
        Gather all historical data needed for metric calculations
        Input: as_number (int)
        Output: Dictionary with historical behavior data
        """
        # Get time windows
        now = datetime.now()
        days_30_ago = now - timedelta(days=30)
        days_7_ago = now - timedelta(days=7)
        
        # Analyze violations
        violations_data = self._analyze_violations(as_number, days_30_ago, days_7_ago)
        
        # Analyze BGP announcements (simulated - would come from BGP logs)
        bgp_data = self._analyze_bgp_activity(as_number, days_30_ago)
        
        # Combine all data
        historical_data = {
            **violations_data,
            **bgp_data,
            'analysis_timestamp': now
        }
        
        return historical_data
    
    def _analyze_violations(self, as_number, days_30_ago, days_7_ago):
        """
        Analyze violation patterns from blockchain
        """
        violations = self.blockchain.blockchain_data.get('violations', [])
        
        # Filter violations for this AS
        as_violations = [v for v in violations if v['as_number'] == as_number]
        
        # Count violations in different time windows
        violations_30d = 0
        violations_7d = 0
        response_times = []
        
        for violation in as_violations:
            v_time = datetime.fromisoformat(violation['timestamp'])
            
            if v_time >= days_30_ago:
                violations_30d += 1
                
                if v_time >= days_7_ago:
                    violations_7d += 1
                
                # Simulate response time (would come from BGP logs)
                response_times.append(300)  # 5 minutes average
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'violations_30d': violations_30d,
            'violations_7d': violations_7d,
            'avg_response_time_seconds': avg_response_time
        }
    
    def _analyze_bgp_activity(self, as_number, days_30_ago):
        """
        Analyze BGP announcement patterns (simulated data)
        In real implementation, this would parse BGP logs
        """
        # Simulated BGP activity data
        # In real implementation, this would analyze actual BGP logs
        
        return {
            'announcements_30d': 100,      # Total announcements
            'withdrawals_30d': 10,         # Total withdrawals  
            'valid_announcements': 95,     # Registry-validated announcements
            'total_announcements': 100,    # All announcements
            'flapping_prefixes': 1,        # Prefixes with >10 updates/day
            'active_days_30d': 28,         # Days with BGP activity
            'total_participation_months': 12  # Total months of participation
        }