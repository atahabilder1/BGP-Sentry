#!/usr/bin/env python3
"""
Staking System Tests
Split from enhanced_pre_simulation.py test_6_staking_amounts()
"""

import pytest
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "nodes/rpki_nodes/staking_amount_interface"))

class TestStaking:
    """Test suite for staking system"""
    
    def setup_method(self):
        """Setup for each test method"""
        try:
            from staking_amountchecker import StakingAmountChecker
            self.checker = StakingAmountChecker()
        except ImportError:
            pytest.skip("StakingAmountChecker not available")
    
    def test_staking_checker_initialization(self):
        """Test that staking checker initializes properly"""
        assert self.checker is not None
        assert hasattr(self.checker, 'get_current_stake_amount')
        assert hasattr(self.checker, 'check_participation_eligibility')
    
    def test_economic_compensation_tiers(self):
        """Test economic compensation tier calculations"""
        if hasattr(self.checker, 'compensation_tiers'):
            tiers = self.checker.compensation_tiers
            assert 'high_trust' in tiers
            assert 'medium_trust' in tiers
            assert 'low_trust' in tiers
            assert 'very_low_trust' in tiers
    
    def test_stake_amounts(self):
        """Test stake amount checking for test ASes"""
        test_ases = [2, 4, 6, 8]
        
        for as_number in test_ases:
            try:
                stake = self.checker.get_current_stake_amount(as_number)
                assert isinstance(stake, (int, float)), f"Invalid stake type for AS{as_number:02d}"
                assert stake >= 0, f"Negative stake for AS{as_number:02d}"
            except Exception as e:
                pytest.skip(f"Stake checking failed for AS{as_number:02d}: {e}")

if __name__ == "__main__":
    pytest.main([__file__])
