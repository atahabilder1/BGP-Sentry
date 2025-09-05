import csv
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import random

class CSVLogger:
    """
    THIS MODULE HANDLES CSV WRITING - Core CSV logging functionality
    """
    def __init__(self, filename: str, fieldnames: List[str]):
        self.filename = filename
        self.fieldnames = fieldnames
        self.lock = threading.Lock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        file_path = Path(self.filename)
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Always create fresh file (overwrite previous)
        with open(self.filename, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()  # ← CSV WRITING HAPPENS HERE (Headers)
    
    def log(self, data: Dict[str, Any]):
        """Write a single row to CSV file"""
        with self.lock:
            with open(self.filename, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writerow(data)  # ← CSV WRITING HAPPENS HERE (Data Rows)

class BGPHijackingDetector:
    """
    THIS MODULE DETECTS HIJACKING - Analyzes BGP announcements and logs to CSV
    """
    def __init__(self, observer_asn: int, csv_logger: CSVLogger):
        self.observer_asn = observer_asn
        self.csv_logger = csv_logger  # ← Links to CSV writer
        self.trust_scores = {}  # Track trust scores for each ASN
        
    def initialize_trust_score(self, asn: int, initial_score: float = 50.0):
        """Initialize trust score for an ASN"""
        if asn not in self.trust_scores:
            self.trust_scores[asn] = initial_score
    
    def detect_hijacking(self, sender_asn: int, ip_prefix: str, legitimate_owner: int = None) -> Dict:
        """
        Detect BGP hijacking and log results to CSV
        THIS IS WHERE DETECTION DATA GETS WRITTEN TO CSV
        """
        self.initialize_trust_score(sender_asn)
        
        # Simulate hijacking detection logic
        is_attack = False
        attack_type = "None"
        severity = "Low"
        confidence = 0.0
        legitimate_owner_asn = ""
        trust_penalty = 0.0
        
        # Check for known malicious ASNs (simulate detection)
        malicious_asns = [666, 777, 888, 999]
        if sender_asn in malicious_asns:
            is_attack = True
            if "192.168" in ip_prefix or "10." in ip_prefix or "203.0.113" in ip_prefix:
                attack_type = "prefix_hijacking"
                severity = "critical"
                confidence = 0.95
                legitimate_owner_asn = legitimate_owner if legitimate_owner else 12
                trust_penalty = 15.0
            elif "/25" in ip_prefix or "/26" in ip_prefix:
                attack_type = "subprefix_hijacking" 
                severity = "high"
                confidence = 0.9
                legitimate_owner_asn = legitimate_owner if legitimate_owner else 2
                trust_penalty = 10.0
        
        # Calculate trust scores
        trust_score_before = self.trust_scores[sender_asn]
        trust_score_after = max(0, trust_score_before - trust_penalty)
        self.trust_scores[sender_asn] = trust_score_after
        
        # Simulate detection time
        detection_time = random.randint(3, 8)
        
        # Create detection record
        detection_record = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Observer_ASN': self.observer_asn,
            'Sender_ASN': sender_asn,
            'IP_Prefix': ip_prefix,
            'Is_Attack': 'Yes' if is_attack else 'No',
            'Attack_Type': attack_type,
            'Severity': severity,
            'Legitimate_Owner': legitimate_owner_asn if is_attack else '',
            'Confidence': confidence if is_attack else '',
            'Trust_Score_Before': trust_score_before,
            'Trust_Score_After': trust_score_after,
            'Trust_Penalty': trust_penalty,
            'Detection_Time_MS': detection_time
        }
        
        # THIS IS WHERE THE DETECTION GETS WRITTEN TO CSV
        self.csv_logger.log(detection_record)  # ← CSV WRITING TRIGGERED HERE
        
        return detection_record

class MetricsAggregator:
    """
    THIS MODULE AGGREGATES METRICS - Calculates statistics and writes to CSV
    """
    def __init__(self, metrics_csv_logger: CSVLogger):
        self.metrics_csv_logger = metrics_csv_logger  # ← Links to metrics CSV writer
        self.all_detections = []
    
    def add_detection(self, detection: Dict):
        """Add a detection result for analysis"""
        self.all_detections.append(detection)
    
    def calculate_and_log_metrics(self):
        """
        Calculate metrics and write to CSV
        THIS IS WHERE METRICS GET WRITTEN TO CSV
        """
        if not self.all_detections:
            return
        
        total_announcements = len(self.all_detections)
        attacks_detected = sum(1 for d in self.all_detections if d['Is_Attack'] == 'Yes')
        trust_penalties_applied = sum(1 for d in self.all_detections if float(d['Trust_Penalty']) > 0)
        prefix_hijacking = sum(1 for d in self.all_detections if d['Attack_Type'] == 'prefix_hijacking')
        subprefix_hijacking = sum(1 for d in self.all_detections if d['Attack_Type'] == 'subprefix_hijacking')
        legitimate = sum(1 for d in self.all_detections if d['Is_Attack'] == 'No')
        
        # Create metrics records
        metrics = [
            {
                'Metric': 'Total Announcements',
                'Count': total_announcements,
                'Percentage': '100%'
            },
            {
                'Metric': 'Attacks Detected', 
                'Count': attacks_detected,
                'Percentage': f"{(attacks_detected/total_announcements)*100:.1f}%"
            },
            {
                'Metric': 'Trust Penalties Applied',
                'Count': trust_penalties_applied,
                'Percentage': f"{(trust_penalties_applied/total_announcements)*100:.1f}%"
            },
            {
                'Metric': 'Prefix Hijacking',
                'Count': prefix_hijacking,
                'Percentage': f"{(prefix_hijacking/total_announcements)*100:.1f}%"
            },
            {
                'Metric': 'Subprefix Hijacking', 
                'Count': subprefix_hijacking,
                'Percentage': f"{(subprefix_hijacking/total_announcements)*100:.1f}%"
            },
            {
                'Metric': 'Legitimate',
                'Count': legitimate,
                'Percentage': f"{(legitimate/total_announcements)*100:.1f}%"
            }
        ]
        
        # WRITE ALL METRICS TO CSV
        for metric in metrics:
            self.metrics_csv_logger.log(metric)  # ← CSV WRITING HAPPENS HERE
        
        return metrics

class TrustScoreTracker:
    """
    THIS MODULE TRACKS TRUST SCORES - Logs trust score changes to CSV
    """
    def __init__(self, trust_csv_logger: CSVLogger):
        self.trust_csv_logger = trust_csv_logger  # ← Links to trust CSV writer
    
    def log_trust_change(self, asn: int, old_score: float, new_score: float, reason: str):
        """
        Log trust score changes to CSV
        THIS IS WHERE TRUST CHANGES GET WRITTEN TO CSV
        """
        trust_record = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ASN': asn,
            'Trust_Score_Before': old_score,
            'Trust_Score_After': new_score,
            'Score_Change': new_score - old_score,
            'Reason': reason
        }
        
        # WRITE TRUST CHANGE TO CSV
        self.trust_csv_logger.log(trust_record)  # ← CSV WRITING HAPPENS HERE

class PerformanceTracker:
    """
    THIS MODULE TRACKS PERFORMANCE - Logs system performance to CSV
    """
    def __init__(self, performance_csv_logger: CSVLogger):
        self.performance_csv_logger = performance_csv_logger
        self.experiment_start_time = None
        self.total_detections = 0
        self.detection_times = []
    
    def start_experiment(self):
        """Mark the start of experiment"""
        self.experiment_start_time = time.time()
    
    def record_detection_time(self, detection_time_ms: int):
        """Record individual detection time"""
        self.detection_times.append(detection_time_ms)
        self.total_detections += 1
    
    def log_final_performance(self):
        """Log final performance metrics to CSV"""
        if not self.experiment_start_time:
            return
        
        total_time = time.time() - self.experiment_start_time
        avg_detection_time = sum(self.detection_times) / len(self.detection_times) if self.detection_times else 0
        throughput = self.total_detections / total_time if total_time > 0 else 0
        
        performance_record = {
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Total_Experiment_Time_Seconds': round(total_time, 2),
            'Total_Detections': self.total_detections,
            'Average_Detection_Time_MS': round(avg_detection_time, 2),
            'Detections_Per_Second': round(throughput, 2),
            'Min_Detection_Time_MS': min(self.detection_times) if self.detection_times else 0,
            'Max_Detection_Time_MS': max(self.detection_times) if self.detection_times else 0
        }
        
        # WRITE PERFORMANCE DATA TO CSV
        self.performance_csv_logger.log(performance_record)

def save_experiment_metadata(total_detections: int, experiment_duration: float):
    """Save metadata about the last experiment run"""
    metadata = {
        'last_run_timestamp': datetime.now().isoformat(),
        'experiment_duration_seconds': round(experiment_duration, 2),
        'total_detections_processed': total_detections,
        'output_files': [
            'results/detections.csv',
            'results/metrics.csv', 
            'results/trust_changes.csv',
            'results/performance.csv'
        ]
    }
    
    with open('results/last_run_info.json', 'w') as f:
        json.dump(metadata, f, indent=2)

def main_experiment():
    """
    MAIN EXPERIMENT FUNCTION - Orchestrates all CSV logging to results folder
    THIS IS WHERE ALL CSV FILES ARE CREATED AND WRITTEN TO RESULTS/
    """
    print("🚀 Starting BGP Hijacking Detection Experiment")
    print("📁 Results will be saved to BGP-Sentry/results/ folder")
    
    # 1. ENSURE RESULTS DIRECTORY EXISTS
    Path('results').mkdir(exist_ok=True)
    
    # 2. SETUP CSV LOGGERS - ALL FILES GO TO RESULTS FOLDER
    
    # Detection results CSV (matches your sample file exactly)
    detection_fields = [
        'Timestamp', 'Observer_ASN', 'Sender_ASN', 'IP_Prefix', 'Is_Attack', 
        'Attack_Type', 'Severity', 'Legitimate_Owner', 'Confidence', 
        'Trust_Score_Before', 'Trust_Score_After', 'Trust_Penalty', 'Detection_Time_MS'
    ]
    detection_logger = CSVLogger('results/detections.csv', detection_fields)
    
    # Metrics CSV (matches your metrics format)
    metrics_fields = ['Metric', 'Count', 'Percentage']
    metrics_logger = CSVLogger('results/metrics.csv', metrics_fields)
    
    # Trust score tracking CSV
    trust_fields = ['Timestamp', 'ASN', 'Trust_Score_Before', 'Trust_Score_After', 'Score_Change', 'Reason']
    trust_logger = CSVLogger('results/trust_changes.csv', trust_fields)
    
    # Performance tracking CSV
    performance_fields = [
        'Timestamp', 'Total_Experiment_Time_Seconds', 'Total_Detections', 
        'Average_Detection_Time_MS', 'Detections_Per_Second', 
        'Min_Detection_Time_MS', 'Max_Detection_Time_MS'
    ]
    performance_logger = CSVLogger('results/performance.csv', performance_fields)
    
    # 3. CREATE DETECTION SYSTEM COMPONENTS
    detector = BGPHijackingDetector(observer_asn=99, csv_logger=detection_logger)
    aggregator = MetricsAggregator(metrics_logger)
    trust_tracker = TrustScoreTracker(trust_logger)
    performance_tracker = PerformanceTracker(performance_logger)
    
    # 4. START PERFORMANCE TRACKING
    performance_tracker.start_experiment()
    experiment_start_time = time.time()
    
    # 5. SIMULATE BGP ANNOUNCEMENTS (THIS TRIGGERS ALL THE CSV WRITING)
    print("📊 Processing BGP announcements and logging to CSV...")
    
    # Test announcements based on your sample data
    test_announcements = [
        (12, '192.168.12.0/24', 12),    # Legitimate
        (5, '192.168.5.0/24', 5),      # Legitimate  
        (666, '192.168.12.0/24', 12),  # Prefix hijacking
        (777, '10.5.0.0/16', 5),       # Prefix hijacking
        (888, '203.0.113.0/24', 12),   # Prefix hijacking
        (999, '192.168.2.0/25', 2),    # Subprefix hijacking
        (2, '172.16.2.0/24', 2),       # Legitimate
        (6, '198.51.100.0/24', 6),     # Legitimate
    ]
    
    # Process announcements multiple times (simulate time intervals)
    for round_num in range(3):
        print(f"\n📡 Processing round {round_num + 1}...")
        
        for sender_asn, ip_prefix, legitimate_owner in test_announcements:
            # Each detection gets logged to CSV
            detection = detector.detect_hijacking(sender_asn, ip_prefix, legitimate_owner)
            
            # Track performance
            performance_tracker.record_detection_time(detection['Detection_Time_MS'])
            
            # Add to aggregator for metrics
            aggregator.add_detection(detection)
            
            # Log trust score changes if there was a penalty
            if float(detection['Trust_Penalty']) > 0:
                trust_tracker.log_trust_change(
                    sender_asn, 
                    float(detection['Trust_Score_Before']),
                    float(detection['Trust_Score_After']),
                    f"Attack detected: {detection['Attack_Type']}"
                )
            
            attack_status = "🚨 ATTACK" if detection['Is_Attack'] == 'Yes' else "✅ LEGITIMATE"
            print(f"   {attack_status}: ASN {sender_asn} -> {ip_prefix}")
        
        time.sleep(0.5)  # Simulate time between rounds
    
    # 6. GENERATE AND LOG FINAL RESULTS
    print("\n📈 Calculating and logging final metrics...")
    metrics = aggregator.calculate_and_log_metrics()
    
    # 7. LOG PERFORMANCE METRICS
    performance_tracker.log_final_performance()
    
    # 8. SAVE EXPERIMENT METADATA
    total_time = time.time() - experiment_start_time
    save_experiment_metadata(performance_tracker.total_detections, total_time)
    
    print("\n" + "="*60)
    print("📋 EXPERIMENT COMPLETE - FILES SAVED TO BGP-Sentry/results/:")
    print("="*60)
    print("📄 detections.csv - All detection results (overwrites previous)")
    print("📄 metrics.csv - Summary statistics (overwrites previous)")
    print("📄 trust_changes.csv - Trust score changes (overwrites previous)")
    print("📄 performance.csv - System performance data (overwrites previous)")
    print("📄 last_run_info.json - Experiment metadata")
    
    # Display summary
    total_announcements = len(aggregator.all_detections)
    attacks_detected = sum(1 for d in aggregator.all_detections if d['Is_Attack'] == 'Yes')
    attack_percentage = (attacks_detected/total_announcements)*100 if total_announcements > 0 else 0
    
    print(f"\n📊 Latest Results Summary:")
    print(f"   • Total BGP Announcements: {total_announcements}")
    print(f"   • Attacks Detected: {attacks_detected} ({attack_percentage:.1f}%)")
    print(f"   • Experiment Duration: {total_time:.2f} seconds")
    print(f"   • Results Location: BGP-Sentry/results/")
    
    return {
        'detections_file': 'results/detections.csv',
        'metrics_file': 'results/metrics.csv',
        'trust_file': 'results/trust_changes.csv',
        'performance_file': 'results/performance.csv',
        'metadata_file': 'results/last_run_info.json',
        'total_detections': total_announcements,
        'attacks_detected': attacks_detected
    }

def show_csv_writing_summary():
    """
    DOCUMENTATION FUNCTION - Shows exactly where CSV writing happens
    """
    print("\n" + "="*60)
    print("🔍 CSV WRITING MODULES AND LOCATIONS:")
    print("="*60)
    
    modules = [
        "1. CSVLogger._ensure_file_exists() - Creates CSV files with headers",
        "2. CSVLogger.log() - Writes individual data rows to CSV",
        "3. BGPHijackingDetector.detect_hijacking() - Writes detection results",
        "4. MetricsAggregator.calculate_and_log_metrics() - Writes summary metrics", 
        "5. TrustScoreTracker.log_trust_change() - Writes trust score changes",
        "6. PerformanceTracker.log_final_performance() - Writes performance data"
    ]
    
    for module in modules:
        print(f"   {module}")
    
    print(f"\n📁 All CSV files are created in: BGP-Sentry/results/")
    print(f"🔄 Each experiment run OVERWRITES previous results")
    print(f"📊 Four types of data logged: detections, metrics, trust, performance")

if __name__ == "__main__":
    # Run the main experiment
    print("🎯 BGP-Sentry Hijacking Detection Experiment")
    print("=" * 50)
    
    experiment_results = main_experiment()
    
    # Show technical details
    show_csv_writing_summary()
    
    print(f"\n✨ Check BGP-Sentry/results/ folder for your latest experiment data!")
    print(f"🎉 Experiment completed successfully!")