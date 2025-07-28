#!/usr/bin/env python3
"""
Enhanced Attack Logger with Working Trust Integration
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

class EnhancedAttackLogger:
    """Enhanced logger with trust score integration"""
    
    def __init__(self, log_dir="../shared_data/logs/"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize trust manager
        try:
            from integrated_trust_manager import IntegratedTrustManager
            self.trust_manager = IntegratedTrustManager()
        except Exception as e:
            print(f"Warning: Could not import trust manager: {e}")
            self.trust_manager = None
        
        # CSV files
        self.detection_log = self.log_dir / "attack_detection_with_trust.csv"
        
        self._initialize_csv_files()
        
        # Counters
        self.counters = {
            'total_announcements': 0,
            'prefix_hijacking': 0,
            'subprefix_hijacking': 0,
            'route_leaks': 0,
            'legitimate': 0,
            'trust_penalties_applied': 0
        }
    
    def _initialize_csv_files(self):
        """Initialize CSV files with headers"""
        
        if not self.detection_log.exists():
            with open(self.detection_log, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Observer_ASN', 'Sender_ASN', 'IP_Prefix',
                    'Is_Attack', 'Attack_Type', 'Severity', 'Legitimate_Owner',
                    'Confidence', 'Trust_Score_Before', 'Trust_Score_After',
                    'Trust_Penalty', 'Detection_Time_MS'
                ])
    
    def log_detection_result(self, announcement, detection_results, observer_asn, detection_time_ms=5):
        """Enhanced logging with trust score integration"""
        
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        sender_asn = announcement.get('sender_asn', 'Unknown')
        ip_prefix = announcement.get('ip_prefix', 'Unknown')
        
        # Update counters
        self.counters['total_announcements'] += 1
        
        # Get trust score before processing
        trust_before = 50.0  # Default
        if self.trust_manager:
            trust_before = self.trust_manager.get_trust_score(sender_asn)
        
        # Process with trust manager (apply penalties)
        if self.trust_manager:
            self.trust_manager.process_attack_detection(announcement, detection_results, observer_asn)
        
        # Get trust score after processing
        trust_after = trust_before
        if self.trust_manager:
            trust_after = self.trust_manager.get_trust_score(sender_asn)
        
        trust_penalty = trust_before - trust_after
        
        if detection_results['legitimate']:
            self.counters['legitimate'] += 1
            # Log legitimate announcement
            with open(self.detection_log, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, observer_asn, sender_asn, ip_prefix,
                    'No', 'None', 'Low', '', '', 
                    trust_before, trust_after, 0, detection_time_ms
                ])
        else:
            # Log each attack detected
            for attack in detection_results['attacks_detected']:
                attack_type = attack.get('attack_type', 'Unknown')
                severity = attack.get('severity', 'Medium')
                legitimate_owner = attack.get('legitimate_owner', '')
                confidence = attack.get('confidence', 0.0)
                
                # Update attack type counters
                if attack_type == 'prefix_hijacking':
                    self.counters['prefix_hijacking'] += 1
                elif attack_type == 'subprefix_hijacking':
                    self.counters['subprefix_hijacking'] += 1
                elif attack_type == 'route_leak':
                    self.counters['route_leaks'] += 1
                
                if trust_penalty > 0:
                    self.counters['trust_penalties_applied'] += 1
                
                # Log attack with trust scores
                with open(self.detection_log, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        timestamp, observer_asn, sender_asn, ip_prefix,
                        'Yes', attack_type, severity, legitimate_owner,
                        confidence, trust_before, trust_after, trust_penalty, detection_time_ms
                    ])
    
    def get_summary_stats(self):
        """Get enhanced summary statistics"""
        total = self.counters['total_announcements']
        attacks = total - self.counters['legitimate']
        
        return {
            'total_announcements': total,
            'attacks_detected': attacks,
            'attack_rate': (attacks / total * 100) if total > 0 else 0,
            'prefix_hijacking': self.counters['prefix_hijacking'],
            'subprefix_hijacking': self.counters['subprefix_hijacking'],
            'route_leaks': self.counters['route_leaks'],
            'legitimate': self.counters['legitimate'],
            'trust_penalties_applied': self.counters['trust_penalties_applied']
        }
    
    def generate_enhanced_summary(self):
        """Generate enhanced summary with trust metrics"""
        stats = self.get_summary_stats()
        
        summary_file = self.log_dir / "enhanced_detection_summary.csv"
        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Count', 'Percentage'])
            writer.writerow(['Total Announcements', stats['total_announcements'], '100%'])
            writer.writerow(['Attacks Detected', stats['attacks_detected'], f"{stats['attack_rate']:.1f}%"])
            writer.writerow(['Trust Penalties Applied', stats['trust_penalties_applied'], f"{stats['trust_penalties_applied']/stats['total_announcements']*100:.1f}%" if stats['total_announcements'] > 0 else "0%"])
            writer.writerow(['Prefix Hijacking', stats['prefix_hijacking'], f"{stats['prefix_hijacking']/stats['total_announcements']*100:.1f}%" if stats['total_announcements'] > 0 else "0%"])
            writer.writerow(['Subprefix Hijacking', stats['subprefix_hijacking'], f"{stats['subprefix_hijacking']/stats['total_announcements']*100:.1f}%" if stats['total_announcements'] > 0 else "0%"])
            writer.writerow(['Legitimate', stats['legitimate'], f"{stats['legitimate']/stats['total_announcements']*100:.1f}%" if stats['total_announcements'] > 0 else "0%"])
        
        print(f"📊 Enhanced summary saved to: {summary_file}")
        return summary_file
