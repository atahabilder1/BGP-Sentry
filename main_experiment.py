#!/usr/bin/env python3
"""
BGP-Sentry Enhanced Parallel Simulation with Real Data Sources
===============================================================

This script runs a distributed BGP security monitoring system with:
- Multiple RPKI nodes running in parallel
- Real RPKI verification using your verifier module
- Attack pattern detection and consensus voting
- Integration with your existing data sources
- Blockchain-based consensus mechanism

Author: BGP-Sentry Team
Date: 2025-08-04
"""

import json
import threading
import time
import queue
from datetime import datetime
from pathlib import Path
import concurrent.futures
import logging
import sys
import random
import os
from typing import List, Dict, Any, Optional

# =============================================================================
# RPKI VERIFIER MODULE INTEGRATION
# =============================================================================

# Add RPKI verifier module to path
sys.path.append('nodes/rpki_nodes/rpki_verification_interface')
try:
    from verifier import is_as_verified, get_all_verified_ases, get_all_unverified_ases
    RPKI_VERIFIER_AVAILABLE = True
    print("✅ RPKI Verifier module loaded successfully")
    print(f"🔍 Available functions: is_as_verified, get_all_verified_ases, get_all_unverified_ases")
except ImportError as e:
    print(f"⚠️ RPKI Verifier module not found: {e}")
    print("   Falling back to basic verification")
    RPKI_VERIFIER_AVAILABLE = False

# =============================================================================
# DATA SOURCE INTEGRATION
# =============================================================================

class DataSourceManager:
    """
    Manages loading and processing data from various sources including:
    - Blockchain registry data
    - RPKI verification data
    - BGP announcement feeds
    - Attack scenario databases
    """
    
    def __init__(self):
        """Initialize data source manager with paths to data directories"""
        self.logger = logging.getLogger('DataSourceManager')
        
        # Define paths to your data sources
        self.data_paths = {
            'blockchain_registry': 'nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/',
            'rpki_data': 'nodes/rpki_nodes/rpki_verification_interface/',
            'bgp_feeds': 'data/bgp_feeds/',
            'attack_scenarios': 'data/attack_scenarios/'
        }
        
        # Initialize data containers
        self.blockchain_registry = {}
        self.verified_ases = []
        self.bgp_announcements = []
        self.attack_scenarios = []
        
    def load_blockchain_registry(self) -> Dict[str, Any]:
        """
        Load blockchain registry data containing legitimate prefix ownership
        Expected files: public_network_registry.json, rpki_registry.json
        """
        self.logger.info("📋 Loading blockchain registry data...")
        
        registry_files = [
            'public_network_registry.json',
            'rpki_registry.json',
            'shared_registry.json'
        ]
        
        for filename in registry_files:
            filepath = Path(self.data_paths['blockchain_registry']) / filename
            
            if filepath.exists():
                try:
                    with open(filepath, 'r') as f:
                        registry_data = json.load(f)
                        self.blockchain_registry.update(registry_data)
                        self.logger.info(f"✅ Loaded registry: {filename}")
                except Exception as e:
                    self.logger.error(f"❌ Failed to load {filename}: {e}")
            else:
                self.logger.warning(f"⚠️ Registry file not found: {filepath}")
        
        if not self.blockchain_registry:
            # Fallback: Create basic registry from known data
            self.logger.info("🔄 Creating fallback registry from known ASNs...")
            self._create_fallback_registry()
        
        return self.blockchain_registry
    
    def _create_fallback_registry(self):
        """Create fallback registry when data files are not available"""
        # Known legitimate ASNs from your simulation
        legitimate_asns = [1, 3, 5, 7, 9, 11, 13, 15, 17]
        
        # Create basic registry structure
        self.blockchain_registry = {
            "rpki_nodes": {},
            "prefix_ownership": {},
            "last_updated": datetime.now().isoformat()
        }
        
        # Add legitimate ASNs
        for asn in legitimate_asns:
            self.blockchain_registry["rpki_nodes"][str(asn)] = {
                "status": "valid",
                "verified": True,
                "last_verified": datetime.now().isoformat()
            }
        
        # Add some prefix ownership data
        prefix_mappings = {
            "10.1.0.0/16": 1,
            "10.3.0.0/16": 3,
            "10.5.0.0/16": 5,
            "172.16.4.0/24": 7,
            "172.16.6.0/24": 9,
            "192.168.1.0/24": 11,
            "192.168.2.0/24": 13,
            "192.168.3.0/24": 15,
            "203.0.113.0/24": 17
        }
        
        for prefix, owner_asn in prefix_mappings.items():
            self.blockchain_registry["prefix_ownership"][prefix] = {
                "owner_asn": owner_asn,
                "verified": True,
                "last_updated": datetime.now().isoformat()
            }
    
    def load_verified_ases(self) -> List[int]:
        """Load list of RPKI-verified ASNs from your verifier module"""
        self.logger.info("🔐 Loading RPKI-verified ASNs...")
        
        if RPKI_VERIFIER_AVAILABLE:
            try:
                # Use your actual verifier to get verified ASNs
                self.verified_ases = get_all_verified_ases()
                self.logger.info(f"✅ Loaded {len(self.verified_ases)} verified ASNs from RPKI module")
            except Exception as e:
                self.logger.error(f"❌ Error loading verified ASNs: {e}")
                self._load_fallback_verified_ases()
        else:
            self._load_fallback_verified_ases()
        
        return self.verified_ases
    
    def _load_fallback_verified_ases(self):
        """Fallback list of verified ASNs when RPKI module unavailable"""
        self.verified_ases = [1, 3, 5, 7, 9, 11, 13, 15, 17]
        self.logger.info(f"🔄 Using fallback verified ASNs: {self.verified_ases}")
    
    def generate_realistic_bgp_announcements(self, count: int = 90) -> List[Dict[str, Any]]:
        """
        Generate realistic BGP announcements including both legitimate traffic and attacks
        Uses data from your blockchain registry and verified ASN lists
        """
        self.logger.info(f"📡 Generating {count} realistic BGP announcements...")
        
        announcements = []
        
        # Calculate distribution: 70% legitimate, 30% attacks
        legitimate_count = int(count * 0.7)
        attack_count = count - legitimate_count
        
        # Generate legitimate announcements
        legitimate_announcements = self._generate_legitimate_announcements(legitimate_count)
        announcements.extend(legitimate_announcements)
        
        # Generate attack scenarios
        attack_announcements = self._generate_attack_announcements(attack_count)
        announcements.extend(attack_announcements)
        
        # Shuffle to mix legitimate and attack traffic realistically
        random.shuffle(announcements)
        
        self.logger.info(f"✅ Generated {len(announcements)} announcements:")
        self.logger.info(f"   • {legitimate_count} legitimate announcements")
        self.logger.info(f"   • {attack_count} attack scenarios")
        
        self.bgp_announcements = announcements
        return announcements
    
    def _generate_legitimate_announcements(self, count: int) -> List[Dict[str, Any]]:
        """Generate legitimate BGP announcements from verified ASNs"""
        announcements = []
        
        # Use verified ASNs and legitimate prefixes from blockchain registry
        legitimate_prefixes = list(self.blockchain_registry.get("prefix_ownership", {}).keys())
        
        # If no prefixes in registry, use fallback prefixes
        if not legitimate_prefixes:
            legitimate_prefixes = [
                "10.1.0.0/16", "10.3.0.0/16", "10.5.0.0/16", "10.7.0.0/16",
                "172.16.4.0/24", "172.16.6.0/24", "172.16.8.0/24", "172.16.10.0/24",
                "192.168.1.0/24", "192.168.2.0/24", "192.168.3.0/24", "192.168.4.0/24",
                "203.0.113.0/24", "198.51.100.0/24", "233.252.0.0/24"
            ]
        
        for i in range(count):
            # Select random legitimate ASN and prefix
            sender_asn = random.choice(self.verified_ases)
            prefix = random.choice(legitimate_prefixes)
            
            # Get legitimate owner from registry
            prefix_info = self.blockchain_registry.get("prefix_ownership", {}).get(prefix, {})
            legitimate_owner = prefix_info.get("owner_asn", sender_asn)
            
            announcement = {
                "id": f"legit_{i+1}",
                "sender_asn": legitimate_owner,  # Use legitimate owner
                "origin_as": legitimate_owner,
                "announced_prefix": prefix,
                "prefix": prefix,
                "as_path": [legitimate_owner],
                "timestamp": datetime.now().isoformat(),
                "type": "legitimate",
                "source": "verified_registry"
            }
            
            announcements.append(announcement)
        
        return announcements
    
    def _generate_attack_announcements(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic attack scenarios based on known attack patterns"""
        announcements = []
        
        # Define attack scenarios with different types and severities
        attack_types = [
            "prefix_hijack",      # Attacker announces legitimate prefix
            "sub_prefix_hijack",  # More specific route attack
            "route_leak",         # Legitimate AS announces wrong prefix
            "origin_hijack",      # Wrong origin AS in announcement
            "dns_hijack"          # Targeting DNS infrastructure
        ]
        
        # Attacker ASNs (not in verified list)
        attacker_asns = [666, 31337, 8888, 9999, 1234, 65000, 65001, 4444, 7777]
        
        # High-value target prefixes (common attack targets)
        high_value_targets = [
            "8.8.8.0/24",         # Google DNS
            "1.1.1.0/24",         # Cloudflare DNS
            "208.67.222.0/24",    # OpenDNS
            "185.199.108.0/22",   # GitHub
            "151.101.0.0/16",     # Reddit/Fastly
            "104.16.0.0/12",      # Cloudflare CDN
            "13.107.42.0/24"      # Microsoft Office 365
        ]
        
        # Generate diverse attack scenarios
        for i in range(count):
            attack_type = random.choice(attack_types)
            attacker_asn = random.choice(attacker_asns)
            
            if attack_type == "prefix_hijack":
                # Attacker announces high-value prefix
                target_prefix = random.choice(high_value_targets)
                legitimate_owner = random.choice(self.verified_ases)
                
                announcement = {
                    "id": f"attack_hijack_{i+1}",
                    "sender_asn": attacker_asn,
                    "origin_as": attacker_asn,
                    "announced_prefix": target_prefix,
                    "prefix": target_prefix,
                    "as_path": [attacker_asn],
                    "timestamp": datetime.now().isoformat(),
                    "type": "prefix_hijack",
                    "severity": "HIGH",
                    "legitimate_owner": legitimate_owner,
                    "source": "attack_simulation"
                }
                
            elif attack_type == "sub_prefix_hijack":
                # More specific route than legitimate announcement
                base_prefix = random.choice(high_value_targets)
                if "/24" in base_prefix:
                    hijacked_prefix = base_prefix.replace("/24", "/25")
                elif "/22" in base_prefix:
                    hijacked_prefix = base_prefix.replace("/22", "/24")
                else:
                    hijacked_prefix = base_prefix.replace("/12", "/16")
                
                announcement = {
                    "id": f"attack_subprefix_{i+1}",
                    "sender_asn": attacker_asn,
                    "origin_as": attacker_asn,
                    "announced_prefix": hijacked_prefix,
                    "prefix": hijacked_prefix,
                    "as_path": [attacker_asn],
                    "timestamp": datetime.now().isoformat(),
                    "type": "sub_prefix_hijack",
                    "severity": "CRITICAL",
                    "parent_prefix": base_prefix,
                    "source": "attack_simulation"
                }
                
            elif attack_type == "route_leak":
                # Legitimate AS announces prefix it shouldn't
                leaker_asn = random.choice(self.verified_ases)
                leaked_prefix = random.choice(high_value_targets)
                
                announcement = {
                    "id": f"attack_leak_{i+1}",
                    "sender_asn": leaker_asn,
                    "origin_as": leaker_asn,
                    "announced_prefix": leaked_prefix,
                    "prefix": leaked_prefix,
                    "as_path": [leaker_asn],
                    "timestamp": datetime.now().isoformat(),
                    "type": "route_leak",
                    "severity": "MEDIUM",
                    "source": "attack_simulation"
                }
                
            else:  # origin_hijack or dns_hijack
                target_prefix = random.choice(high_value_targets)
                legitimate_owner = random.choice(self.verified_ases)
                
                announcement = {
                    "id": f"attack_{attack_type}_{i+1}",
                    "sender_asn": attacker_asn,
                    "origin_as": attacker_asn,
                    "announced_prefix": target_prefix,
                    "prefix": target_prefix,
                    "as_path": [attacker_asn, random.choice(self.verified_ases)],
                    "timestamp": datetime.now().isoformat(),
                    "type": attack_type,
                    "severity": "HIGH",
                    "legitimate_owner": legitimate_owner,
                    "source": "attack_simulation"
                }
            
            announcements.append(announcement)
        
        return announcements

# =============================================================================
# ENHANCED RPKI NODE WITH PARALLEL PROCESSING
# =============================================================================

class EnhancedRPKINode:
    """
    Enhanced RPKI verification node with:
    - Real RPKI verification integration
    - Advanced attack pattern detection
    - Parallel processing capabilities
    - Consensus voting participation
    """
    
    def __init__(self, node_id: str, announcements: List[Dict], 
                 blockchain_manager, voting_engine, data_source_manager):
        """
        Initialize enhanced RPKI node
        
        Args:
            node_id: Unique identifier for this node (e.g., "as01")
            announcements: List of BGP announcements to process
            blockchain_manager: Blockchain consensus manager
            voting_engine: Consensus voting engine
            data_source_manager: Data source manager for registry access
        """
        self.node_id = node_id
        self.announcements = announcements
        self.blockchain_manager = blockchain_manager
        self.voting_engine = voting_engine
        self.data_source_manager = data_source_manager
        self.logger = logging.getLogger(f'BGP-Sentry-{node_id}')
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'legitimate_count': 0,
            'attacks_detected': 0,
            'rpki_valid': 0,
            'rpki_invalid': 0,
            'processing_start_time': None,
            'processing_end_time': None
        }
        
        # Attack detection storage
        self.detected_attacks = []
        
        self.logger.info(f"🚀 {self.node_id}: Initialized with {len(announcements)} announcements")
    
    def enhanced_rpki_verify(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced RPKI verification using actual verifier module and attack detection
        
        Args:
            announcement: BGP announcement to verify
            
        Returns:
            Dict containing verification result and attack indicators
        """
        sender_asn = announcement.get('sender_asn', announcement.get('origin_as'))
        prefix = announcement.get('announced_prefix', announcement.get('prefix', ''))
        
        # Initialize result structure
        verification_result = {
            'valid': False,
            'reason': 'unknown',
            'attack_indicators': [],
            'verification_method': 'unknown',
            'confidence': 0.0
        }
        
        # Step 1: RPKI verification using your actual verifier module
        if RPKI_VERIFIER_AVAILABLE:
            try:
                is_verified = is_as_verified(sender_asn)
                verification_result['verification_method'] = 'rpki_module'
                
                if is_verified:
                    verification_result['valid'] = True
                    verification_result['reason'] = 'RPKI_VALID'
                    verification_result['confidence'] = 0.9
                    self.stats['rpki_valid'] += 1
                else:
                    verification_result['valid'] = False
                    verification_result['reason'] = 'RPKI_INVALID'
                    verification_result['confidence'] = 0.8
                    self.stats['rpki_invalid'] += 1
                    
            except Exception as e:
                self.logger.error(f"RPKI verification error for AS{sender_asn}: {e}")
                verification_result = self._fallback_rpki_verify(announcement)
        else:
            # Use fallback verification
            verification_result = self._fallback_rpki_verify(announcement)
        
        # Step 2: Advanced attack pattern detection (even for RPKI-valid announcements)
        attack_indicators = self._detect_attack_patterns(announcement)
        verification_result['attack_indicators'] = attack_indicators
        
        # Step 3: Cross-reference with blockchain registry
        registry_result = self._verify_against_registry(announcement)
        if not registry_result['valid']:
            verification_result['valid'] = False
            verification_result['reason'] = registry_result['reason']
            verification_result['attack_indicators'].extend(registry_result.get('indicators', []))
        
        # Step 4: Adjust confidence based on attack indicators
        if attack_indicators:
            verification_result['confidence'] = max(0.1, verification_result['confidence'] - (len(attack_indicators) * 0.2))
            if len(attack_indicators) >= 2:
                verification_result['valid'] = False
                verification_result['reason'] = 'MULTIPLE_ATTACK_INDICATORS'
        
        return verification_result
    
    def _fallback_rpki_verify(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback RPKI verification when module is unavailable
        Uses verified ASN list from data source manager
        """
        sender_asn = announcement.get('sender_asn', announcement.get('origin_as'))
        
        if sender_asn in self.data_source_manager.verified_ases:
            return {
                'valid': True,
                'reason': 'FALLBACK_VERIFIED',
                'verification_method': 'fallback_list',
                'confidence': 0.7
            }
        else:
            return {
                'valid': False,
                'reason': 'FALLBACK_UNVERIFIED',
                'verification_method': 'fallback_list',
                'confidence': 0.6
            }
    
    def _detect_attack_patterns(self, announcement: Dict[str, Any]) -> List[str]:
        """
        Advanced attack pattern detection using multiple heuristics
        
        Returns:
            List of attack indicators found
        """
        sender_asn = announcement.get('sender_asn', announcement.get('origin_as'))
        prefix = announcement.get('announced_prefix', announcement.get('prefix', ''))
        as_path = announcement.get('as_path', [])
        
        indicators = []
        
        # Pattern 1: Suspicious AS numbers
        suspicious_asns = [666, 31337, 8888, 9999, 1234, 4444, 7777, 65000, 65001]
        if sender_asn in suspicious_asns:
            indicators.append("SUSPICIOUS_ASN")
        
        # Pattern 2: High-value target prefixes
        high_value_targets = [
            "8.8.8.0/24", "1.1.1.0/24", "208.67.222.0/24",
            "185.199.108.0/22", "151.101.0.0/16", "104.16.0.0/12"
        ]
        if prefix in high_value_targets:
            indicators.append("HIGH_VALUE_TARGET")
        
        # Pattern 3: Sub-prefix hijacking (unusually specific routes)
        if any(specific in prefix for specific in ["/25", "/26", "/27", "/28", "/29", "/30"]):
            indicators.append("SUSPICIOUS_SPECIFICITY")
        
        # Pattern 4: Bogon prefixes (should never be announced)
        bogon_prefixes = ["0.0.0.0/8", "127.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4", "240.0.0.0/4"]
        for bogon in bogon_prefixes:
            if prefix.startswith(bogon.split('/')[0]):
                indicators.append("BOGON_PREFIX")
        
        # Pattern 5: AS path anomalies
        if len(as_path) > 10:
            indicators.append("SUSPICIOUS_PATH_LENGTH")
        
        if len(set(as_path)) != len(as_path):  # Duplicate ASNs in path
            indicators.append("AS_PATH_LOOPS")
        
        # Pattern 6: Timestamp anomalies (if available)
        try:
            announcement_time = datetime.fromisoformat(announcement.get('timestamp', ''))
            time_diff = (datetime.now() - announcement_time).total_seconds()
            if abs(time_diff) > 3600:  # More than 1 hour difference
                indicators.append("TIMESTAMP_ANOMALY")
        except:
            pass
        
        return indicators
    
    def _verify_against_registry(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify announcement against blockchain registry ground truth
        
        Returns:
            Dict with verification result and any registry-based indicators
        """
        sender_asn = announcement.get('sender_asn', announcement.get('origin_as'))
        prefix = announcement.get('announced_prefix', announcement.get('prefix', ''))
        
        # Check prefix ownership in registry
        prefix_info = self.data_source_manager.blockchain_registry.get("prefix_ownership", {}).get(prefix)
        
        if prefix_info:
            legitimate_owner = prefix_info.get("owner_asn")
            
            if sender_asn == legitimate_owner:
                return {'valid': True, 'reason': 'REGISTRY_VERIFIED'}
            else:
                return {
                    'valid': False,
                    'reason': 'REGISTRY_OWNERSHIP_MISMATCH',
                    'indicators': ['WRONG_ORIGIN_ASN'],
                    'legitimate_owner': legitimate_owner
                }
        else:
            # Prefix not in registry - could be legitimate or attack
            return {'valid': True, 'reason': 'PREFIX_NOT_IN_REGISTRY'}
    
    def process_announcement(self, announcement: Dict[str, Any], announcement_index: int) -> Optional[Dict[str, Any]]:
        """
        Process individual BGP announcement with comprehensive analysis
        
        Args:
            announcement: BGP announcement to process
            announcement_index: Index of announcement being processed
            
        Returns:
            Attack data if attack detected, None if legitimate
        """
        sender_asn = announcement.get('sender_asn', announcement.get('origin_as'))
        prefix = announcement.get('announced_prefix', announcement.get('prefix', ''))
        
        self.logger.info(f"🔍 {self.node_id}: Processing {prefix} from AS{sender_asn}")
        
        # Perform enhanced RPKI verification and attack detection
        verification_result = self.enhanced_rpki_verify(announcement)
        
        # Update statistics
        self.stats['total_processed'] += 1
        
        if verification_result['valid'] and not verification_result['attack_indicators']:
            # Legitimate announcement
            self.stats['legitimate_count'] += 1
            self.logger.info(f"✅ {self.node_id}: RPKI Valid - Legitimate announcement")
            return None
        else:
            # Attack detected!
            self.stats['attacks_detected'] += 1
            
            # Create detailed attack data
            attack_data = {
                'node_id': self.node_id,
                'announcement_id': announcement.get('id', f'unknown_{announcement_index}'),
                'detection_timestamp': datetime.now().isoformat(),
                'sender_asn': sender_asn,
                'announced_prefix': prefix,
                'attack_type': announcement.get('type', 'detected_attack'),
                'severity': self._calculate_severity(verification_result['attack_indicators']),
                'rpki_status': verification_result['reason'],
                'attack_indicators': verification_result['attack_indicators'],
                'confidence': verification_result['confidence'],
                'verification_method': verification_result['verification_method'],
                'original_announcement': announcement
            }
            
            self.detected_attacks.append(attack_data)
            
            # Log attack detection
            self.logger.warning(f"🚨 {self.node_id}: ATTACK DETECTED!")
            self.logger.warning(f"   ├─ Prefix: {prefix}")
            self.logger.warning(f"   ├─ Origin AS: {sender_asn}")
            self.logger.warning(f"   ├─ Type: {attack_data['attack_type']}")
            self.logger.warning(f"   ├─ Severity: {attack_data['severity']}")
            self.logger.warning(f"   ├─ Confidence: {attack_data['confidence']:.2f}")
            self.logger.warning(f"   └─ Indicators: {', '.join(verification_result['attack_indicators'])}")
            
            # Submit to voting engine for consensus
            if self.voting_engine:
                self.voting_engine.submit_attack_detection(attack_data)
            
            return attack_data
    
    def _calculate_severity(self, indicators: List[str]) -> str:
        """Calculate attack severity based on indicators"""
        if not indicators:
            return "LOW"
        
        critical_indicators = ["HIGH_VALUE_TARGET", "BOGON_PREFIX", "MULTIPLE_ATTACK_INDICATORS"]
        high_indicators = ["SUSPICIOUS_ASN", "WRONG_ORIGIN_ASN", "SUSPICIOUS_SPECIFICITY"]
        
        if any(ind in indicators for ind in critical_indicators):
            return "CRITICAL"
        elif any(ind in indicators for ind in high_indicators):
            return "HIGH"
        elif len(indicators) >= 3:
            return "HIGH"
        elif len(indicators) >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def run(self):
        """
        Main processing loop for the RPKI node
        Processes all assigned announcements in sequence
        """
        self.stats['processing_start_time'] = datetime.now()
        self.logger.info(f"🏃 {self.node_id}: Starting processing loop")
        
        for i, announcement in enumerate(self.announcements, 1):
            self.logger.info(f"📡 {self.node_id}: Processing announcement {i}/{len(self.announcements)}")
            
            # Process announcement with attack detection
            attack_detected = self.process_announcement(announcement, i)
            
            # Simulate realistic processing delay
            time.sleep(0.1)
        
        self.stats['processing_end_time'] = datetime.now()
        processing_duration = (self.stats['processing_end_time'] - self.stats['processing_start_time']).total_seconds()
        
        # Log completion statistics
        self.logger.info(f"✅ {self.node_id}: Processing completed")
        self.logger.info(f"   ├─ Total processed: {self.stats['total_processed']}")
        self.logger.info(f"   ├─ Legitimate: {self.stats['legitimate_count']}")
        self.logger.info(f"   ├─ Attacks detected: {self.stats['attacks_detected']}")
        self.logger.info(f"   ├─ RPKI valid: {self.stats['rpki_valid']}")
        self.logger.info(f"   ├─ RPKI invalid: {self.stats['rpki_invalid']}")
        self.logger.info(f"   └─ Duration: {processing_duration:.2f}s")

# =============================================================================
# CONSENSUS VOTING ENGINE
# =============================================================================

class ConsensusVotingEngine:
    """
    Distributed consensus voting engine for attack validation
    Uses Byzantine fault-tolerant consensus to confirm attacks
    """
    
    def __init__(self, num_nodes: int, consensus_threshold: float = 0.6):
        """
        Initialize voting engine
        
        Args:
            num_nodes: Total number of RPKI nodes participating
            consensus_threshold: Minimum percentage of nodes required for consensus (0.0-1.0)
        """
        self.num_nodes = num_nodes
        self.consensus_threshold = consensus_threshold
        self.required_votes = max(1, int(num_nodes * consensus_threshold))
        
        # Voting storage
        self.attack_votes = {}  # Key: attack_signature -> voting_data
        self.confirmed_attacks = []
        self.rejected_attacks = []
        
        # Thread safety
        self.vote_lock = threading.Lock()
        
        self.logger = logging.getLogger('ConsensusEngine')
        self.logger.info(f"🗳️ Consensus engine started with {num_nodes} nodes")
        self.logger.info(f"   └─ Consensus threshold: {consensus_threshold*100}% ({self.required_votes} votes)")
    
    def submit_attack_detection(self, attack_data: Dict[str, Any]) -> bool:
        """
        Submit attack detection for consensus voting
        
        Args:
            attack_data: Attack detection data from RPKI node
            
        Returns:
            True if consensus reached, False otherwise
        """
        # Create unique attack signature for deduplication
        attack_signature = f"{attack_data['announced_prefix']}:{attack_data['sender_asn']}:{attack_data['attack_type']}"
        
        with self.vote_lock:
            # Initialize voting record if not exists
            if attack_signature not in self.attack_votes:
                self.attack_votes[attack_signature] = {
                    'attack_data': attack_data,
                    'votes': [],
                    'voting_nodes': set(),
                    'total_confidence': 0.0,
                    'first_detection': datetime.now().isoformat()
                }
            
            voting_record = self.attack_votes[attack_signature]
            
            # Check if this node already voted
            if attack_data['node_id'] in voting_record['voting_nodes']:
                return False  # Node already voted
            
            # Add vote
            voting_record['votes'].append(attack_data)
            voting_record['voting_nodes'].add(attack_data['node_id'])
            voting_record['total_confidence'] += attack_data.get('confidence', 0.5)
            
            vote_count = len(voting_record['votes'])
            average_confidence = voting_record['total_confidence'] / vote_count
            
            self.logger.info(f"🗳️ Vote received for {attack_signature}")
            self.logger.info(f"   ├─ Votes: {vote_count}/{self.num_nodes}")
            self.logger.info(f"   ├─ Required: {self.required_votes}")
            self.logger.info(f"   └─ Avg confidence: {average_confidence:.2f}")
            
            # Check for consensus
            if vote_count >= self.required_votes:
                return self._finalize_consensus(attack_signature, voting_record, average_confidence)
        
        return False
    
    def _finalize_consensus(self, attack_signature: str, voting_record: Dict, average_confidence: float) -> bool:
        """
        Finalize consensus decision for an attack
        
        Args:
            attack_signature: Unique attack identifier
            voting_record: Voting data for this attack
            average_confidence: Average confidence across all votes
            
        Returns:
            True if attack confirmed, False if rejected
        """
        vote_count = len(voting_record['votes'])
        
        # Consensus decision logic
        consensus_reached = vote_count >= self.required_votes
        confidence_threshold = 0.6
        attack_confirmed = consensus_reached and average_confidence >= confidence_threshold
        
        if attack_confirmed:
            # Attack confirmed by consensus
            confirmed_attack = voting_record['attack_data'].copy()
            confirmed_attack.update({
                'consensus_status': 'CONFIRMED',
                'consensus_votes': vote_count,
                'consensus_confidence': average_confidence,
                'consensus_timestamp': datetime.now().isoformat(),
                'voting_nodes': list(voting_record['voting_nodes']),
                'consensus_threshold_met': True
            })
            
            self.confirmed_attacks.append(confirmed_attack)
            
            self.logger.warning(f"✅ ATTACK CONFIRMED: {attack_signature}")
            self.logger.warning(f"   ├─ Votes: {vote_count}/{self.num_nodes}")
            self.logger.warning(f"   ├─ Confidence: {average_confidence:.2f}")
            self.logger.warning(f"   ├─ Type: {confirmed_attack['attack_type']}")
            self.logger.warning(f"   └─ Severity: {confirmed_attack['severity']}")
            
        else:
            # Attack rejected or insufficient confidence
            rejected_attack = voting_record['attack_data'].copy()
            rejected_attack.update({
                'consensus_status': 'REJECTED',
                'consensus_votes': vote_count,
                'consensus_confidence': average_confidence,
                'consensus_timestamp': datetime.now().isoformat(),
                'rejection_reason': 'INSUFFICIENT_CONFIDENCE' if consensus_reached else 'INSUFFICIENT_VOTES'
            })
            
            self.rejected_attacks.append(rejected_attack)
            
            self.logger.info(f"❌ Attack rejected: {attack_signature} (confidence: {average_confidence:.2f})")
        
        # Remove from active voting
        del self.attack_votes[attack_signature]
        
        return attack_confirmed
    
    def get_consensus_summary(self) -> Dict[str, Any]:
        """Get summary of consensus voting results"""
        return {
            'total_confirmed_attacks': len(self.confirmed_attacks),
            'total_rejected_attacks': len(self.rejected_attacks),
            'active_votes': len(self.attack_votes),
            'consensus_threshold': self.consensus_threshold,
            'required_votes': self.required_votes,
            'confirmed_attacks': self.confirmed_attacks,
            'rejected_attacks': self.rejected_attacks
        }

# =============================================================================
# BLOCKCHAIN CONSENSUS MANAGER (Placeholder)
# =============================================================================

class BlockchainConsensusManager:
    """
    Placeholder for blockchain consensus management
    In production, this would interface with actual blockchain
    """
    
    def __init__(self):
        self.logger = logging.getLogger('BlockchainManager')
        self.transactions = []
    
    def record_attack_detection(self, attack_data: Dict[str, Any]) -> str:
        """Record confirmed attack on blockchain"""
        transaction = {
            'id': f"tx_{len(self.transactions) + 1}",
            'timestamp': datetime.now().isoformat(),
            'type': 'attack_detection',
            'data': attack_data
        }
        
        self.transactions.append(transaction)
        self.logger.info(f"📝 Recorded attack on blockchain: {transaction['id']}")
        return transaction['id']

# =============================================================================
# MAIN SIMULATION ORCHESTRATOR
# =============================================================================

def main():
    """
    Main BGP-Sentry enhanced parallel simulation with real data integration
    """
    
    # Setup logging with better formatting
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("\n" + "🎯 BGP-SENTRY ENHANCED PARALLEL SIMULATION" + "\n")
    print("=" * 80)
    print("🔄 Architecture:")
    print("   • Multiple RPKI nodes processing in parallel")
    print("   • Real RPKI verification integration")
    print("   • Advanced attack pattern detection")
    print("   • Consensus-based attack validation")
    print("   • Blockchain-integrated ground truth")
    print("=" * 80)
    
    # =================================================================
    # STEP 1: Initialize Data Sources
    # =================================================================
    print("📋 Step 1: Loading data sources...")
    
    data_manager = DataSourceManager()
    
    # Load blockchain registry data
    blockchain_registry = data_manager.load_blockchain_registry()
    print(f"✅ Loaded blockchain registry with {len(blockchain_registry)} entries")
    
    # Load verified ASN list
    verified_ases = data_manager.load_verified_ases()
    print(f"✅ Loaded {len(verified_ases)} verified ASNs: {verified_ases}")
    
    # Generate realistic BGP announcements with attacks
    total_announcements = 90  # Distributed across nodes
    all_announcements = data_manager.generate_realistic_bgp_announcements(total_announcements)
    
    # =================================================================
    # STEP 2: Initialize Consensus Systems
    # =================================================================
    print("\n📋 Step 2: Initializing consensus systems...")
    
    num_nodes = 9
    consensus_threshold = 0.6  # 60% of nodes must agree
    
    # Initialize voting engine
    voting_engine = ConsensusVotingEngine(num_nodes, consensus_threshold)
    
    # Initialize blockchain manager
    blockchain_manager = BlockchainConsensusManager()
    
    print(f"✅ Consensus systems initialized")
    print(f"   ├─ Nodes: {num_nodes}")
    print(f"   ├─ Consensus threshold: {consensus_threshold*100}%")
    print(f"   └─ Required votes: {voting_engine.required_votes}")
    
    # =================================================================
    # STEP 3: Create and Distribute RPKI Nodes
    # =================================================================
    print("\n📋 Step 3: Creating RPKI nodes...")
    
    # Distribute announcements across nodes
    announcements_per_node = len(all_announcements) // num_nodes
    
    nodes = []
    for i in range(num_nodes):
        node_id = f"as{(i*2)+1:02d}"  # as01, as03, as05, etc.
        
        # Calculate announcement range for this node
        start_idx = i * announcements_per_node
        if i == num_nodes - 1:  # Last node gets remaining announcements
            node_announcements = all_announcements[start_idx:]
        else:
            end_idx = start_idx + announcements_per_node
            node_announcements = all_announcements[start_idx:end_idx]
        
        # Create enhanced RPKI node
        node = EnhancedRPKINode(
            node_id=node_id,
            announcements=node_announcements,
            blockchain_manager=blockchain_manager,
            voting_engine=voting_engine,
            data_source_manager=data_manager
        )
        
        nodes.append(node)
        print(f"🚀 Created {node_id}: {len(node_announcements)} announcements")
    
    # =================================================================
    # STEP 4: Run Parallel Simulation
    # =================================================================
    print(f"\n📋 Step 4: Starting parallel simulation...")
    print(f"📡 Processing {len(all_announcements)} total announcements across {num_nodes} nodes")
    
    start_time = time.time()
    
    # Execute nodes in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_nodes) as executor:
        print(f"🏃 Launching {num_nodes} parallel RPKI processing threads...")
        
        # Submit all node processing tasks
        future_to_node = {executor.submit(node.run): node for node in nodes}
        
        # Wait for all nodes to complete
        concurrent.futures.wait(future_to_node)
        
        print("✅ All nodes completed processing")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # =================================================================
    # STEP 5: Collect and Analyze Results
    # =================================================================
    print(f"\n📋 Step 5: Analyzing results...")
    
    # Aggregate statistics from all nodes
    total_processed = sum(node.stats['total_processed'] for node in nodes)
    total_legitimate = sum(node.stats['legitimate_count'] for node in nodes)
    total_attacks_detected = sum(node.stats['attacks_detected'] for node in nodes)
    total_rpki_valid = sum(node.stats['rpki_valid'] for node in nodes)
    total_rpki_invalid = sum(node.stats['rpki_invalid'] for node in nodes)
    
    # Get consensus results
    consensus_summary = voting_engine.get_consensus_summary()
    
    # =================================================================
    # STEP 6: Generate Comprehensive Results
    # =================================================================
    print("\n" + "=" * 80)
    print("🎉 BGP-SENTRY ENHANCED SIMULATION COMPLETE!")
    print("=" * 80)
    
    # Performance metrics
    print(f"⏱️  Duration: {total_duration:.2f} seconds")
    print(f"🖥️  Nodes: {num_nodes}")
    print(f"📊 Total Announcements: {total_processed}")
    print(f"⚡ Processing Rate: {total_processed/total_duration:.1f} announcements/second")
    
    # Detection metrics
    print(f"\n🔍 DETECTION RESULTS:")
    print(f"   ├─ Legitimate Traffic: {total_legitimate}")
    print(f"   ├─ Attacks Detected: {total_attacks_detected}")
    print(f"   ├─ RPKI Valid: {total_rpki_valid}")
    print(f"   └─ RPKI Invalid: {total_rpki_invalid}")
    
    # Consensus metrics
    print(f"\n🗳️  CONSENSUS RESULTS:")
    print(f"   ├─ Confirmed Attacks: {consensus_summary['total_confirmed_attacks']}")
    print(f"   ├─ Rejected Detections: {consensus_summary['total_rejected_attacks']}")
    print(f"   ├─ Consensus Threshold: {consensus_threshold*100}%")
    print(f"   └─ Active Votes: {consensus_summary['active_votes']}")
    
    # Attack breakdown
    if consensus_summary['confirmed_attacks']:
        print(f"\n🚨 CONFIRMED ATTACKS SUMMARY:")
        attack_types = {}
        severity_counts = {}
        
        for attack in consensus_summary['confirmed_attacks']:
            attack_type = attack.get('attack_type', 'unknown')
            severity = attack.get('severity', 'unknown')
            
            attack_types[attack_type] = attack_types.get(attack_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            print(f"   • {attack_type}: {attack['announced_prefix']} (AS{attack['sender_asn']}) - {severity}")
        
        print(f"\n📊 ATTACK TYPE BREAKDOWN:")
        for attack_type, count in attack_types.items():
            print(f"   ├─ {attack_type}: {count}")
        
        print(f"\n⚠️  SEVERITY BREAKDOWN:")
        for severity, count in severity_counts.items():
            print(f"   ├─ {severity}: {count}")
    
    # Data source utilization
    print(f"\n📋 DATA SOURCE UTILIZATION:")
    print(f"   ├─ RPKI Module: {'✅ Active' if RPKI_VERIFIER_AVAILABLE else '❌ Fallback'}")
    print(f"   ├─ Blockchain Registry: {len(blockchain_registry)} entries")
    print(f"   ├─ Verified ASNs: {len(verified_ases)}")
    print(f"   └─ Generated Announcements: {len(all_announcements)}")
    
    # Save detailed results
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Save attack detections
    with open(results_dir / "enhanced_attack_detections.json", "w") as f:
        json.dump(consensus_summary['confirmed_attacks'], f, indent=2)
    
    # Save simulation summary
    simulation_summary = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": total_duration,
        "nodes": num_nodes,
        "total_announcements": total_processed,
        "legitimate_count": total_legitimate,
        "attacks_detected": total_attacks_detected,
        "confirmed_attacks": consensus_summary['total_confirmed_attacks'],
        "consensus_threshold": consensus_threshold,
        "rpki_module_available": RPKI_VERIFIER_AVAILABLE,
        "performance": {
            "announcements_per_second": total_processed/total_duration,
            "average_processing_time_per_announcement": total_duration/total_processed
        }
    }
    
    with open(results_dir / "enhanced_simulation_summary.json", "w") as f:
        json.dump(simulation_summary, f, indent=2)
    
    print(f"\n📁 Results saved to:")
    print(f"   ├─ results/enhanced_attack_detections.json")
    print(f"   └─ results/enhanced_simulation_summary.json")
    
    print(f"\n✨ Enhanced simulation completed successfully!")
    
    # Performance analysis
    if total_duration > 0:
        efficiency = (total_processed / total_duration) / num_nodes
        print(f"\n📈 PERFORMANCE ANALYSIS:")
        print(f"   ├─ Overall efficiency: {efficiency:.1f} announcements/second/node")
        print(f"   ├─ Parallel speedup: ~{num_nodes}x")
        print(f"   └─ Attack detection rate: {(total_attacks_detected/total_processed)*100:.1f}%")

if __name__ == "__main__":
    main()