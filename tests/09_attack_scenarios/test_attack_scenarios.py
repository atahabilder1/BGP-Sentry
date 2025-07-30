#!/usr/bin/env python3
"""
BGP Attack Scenario Tests
"""

import sys
from pathlib import Path

# Add interface paths
base_path = Path(__file__).parent.parent.parent
interfaces = [
    'nodes/rpki_nodes/bgp_attack_detection',
    'nodes/rpki_nodes/rpki_verification_interface'
]

for interface in interfaces:
    sys.path.insert(0, str(base_path / interface))

def test_prefix_hijacking():
    """Test prefix hijacking detection"""
    print("🚨 Testing Prefix Hijacking...")
    
    from attack_detector import BGPSecurityAnalyzer
    analyzer = BGPSecurityAnalyzer()
    
    hijack_announcement = {
        'as_number': 4,
        'prefix': '192.0.2.0/24',
        'timestamp': '2025-07-30T12:00:00Z'
    }
    
    result = analyzer.analyze_announcement(hijack_announcement)
    success = not result['legitimate']
    
    if success:
        print("   ✅ Prefix hijacking detected successfully")
        attacks = result['attacks_detected']
        for attack in attacks:
            print(f"      - {attack.get('type', 'unknown')} attack detected")
    else:
        print("   ❌ Failed to detect prefix hijacking")
    
    return success

def test_subprefix_hijacking():
    """Test subprefix hijacking detection"""
    print("🚨 Testing Subprefix Hijacking...")
    
    from attack_detector import BGPSecurityAnalyzer
    analyzer = BGPSecurityAnalyzer()
    
    subprefix_announcement = {
        'as_number': 6,
        'prefix': '203.0.113.128/25',
        'timestamp': '2025-07-30T12:00:00Z'
    }
    
    result = analyzer.analyze_announcement(subprefix_announcement)
    success = not result['legitimate']
    
    if success:
        print("   ✅ Subprefix hijacking detected successfully")
        attacks = result['attacks_detected']
        for attack in attacks:
            print(f"      - {attack.get('type', 'unknown')} attack detected")
    else:
        print("   ❌ Failed to detect subprefix hijacking")
    
    return success

def test_route_leak():
    """Test route leak detection"""
    print("🚨 Testing Route Leak...")
    
    from attack_detector import BGPSecurityAnalyzer
    analyzer = BGPSecurityAnalyzer()
    
    route_leak_announcement = {
        'as_number': 8,
        'prefix': '10.0.0.0/8',
        'timestamp': '2025-07-30T12:00:00Z'
    }
    
    result = analyzer.analyze_announcement(route_leak_announcement)
    success = not result['legitimate']
    
    if success:
        print("   ✅ Route leak detected successfully")
        attacks = result['attacks_detected']
        for attack in attacks:
            print(f"      - {attack.get('type', 'unknown')} attack detected")
    else:
        print("   ❌ Failed to detect route leak")
    
    return success

if __name__ == "__main__":
    print("🧪 BGP Attack Scenario Tests")
    print("=" * 40)
    
    tests = [
        test_prefix_hijacking, 
        test_subprefix_hijacking,
        test_route_leak
    ]
    
    passed = 0
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{len(tests)} attack scenarios detected correctly")
    
    if passed == len(tests):
        print("🎉 All attack detection scenarios passed!")
    else:
        print("⚠️  Some attack scenarios need attention")
