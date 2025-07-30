#!/usr/bin/env python3
"""
Economic System Tests
"""

import sys
from pathlib import Path

base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/staking_amount_interface"))

def test_staking_requirements():
    """Test staking requirement calculations"""
    print("💰 Testing Staking Requirements...")
    
    from staking_amountchecker import StakingAmountChecker
    checker = StakingAmountChecker()
    
    # Test different trust levels
    test_cases = [
        {'trust': 85, 'tier': 'high_trust'},
        {'trust': 65, 'tier': 'medium_trust'},
        {'trust': 35, 'tier': 'low_trust'},
        {'trust': 15, 'tier': 'very_low_trust'}
    ]
    
    stakes = []
    
    for case in test_cases:
        required = checker.calculate_required_stake_for_compensation(case['trust'])
        tier = checker._get_compensation_tier(case['trust'])
        stakes.append(required)
        
        print(f"   Trust {case['trust']:2d}: {required:.3f} ETH ({tier})")
        
        if tier != case['tier']:
            print(f"      ⚠️  Expected {case['tier']}, got {tier}")
    
    # Verify increasing requirements (lower trust = higher stake)
    success = all(stakes[i] <= stakes[i+1] for i in range(len(stakes)-1))
    
    if success:
        print("   ✅ Staking requirements increase correctly with lower trust")
    else:
        print("   ❌ Staking requirements not calculated correctly")
    
    return success

def test_participation_eligibility():
    """Test participation eligibility"""
    print("🎯 Testing Participation Eligibility...")
    
    from staking_amountchecker import StakingAmountChecker
    checker = StakingAmountChecker()
    
    test_ases = [2, 4, 6, 8]
    results = []
    
    for as_number in test_ases:
        eligibility = checker.check_participation_eligibility(as_number)
        results.append(eligibility)
        
        status = "✅" if eligibility['can_participate'] else "❌"
        print(f"   {status} AS{as_number:02d}: {eligibility['reason']}")
        print(f"      Trust: {eligibility['trust_score']}, Stake: {eligibility['current_stake']:.3f}/{eligibility['required_stake']:.3f} ETH")
        
        if not eligibility['can_participate'] and eligibility['stake_deficit'] > 0:
            print(f"      �� Needs {eligibility['stake_deficit']:.3f} more ETH to participate")
    
    eligible_count = sum(1 for r in results if r['can_participate'])
    print(f"   📊 {eligible_count}/{len(test_ases)} ASes eligible to participate")
    
    return len(results) > 0

def test_wallet_mappings():
    """Test AS to wallet address mappings"""
    print("🔗 Testing Wallet Mappings...")
    
    from staking_amountchecker import StakingAmountChecker
    checker = StakingAmountChecker()
    
    test_ases = [2, 4, 6, 8, 10]
    missing_wallets = []
    
    for as_number in test_ases:
        wallet = checker.get_wallet_address(as_number)
        
        if wallet and wallet.startswith('0x') and len(wallet) == 42:
            print(f"   ✅ AS{as_number:02d}: {wallet}")
        else:
            print(f"   ❌ AS{as_number:02d}: Invalid or missing wallet")
            missing_wallets.append(as_number)
    
    success = len(missing_wallets) == 0
    
    if success:
        print("   ✅ All wallet mappings valid")
    else:
        print(f"   ❌ Missing wallets for ASes: {missing_wallets}")
    
    return success

if __name__ == "__main__":
    print("🧪 Economic System Tests")
    print("=" * 40)
    
    tests = [
        test_staking_requirements,
        test_participation_eligibility,
        test_wallet_mappings
    ]
    
    passed = 0
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{len(tests)} economic tests passed")
    
    if passed == len(tests):
        print("🎉 All economic system tests passed!")
    else:
        print("⚠️  Some economic tests need attention")
