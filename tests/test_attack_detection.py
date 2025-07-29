#!/usr/bin/env python3
"""
Simple Attack Detection Test for Excel Analysis
"""

import sys
import os
sys.path.append('../utils_common')
sys.path.append('../services/rpki_observer_service')

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from simple_attack_logger import SimpleAttackLogger

def mock_attack_detection(announcement):
    """Mock attack detection for testing (replace with real detection later)"""
    
    sender_asn = announcement['sender_asn']
    ip_prefix = announcement['ip_prefix']
    
    # Simple mock detection logic
    detection_results = {
        'legitimate': True,
        'attacks_detected': [],
        'severity': 'low'
    }
    
    # Mock prefix hijacking detection
    known_prefixes = {
        "192.168.12.0/24": 12,
        "10.5.0.0/16": 5,
        "203.0.113.0/24": 12,
        "192.168.2.0/24": 2,
        "10.1.0.0/16": 1,
        "192.168.5.0/24": 5,
        "233.252.0.0/24": 18,
        "172.16.2.0/24": 2,
        "198.51.100.0/24": 6
    }
    
    if ip_prefix in known_prefixes:
        legitimate_owner = known_prefixes[ip_prefix]
        if sender_asn != legitimate_owner:
            # Prefix hijacking detected
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
    
    # Mock subprefix hijacking detection (simple check for /25 in /24)
    if '/25' in ip_prefix:
        parent_prefix = ip_prefix.replace('/25', '/24')
        if parent_prefix in known_prefixes:
            legitimate_owner = known_prefixes[parent_prefix]
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
                if detection_results['severity'] != 'critical':
                    detection_results['severity'] = 'high'
    
    return detection_results

def run_attack_tests():
    """Run various attack scenarios for testing"""
    
    print("🔍 Running BGP Attack Detection Tests for Excel Analysis...")
    
    # Initialize simple logger
    logger = SimpleAttackLogger()
    
    # Test scenarios
    scenarios = [
        # Legitimate announcements
        {"sender_asn": 12, "ip_prefix": "192.168.12.0/24", "desc": "Legitimate AS12"},
        {"sender_asn": 5, "ip_prefix": "192.168.5.0/24", "desc": "Legitimate RPKI AS5"},
        {"sender_asn": 18, "ip_prefix": "233.252.0.0/24", "desc": "Legitimate AS18"},
        {"sender_asn": 2, "ip_prefix": "172.16.2.0/24", "desc": "Legitimate AS2"},
        {"sender_asn": 6, "ip_prefix": "198.51.100.0/24", "desc": "Legitimate AS6"},
        
        # Prefix hijacking attacks
        {"sender_asn": 666, "ip_prefix": "192.168.12.0/24", "desc": "Hijack AS12 prefix"},
        {"sender_asn": 777, "ip_prefix": "10.5.0.0/16", "desc": "Hijack RPKI AS5 prefix"},
        {"sender_asn": 888, "ip_prefix": "203.0.113.0/24", "desc": "Hijack content prefix"},
        
        # Subprefix hijacking attacks
        {"sender_asn": 999, "ip_prefix": "192.168.2.0/25", "desc": "Subhijack AS2"},
        {"sender_asn": 1001, "ip_prefix": "10.1.1.0/24", "desc": "Subhijack RPKI AS1"},
        
        # More legitimate for balance
        {"sender_asn": 12, "ip_prefix": "203.0.113.0/24", "desc": "Legitimate AS12 content"},
        {"sender_asn": 1, "ip_prefix": "10.1.0.0/16", "desc": "Legitimate RPKI AS1"},
    ]
    
    for i, scenario in enumerate(scenarios):
        print(f"Testing {i+1}/{len(scenarios)}: {scenario['desc']}")
        
        # Create announcement
        announcement = {
            "sender_asn": scenario["sender_asn"],
            "ip_prefix": scenario["ip_prefix"],
            "timestamp": f"2025-07-28T{i:02d}:00:00Z"
        }
        
        # Process announcement with mock detection
        detection_results = mock_attack_detection(announcement)
        
        # Log result
        logger.log_detection_result(announcement, detection_results, observer_asn=99)
        
        if detection_results['legitimate']:
            print(f"  ✅ Legitimate announcement")
        else:
            attacks = detection_results['attacks_detected']
            print(f"  🚨 {len(attacks)} attack(s) detected:")
            for attack in attacks:
                print(f"    - {attack['attack_type']} (severity: {attack['severity']})")
    
    # Generate Excel summary
    summary_file = logger.generate_excel_summary()
    stats = logger.get_summary_stats()
    
    print(f"\n📊 TEST COMPLETED!")
    print(f"Total Announcements: {stats['total_announcements']}")
    print(f"Attacks Detected: {stats['attacks_detected']}")
    print(f"Attack Rate: {stats['attack_rate']:.1f}%")
    print(f"Prefix Hijacking: {stats['prefix_hijacking']}")
    print(f"Subprefix Hijacking: {stats['subprefix_hijacking']}")
    print(f"Legitimate: {stats['legitimate']}")
    
    return logger.log_dir

if __name__ == "__main__":
    log_dir = run_attack_tests()
    print(f"\n�� CSV files created in: {log_dir}")
