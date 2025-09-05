# =============================================================================
# File: adaptive_trust_engine/behavioral_metrics.py
# Location: trust_engine/adaptive_trust_engine/behavioral_metrics.py
# Called by: adaptive_trust_engine.py
# Calls: historical_analyzer.py, shared/config.py
# Input: AS number to analyze
# Output: 5 behavioral metric scores
# =============================================================================

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
trust_engine_root = current_dir.parent
sys.path.insert(0, str(trust_engine_root))

from adaptive_trust_engine.historical_analyzer import HistoricalAnalyzer
from shared.config import Config

class BehavioralMetrics:
    """
    Calculates all 5 behavioral metrics for ATE evaluation
    Each metric scores 0-100 based on AS behavior patterns
    """
    
    def __init__(self):
        self.config = Config()
        self.analyzer = HistoricalAnalyzer()
        
    def calculate_all_metrics(self, as_number):
        """
        Calculate all 5 behavioral metrics for given AS
        Input: as_number (int)
        Output: Dictionary with all metric scores
        """
        metrics = {}
        
        # Get historical data for analysis
        historical_data = self.analyzer.get_historical_data(as_number)
        
        # Calculate each metric
        metrics['attack_frequency'] = self._calculate_attack_frequency(historical_data)
        metrics['announcement_stability'] = self._calculate_announcement_stability(historical_data)
        metrics['prefix_consistency'] = self._calculate_prefix_consistency(historical_data)
        metrics['response_time'] = self._calculate_response_time(historical_data)
        metrics['participation'] = self._calculate_participation_consistency(historical_data)
        
        return metrics
    
    def _calculate_attack_frequency(self, historical_data):
        """
        Calculate attack frequency metric (f1)
        Formula: f1 = max(0, 100 - (V_count × 20))
        """
        violations_30d = historical_data.get('violations_30d', 0)
        
        # Base calculation
        score = max(0, 100 - (violations_30d * 20))
        
        # Check for escalation pattern
        if self._has_escalation_pattern(historical_data):
            score -= 10  # Escalation penalty
            
        return max(0, score)
    
    def _calculate_announcement_stability(self, historical_data):
        """
        Calculate announcement stability metric (f2)
        Formula: f2 = (A_total / (A_total + W_total)) × 100
        """
        announcements = historical_data.get('announcements_30d', 0)
        withdrawals = historical_data.get('withdrawals_30d', 0)
        
        if announcements + withdrawals == 0:
            return 100  # No activity = perfectly stable
            
        stability_ratio = announcements / (announcements + withdrawals)
        score = stability_ratio * 100
        
        # Apply flapping penalty
        flapping_prefixes = historical_data.get('flapping_prefixes', 0)
        score -= (flapping_prefixes * 5)  # -5 points per flapping prefix
        
        return max(0, score)
    
    def _calculate_prefix_consistency(self, historical_data):
        """
        Calculate prefix ownership consistency metric (f3)
        Formula: f3 = (A_valid / A_total) × 100
        """
        total_announcements = historical_data.get('total_announcements', 0)
        valid_announcements = historical_data.get('valid_announcements', 0)
        
        if total_announcements == 0:
            return 100  # No announcements = perfect consistency
            
        consistency_ratio = valid_announcements / total_announcements
        return consistency_ratio * 100
    
    def _calculate_response_time(self, historical_data):
        """
        Calculate response to detection metric (f4)
        Formula: f4 = max(0, 100 - (T_avg_response / 60))
        """
        avg_response_time = historical_data.get('avg_response_time_seconds', 0)
        
        if avg_response_time == 0:
            return 100  # No violations = perfect response
            
        score = max(0, 100 - (avg_response_time / 60))
        
        # Fast response bonus
        if avg_response_time < 300:  # Less than 5 minutes
            score += 5
            
        return min(100, score)  # Cap at 100
    
    def _calculate_participation_consistency(self, historical_data):
        """
        Calculate participation consistency metric (f5)
        Formula: f5 = (D_active / D_total) × 100
        """
        active_days = historical_data.get('active_days_30d', 0)
        total_days = 30  # 30-day evaluation period
        
        participation_ratio = active_days / total_days
        score = participation_ratio * 100
        
        # Long-term participation bonus
        total_participation_months = historical_data.get('total_participation_months', 0)
        if total_participation_months > 6:
            score += 10  # Long-term bonus
            
        return min(100, score)  # Cap at 100
    
    def _has_escalation_pattern(self, historical_data):
        """
        Check if AS shows escalating attack patterns
        """
        recent_violations = historical_data.get('violations_7d', 0)
        older_violations = historical_data.get('violations_30d', 0) - recent_violations
        
        # If recent violations > older violations, it's escalating
        return recent_violations > (older_violations / 3)
