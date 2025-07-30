#!/usr/bin/env python3
"""
BGP-Sentry Full Simulation
Complete end-to-end BGP security simulation
"""

import sys
import time
from pathlib import Path

# Add interface paths
base_path = Path(__file__).parent.parent.parent
interfaces = [
    'nodes/rpki_nodes/bgp_attack_detection',
    'nodes/rpki_nodes/rpki_verification_interface', 
    'nodes/rpki_nodes/trust_score_interface',
    'nodes/rpki_nodes/staking_amount_interface',
    'nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils'
]

for interface in interfaces:
    sys.path.insert(0, str(base_path / interface))

def run_full_simulation():
    """Run complete BGP-Sentry simulation"""
    
    print("🚀 BGP-Sentry Full Simulation Starting...")
    print("=" * 60)
    
    # Import all modules
    from verifier import is_as_verified
    from attack_detector_fixed import BGPSecurityAnalyzer
    from trust_engine_interface import TrustEngineInterface
    from staking_amountchecker import StakingAmountChecker
    
    # Initialize systems
    print("\n🔧 Initializing Systems...")
    analyzer = BGPSecurityAnalyzer()
    trust_engine = TrustEngineInterface()
    staking_checker = StakingAmountChecker()
    
    print("✅ All systems initialized")
    
    # Check current system status
    print("\n💰 Economic Participation Status:")
    print("-" * 40)
    
    eligibility_summary = staking_checker.get_participation_summary()
    
    can_participate = sum(1 for r in eligibility_summary if r['can_participate'])
    total = len(eligibility_summary)
    
    print(f"Eligible ASes: {can_participate}/{total}")
    
    for result in eligibility_summary:
        status_icon = "✅" if result['can_participate'] else "❌"
        trust = result['trust_score']
        stake = result['current_stake']
        required = result['required_stake']
        
        print(f"{status_icon} AS{result['as_number']:02d}: Trust={trust:2.0f}, Stake={stake:.3f}/{required:.3f} ETH")
    
    # Simulate BGP announcements
    print(f"\n📡 Simulating BGP Announcements:")
    print("-" * 40)
    
    # Test announcements from different AS types
    test_announcements = [
        {'as_number': 1, 'prefix': '192.0.2.0/24', 'description': 'RPKI-valid AS (should pass)'},
        {'as_number': 2, 'prefix': '203.0.113.0/24', 'description': 'Non-RPKI AS (good behavior)'},
        {'as_number': 4, 'prefix': '192.0.2.0/24', 'description': 'Non-RPKI AS (prefix hijack attempt)'},
        {'as_number': 6, 'prefix': '203.0.113.128/25', 'description': 'Non-RPKI AS (subprefix hijack)'},
        {'as_number': 8, 'prefix': '10.0.0.0/8', 'description': 'Non-RPKI AS (route leak)'}
    ]
    
    results = []
    
    for announcement in test_announcements:
        print(f"\n🔍 Testing: AS{announcement['as_number']:02d} announces {announcement['prefix']}")
        print(f"   Scenario: {announcement['description']}")
        
        # Check RPKI status
        if is_as_verified(announcement['as_number']):
            print(f"   ✅ RPKI-valid AS → Automatically approved")
            results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'RPKI valid'})
            continue
        
        # Check economic eligibility
        eligibility = staking_checker.check_participation_eligibility(announcement['as_number'])
        
        if not eligibility['can_participate']:
            print(f"   ❌ Economic eligibility failed: {eligibility['reason']}")
            print(f"   💰 Needs {eligibility['stake_deficit']:.3f} more ETH")
            results.append({'as': announcement['as_number'], 'result': 'rejected', 'reason': 'insufficient stake'})
            continue
        
        print(f"   ✅ Economic eligibility passed: {eligibility['current_stake']:.3f} ETH staked")
        
        # Attack detection
        detection_result = analyzer.analyze_announcement(announcement)
        
        if detection_result['legitimate']:
            print(f"   ✅ Attack detection: Clean announcement")
            results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'clean'})
        else:
            attacks = detection_result['attacks_detected']
            print(f"   🚨 Attack detection: {len(attacks)} attack(s) detected")
            for attack in attacks:
                print(f"      - {attack.get('type', 'unknown')} attack")
            results.append({'as': announcement['as_number'], 'result': 'rejected', 'reason': 'attack detected'})
    
    # Simulation summary
    print(f"\n" + "=" * 60)
    print(f"📋 SIMULATION SUMMARY")
    print(f"=" * 60)
    
    approved = sum(1 for r in results if r['result'] == 'approved')
    rejected = sum(1 for r in results if r['result'] == 'rejected')
    
    print(f"📊 Results: {approved} approved, {rejected} rejected out of {len(results)} announcements")
    
    print(f"\n📈 Detailed Results:")
    for result in results:
        status_icon = "✅" if result['result'] == 'approved' else "❌"
        print(f"   {status_icon} AS{result['as']:02d}: {result['result'].upper()} ({result['reason']})")
    
    print(f"\n🎯 Key Insights:")
    print(f"   • RPKI-valid ASes: Automatically trusted")
    print(f"   • Non-RPKI ASes: Subject to economic + behavioral validation")
    print(f"   • Attack detection: {len([r for r in results if r['reason'] == 'attack detected'])} attacks prevented")
    print(f"   • Economic security: {len([r for r in results if r['reason'] == 'insufficient stake'])} ASes blocked for insufficient stakes")
    
    print(f"\n🎉 Simulation Complete!")
    print(f"=" * 60)

if __name__ == "__main__":
    run_full_simulation()
