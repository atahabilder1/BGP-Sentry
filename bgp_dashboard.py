#!/usr/bin/env python3
"""
BGP-Sentry Dashboard - Real-time results viewer
"""

import json
import csv
import os
from datetime import datetime

def display_dashboard():
    print("🎯 BGP-SENTRY LIVE DASHBOARD")
    print("="*60)
    
    # Check available result files
    result_files = []
    if os.path.exists('results/odd_nodes_detections.csv'):
        result_files.append('odd_nodes_detections.csv')
    if os.path.exists('results/enhanced_detections.csv'):
        result_files.append('enhanced_detections.csv')
    
    for file in result_files:
        print(f"\n📊 Analysis: {file}")
        analyze_results(f'results/{file}')
    
    # Show service status
    print(f"\n🔧 SERVICE STATUS:")
    services = ['bgp_attack_detection', 'rpki_verification_interface', 
               'trust_score_interface', 'staking_amount_interface', 'shared_blockchain_stack']
    
    for service in services:
        path = f'nodes/rpki_nodes/{service}'
        status = "✅ ACTIVE" if os.path.exists(path) else "❌ INACTIVE"
        print(f"   {service}: {status}")

def analyze_results(csv_file):
    """Analyze BGP detection results"""
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        if not data:
            print("   ⚠️ No data found")
            return
        
        # Calculate statistics
        total = len(data)
        attacks = sum(1 for row in data if row['Is_Attack'] == 'Yes')
        legitimate = total - attacks
        
        # ASN statistics
        asn_stats = {}
        attack_types = {}
        
        for row in data:
            asn = row['Observer_ASN']
            if asn not in asn_stats:
                asn_stats[asn] = {'total': 0, 'attacks': 0}
            
            asn_stats[asn]['total'] += 1
            if row['Is_Attack'] == 'Yes':
                asn_stats[asn]['attacks'] += 1
                attack_type = row['Attack_Type']
                attack_types[attack_type] = attack_types.get(attack_type, 0) + 1
        
        # Display results
        print(f"   📈 Total Events: {total}")
        print(f"   🚨 Attacks: {attacks} ({attacks/total*100:.1f}%)")
        print(f"   ✅ Legitimate: {legitimate} ({legitimate/total*100:.1f}%)")
        
        print(f"   \n   🏢 Top Affected ASNs:")
        sorted_asns = sorted(asn_stats.items(), key=lambda x: x[1]['attacks'], reverse=True)
        for asn, stats in sorted_asns[:5]:
            rate = stats['attacks']/stats['total']*100 if stats['total'] > 0 else 0
            print(f"      AS{asn}: {stats['attacks']}/{stats['total']} attacks ({rate:.1f}%)")
        
        if attack_types:
            print(f"   \n   ⚔️ Attack Types:")
            for attack_type, count in sorted(attack_types.items(), key=lambda x: x[1], reverse=True):
                print(f"      {attack_type}: {count} incidents")
        
    except Exception as e:
        print(f"   ❌ Analysis error: {e}")

if __name__ == "__main__":
    display_dashboard()
