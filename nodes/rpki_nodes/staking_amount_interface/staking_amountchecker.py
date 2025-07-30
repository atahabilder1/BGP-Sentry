#!/usr/bin/env python3
"""
Staking Amount Checker Interface
Economic compensation mechanism for low-trust ASes
"""

import sys
import os
import json
import subprocess
from pathlib import Path

class StakingAmountChecker:
    """Interface to check staking amounts as economic compensation for low trust"""
    
    def __init__(self):
        self.smart_contract_path = Path(__file__).parent.parent.parent.parent / "smart_contract"
        self.wallet_registry_path = Path(__file__).parent.parent / "shared_blockchain_stack/shared_data/shared_registry/nonrpki_wallet_registry.json"
        
        # Economic compensation tiers
        self.compensation_tiers = {
            'high_trust': {'min_score': 80, 'required_stake': 0.04},    # Low stake for high trust
            'medium_trust': {'min_score': 50, 'required_stake': 0.2},   # Medium stake for medium trust  
            'low_trust': {'min_score': 30, 'required_stake': 0.5},      # High stake for low trust
            'very_low_trust': {'min_score': 0, 'required_stake': 1.0}   # Very high stake for very low trust
        }
        
        self.wallet_registry = self._load_wallet_registry()
        
    def _load_wallet_registry(self):
        """Load AS number to wallet address mapping"""
        try:
            with open(self.wallet_registry_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading wallet registry: {e}")
            return {}
    
    def get_wallet_address(self, as_number):
        """Get wallet address for AS number"""
        as_key = f"as{as_number:02d}"
        return self.wallet_registry.get(as_key)
    
    def get_trust_score(self, as_number):
        """Get current trust score (reputation) for AS"""
        trust_state_path = Path(__file__).parent.parent / "shared_blockchain_stack/shared_data/state/trust_state.json"
        
        try:
            with open(trust_state_path, 'r') as f:
                trust_scores = json.load(f)
            return trust_scores.get(str(as_number), 50)  # Default neutral score
        except Exception as e:
            print(f"❌ Error loading trust score for AS{as_number}: {e}")
            return 50
    
    def calculate_required_stake_for_compensation(self, trust_score):
        """Calculate required stake based on trust score (economic compensation)"""
        
        # Lower trust = Higher stake required (compensation mechanism)
        if trust_score >= 80:
            return self.compensation_tiers['high_trust']['required_stake']
        elif trust_score >= 50:
            return self.compensation_tiers['medium_trust']['required_stake']
        elif trust_score >= 30:
            return self.compensation_tiers['low_trust']['required_stake']
        else:
            return self.compensation_tiers['very_low_trust']['required_stake']
    
    def get_current_stake_amount(self, as_number):
        """Get current staked amount from smart contract"""
        wallet_address = self.get_wallet_address(as_number)
        
        if not wallet_address:
            return 0.0
        
        try:
            # Call hardhat script to check actual stake
            script_path = self.smart_contract_path / "scripts/check_single_stake.js"
            
            if not script_path.exists():
                return self._get_mock_stake(as_number)
            
            # Set environment and run script
            env = os.environ.copy()
            env['ADDRESS'] = wallet_address
            
            result = subprocess.run(
                ['npx', 'hardhat', 'run', str(script_path), '--network', 'localhost'],
                cwd=str(self.smart_contract_path),
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode == 0:
                # Parse stake amount from output
                output = result.stdout.strip()
                for line in output.split('\n'):
                    if 'ETH' in line and ':' in line:
                        try:
                            stake_str = line.split(':')[1].strip().replace('ETH', '').strip()
                            return float(stake_str)
                        except ValueError:
                            continue
            
            return self._get_mock_stake(as_number)
                
        except Exception as e:
            print(f"❌ Error checking stake for AS{as_number}: {e}")
            return self._get_mock_stake(as_number)
    
    def _get_mock_stake(self, as_number):
        """Mock staking amounts for testing"""
        mock_stakes = {
            2: 0.2, 4: 0.15, 6: 0.3, 8: 0.25, 10: 0.18,
            12: 0.12, 14: 0.35, 16: 0.22, 18: 0.28, 20: 0.19
        }
        return mock_stakes.get(as_number, 0.1)
    
    def check_participation_eligibility(self, as_number):
        """Check if AS can participate in BGP announcements"""
        
        # Get current reputation and stake
        trust_score = self.get_trust_score(as_number)
        current_stake = self.get_current_stake_amount(as_number)
        required_stake = self.calculate_required_stake_for_compensation(trust_score)
        
        # Determine eligibility
        can_participate = current_stake >= required_stake
        
        # Determine reason for participation
        if trust_score >= 80:
            participation_reason = "High reputation"
        elif can_participate:
            participation_reason = "Economic compensation (sufficient stake)"
        else:
            participation_reason = "Insufficient economic compensation"
        
        return {
            'as_number': as_number,
            'can_participate': can_participate,
            'reason': participation_reason,
            'trust_score': trust_score,
            'current_stake': current_stake,
            'required_stake': required_stake,
            'stake_deficit': max(0, required_stake - current_stake),
            'wallet_address': self.get_wallet_address(as_number),
            'compensation_tier': self._get_compensation_tier(trust_score)
        }
    
    def _get_compensation_tier(self, trust_score):
        """Get compensation tier name"""
        if trust_score >= 80:
            return 'high_trust'
        elif trust_score >= 50:
            return 'medium_trust'
        elif trust_score >= 30:
            return 'low_trust'
        else:
            return 'very_low_trust'
    
    def get_participation_summary(self):
        """Get participation eligibility for all non-RPKI ASes"""
        non_rpki_ases = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        results = []
        
        for as_number in non_rpki_ases:
            eligibility = self.check_participation_eligibility(as_number)
            results.append(eligibility)
        
        return results

# Convenience functions
def can_as_participate(as_number):
    """Quick check if AS can participate"""
    checker = StakingAmountChecker()
    result = checker.check_participation_eligibility(as_number)
    return result['can_participate']

def get_stake_requirement(as_number):
    """Get stake requirement for AS"""
    checker = StakingAmountChecker()
    trust_score = checker.get_trust_score(as_number)
    return checker.calculate_required_stake_for_compensation(trust_score)

if __name__ == "__main__":
    """Test the economic compensation system"""
    checker = StakingAmountChecker()
    
    print("💰 BGP-Sentry Economic Compensation System")
    print("=" * 60)
    print("Lower Trust Score → Higher Stake Required (Compensation)")
    print("=" * 60)
    
    # Show compensation tiers
    print("\n📊 Compensation Tiers:")
    print("  High Trust (80+):     0.04 ETH required")
    print("  Medium Trust (50-79): 0.2 ETH required") 
    print("  Low Trust (30-49):    0.5 ETH required")
    print("  Very Low Trust (0-29): 1.0 ETH required")
    
    # Test individual ASes
    print(f"\n🔍 Individual AS Analysis:")
    test_ases = [2, 4, 6, 8]
    
    for as_number in test_ases:
        print(f"\n--- AS{as_number:02d} Analysis ---")
        eligibility = checker.check_participation_eligibility(as_number)
        
        status = "✅ Can Participate" if eligibility['can_participate'] else "❌ Cannot Participate"
        
        print(f"Status: {status}")
        print(f"Reason: {eligibility['reason']}")
        print(f"Trust Score: {eligibility['trust_score']} (reputation)")
        print(f"Current Stake: {eligibility['current_stake']:.3f} ETH")
        print(f"Required Stake: {eligibility['required_stake']:.3f} ETH")
        print(f"Compensation Tier: {eligibility['compensation_tier']}")
        
        if not eligibility['can_participate']:
            print(f"Need Additional: {eligibility['stake_deficit']:.3f} ETH")
    
    # Full participation report
    print(f"\n📋 Full Non-RPKI AS Participation Report:")
    print("=" * 60)
    
    summary = checker.get_participation_summary()
    
    can_participate = sum(1 for r in summary if r['can_participate'])
    total = len(summary)
    
    print(f"Participation Rate: {can_participate}/{total} ASes eligible")
    print()
    
    for result in summary:
        status_icon = "✅" if result['can_participate'] else "❌"
        trust = result['trust_score']
        stake = result['current_stake']
        required = result['required_stake']
        
        print(f"{status_icon} AS{result['as_number']:02d}: Trust={trust:2.0f}, Stake={stake:.3f}/{required:.3f} ETH")
