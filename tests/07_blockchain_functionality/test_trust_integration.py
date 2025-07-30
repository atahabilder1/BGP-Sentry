#!/usr/bin/env python3
"""
Test Attack Detection with Trust Integration
"""

import sys
sys.path.append('../utils_common')

from enhanced_attack_logger import EnhancedAttackLogger

def mock_detection(announcement):
    """Mock attack detection function"""
    sender_asn = announcement['sender_asn']
    ip_prefix = announcement['ip_prefix']
    
    legitimate_prefixes = {
        "192.168.12.0/24": 12, "10.5.0.0/16": 5, "203.0.113.0/24": 12,
        "192.168.2.0/24": 2, "172.16.2.0/24": 2, "198.51.100.0/24": 6,
        "192.168.5.0/24": 5
    }
    
    detection_results = {'legitimate': True, 'attacks_detected': [], 'severity': 'low'}
    
    # Check for prefix hijacking
    if ip_prefix in legitimate_prefixes:
        legitimate_owner = legitimate_prefixes[ip_prefix]
        if sender_asn != legitimate_owner:
            detection_results['legitimate'] = False
            detection_results['attacks_detected'].append({
                'attack_type': 'prefix_hijacking',
                'hijacker_asn': sender_asn,
                'legitimate_owner': legitimate_owner,
                'hijacked_prefix': ip_prefix,
                'severity': 'critical',
                'confidence': 0.95
            })
            detection_results['severity'] = 'critical'
    
    # Check for subprefix hijacking
    if '/25' in ip_prefix:
        parent_prefix = ip_prefix.replace('/25', '/24')
        if parent_prefix in legitimate_prefixes:
            legitimate_owner = legitimate_prefixes[parent_prefix]
            if sender_asn != legitimate_owner:
                detection_results['legitimate'] = False
                detection_results['attacks_detected'].append({
                    'attack_type': 'subprefix_hijacking',
                    'hijacker_asn': sender_asn,
                    'legitimate_owner': legitimate_owner,
                    'hijacked_subprefix': ip_prefix,
                    'parent_prefix': parent_prefix,
                    'severity': 'high',
                    'confidence': 0.90
                })
    
    return detection_results

def test_trust_integration():
    """Test complete system with trust integration"""
    
    print("🔗 Testing Attack Detection + Trust Score Integration...")
    
    # Initialize enhanced logger
    logger = EnhancedAttackLogger()
    
    # Test scenarios
    scenarios = [
        # Legitimate (no penalties)
        {"sender_asn": 12, "ip_prefix": "192.168.12.0/24", "desc": "Legitimate AS12"},
        {"sender_asn": 5, "ip_prefix": "192.168.5.0/24", "desc": "Legitimate RPKI AS5"},
        
        # Attacks (should apply penalties)
        {"sender_asn": 666, "ip_prefix": "192.168.12.0/24", "desc": "AS666 hijacks AS12 prefix"},
        {"sender_asn": 777, "ip_prefix": "10.5.0.0/16", "desc": "AS777 hijacks RPKI AS5"},
        {"sender_asn": 888, "ip_prefix": "203.0.113.0/24", "desc": "AS888 hijacks content prefix"},
        {"sender_asn": 999, "ip_prefix": "192.168.2.0/25", "desc": "AS999 subhijacks AS2"},
        
        # More legitimate
        {"sender_asn": 2, "ip_prefix": "172.16.2.0/24", "desc": "Legitimate AS2"},
        {"sender_asn": 6, "ip_prefix": "198.51.100.0/24", "desc": "Legitimate AS6"},
    ]
    
    # Process each scenario
    for i, scenario in enumerate(scenarios):
        print(f"\n💡 Testing {i+1}/{len(scenarios)}: {scenario['desc']}")
        
        # Show trust before
        if logger.trust_manager:
            trust_before = logger.trust_manager.get_trust_score(scenario['sender_asn'])
            print(f"   Trust score before: {trust_before:.2f}")
        
        # Create announcement
        announcement = {
            "sender_asn": scenario["sender_asn"],
            "ip_prefix": scenario["ip_prefix"],
            "timestamp": f"2025-07-28T{i:02d}:30:00Z"
        }
        
        # Run detection
        detection_result = mock_detection(announcement)
        
        # Log with trust integration
        logger.log_detection_result(announcement, detection_result, observer_asn=99)
        
        # Show results
        if detection_result['legitimate']:
            print(f"   ✅ Legitimate - No penalty")
        else:
            attacks = detection_result['attacks_detected']
            print(f"   🚨 {len(attacks)} attack(s) detected:")
            for attack in attacks:
                print(f"     - {attack['attack_type']} (severity: {attack['severity']})")
        
        # Show trust after
        if logger.trust_manager:
            trust_after = logger.trust_manager.get_trust_score(scenario['sender_asn'])
            penalty = trust_before - trust_after if 'trust_before' in locals() else 0
            if penalty > 0:
                print(f"   📉 Trust penalty: -{penalty:.2f} (New score: {trust_after:.2f})")
    
    # Generate summary
    summary = logger.generate_enhanced_summary()
    stats = logger.get_summary_stats()
    
    print(f"\n📊 TRUST-INTEGRATED TEST COMPLETED!")
    print(f"Total Announcements: {stats['total_announcements']}")
    print(f"Attacks Detected: {stats['attacks_detected']}")
    print(f"Trust Penalties Applied: {stats['trust_penalties_applied']}")
    print(f"Attack Rate: {stats['attack_rate']:.1f}%")
    
    # Show final trust scores
    if logger.trust_manager:
        print(f"\n📈 Final Trust Scores:")
        trust_summary = logger.trust_manager.get_trust_summary()
        for as_num, score in trust_summary.items():
            print(f"   AS{as_num}: {score:.2f}")
    
    print(f"\n📁 Enhanced CSV file: ../shared_data/logs/attack_detection_with_trust.csv")

if __name__ == "__main__":
    test_trust_integration()
