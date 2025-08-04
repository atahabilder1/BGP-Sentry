#!/usr/bin/env python3
"""
BGP Test Data Generator with Blockchain Ground Truth Integration
================================================================

This script generates realistic BGP test data for RPKI nodes and maintains ground truth on blockchain.

Key Functions:
1. Reads network configurations from shared_registry
2. Generates legitimate BGP announcements based on actual prefix ownership
3. Creates attack scenarios (prefix hijacks, route leaks, etc.)
4. Writes BGP data to individual RPKI node folders
5. Records ground truth data to blockchain for verification

File Structure:
- Input:  nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/*.json
- Output: nodes/rpki_nodes/as{XX}/network_stack/bgpd.json
- Blockchain: shared_blockchain_stack/blockchain_data/ground_truth.json

Author: BGP-Sentry Team
Location: /home/anik/code/BGP-Sentry/tests/data_generator/generate_data.py
"""

import json
import os
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# =============================================================================
# BGP TEST DATA GENERATOR CLASS
# =============================================================================

class BGPTestDataGenerator:
    """
    Comprehensive BGP test data generator that creates realistic network scenarios
    including both legitimate traffic and various attack patterns.
    
    This class:
    - Loads network topology from shared registry configurations
    - Generates BGP announcements based on real AS relationships
    - Creates attack scenarios for security testing
    - Maintains blockchain ground truth for verification
    """
    
    def __init__(self):
        """
        Initialize the BGP data generator with directory paths and default settings
        
        Sets up:
        - Project directory structure
        - Data generation parameters
        - Storage containers for network data
        """
        # =============================================================
        # DIRECTORY STRUCTURE SETUP
        # =============================================================
        
        # Calculate project paths relative to this script location
        self.tests_dir = Path(__file__).parent.parent  # tests/
        self.project_root = self.tests_dir.parent      # BGP-Sentry/
        
        # Define key directory paths
        self.shared_registry_dir = self.project_root / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry"
        self.rpki_nodes_dir = self.project_root / "nodes/rpki_nodes"
        self.blockchain_state_dir = self.project_root / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state"
        self.ip_asn_mapping_file = self.blockchain_state_dir / "ip_asn_mapping.json"
        
        # Display initialization info
        print("🎯 BGP Test Data Generator with Blockchain Ground Truth")
        print("=" * 70)
        print(f"📁 Project Root: {self.project_root}")
        print(f"📁 Shared Registry: {self.shared_registry_dir}")
        print(f"📁 RPKI Nodes: {self.rpki_nodes_dir}")
        print(f"📁 Blockchain State: {self.blockchain_state_dir}")
        print(f"📄 IP-ASN Mapping: {self.ip_asn_mapping_file}")
        
        # =============================================================
        # DATA STRUCTURE INITIALIZATION
        # =============================================================
        
        # Network configuration storage
        self.configs = {}                    # Loaded JSON configurations
        self.rpki_node_folders = []         # List of discovered RPKI node directories
        self.prefix_ownership = {}          # Map: AS_number -> [owned_prefixes]
        self.relationships = {}             # Map: "AS1-AS2" -> relationship_type
        
        # Blockchain ground truth storage - using existing simple blockchain state structure
        self.ground_truth_data = {
            "generation_timestamp": datetime.now().isoformat(),
            "ip_asn_mappings": {},           # Simple format: {"prefix": asn} for blockchain state
            "legitimate_announcements": [],   # Known good announcements for verification
            "attack_scenarios": [],          # Known attack scenarios for testing
            "as_relationships": {},          # Network topology relationships
            "metadata": {
                "generator_version": "2.0",
                "total_announcements": 0,
                "legitimate_count": 0,
                "attack_count": 0,
                "last_updated": datetime.now().isoformat()
            }
        }
        
        # Data generation configuration parameters
        self.generation_settings = {
            "announcements_per_router": 10,    # How many BGP announcements each router observes
            "legitimate_percentage": 70,       # Percentage of legitimate traffic
            "attack_percentage": 30,           # Percentage of attack scenarios
            "time_window_minutes": 60,         # Time range for announcement timestamps
            "enable_blockchain_recording": True  # Whether to record ground truth to blockchain
        }
    
    # =========================================================================
    # CONFIGURATION LOADING METHODS
    # =========================================================================
    
    def load_configurations(self) -> bool:
        """
        Load network configurations from shared_registry directory
        
        This method:
        1. Scans for JSON configuration files
        2. Loads each file into memory
        3. Extracts network topology and ownership data
        4. Handles missing or corrupted files gracefully
        
        Returns:
            bool: True if configurations loaded successfully, False otherwise
        """
        print(f"\n🔍 Loading configurations from shared_registry...")
        
        # Check if shared registry directory exists
        if not self.shared_registry_dir.exists():
            print(f"❌ Shared registry directory not found: {self.shared_registry_dir}")
            print(f"💡 Expected files: public_network_registry.json, as_relationships.json")
            return False
        
        # Scan for JSON configuration files
        config_files = list(self.shared_registry_dir.glob("*.json"))
        print(f"📋 Found {len(config_files)} configuration files:")
        
        # Load each configuration file
        for config_file in config_files:
            print(f"   📄 {config_file.name}")
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    self.configs[config_file.stem] = config_data
                    print(f"   ✅ Loaded successfully ({len(json.dumps(config_data))} bytes)")
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
            except Exception as e:
                print(f"   ❌ Error loading: {e}")
        
        # Extract specific network information from loaded configs
        self.extract_network_info()
        self.extract_relationships()
        
        # Validate that we have minimum required data
        success = len(self.configs) > 0 and len(self.prefix_ownership) > 0
        
        if success:
            print(f"✅ Configuration loading completed successfully")
        else:
            print(f"❌ Configuration loading failed or insufficient data")
        
        return success
    
    def extract_network_info(self):
        """
        Extract network information and prefix ownership from loaded configurations
        
        This method parses the configuration files to determine:
        - Which AS numbers own which IP prefixes
        - RPKI verification status of each AS
        - Network infrastructure details
        
        Expected structure in public_network_registry.json:
        {
          "rpki_nodes": {
            "1": {"owned_prefixes": ["10.1.0.0/16"], "status": "valid"},
            "3": {"owned_prefixes": ["10.3.0.0/16"], "status": "valid"}
          },
          "non_rpki_nodes": {
            "666": {"owned_prefixes": ["192.168.666.0/24"], "status": "malicious"}
          }
        }
        """
        print(f"\n📊 Extracting network information...")
        
        # Try to get data from public_network_registry configuration
        if "public_network_registry" in self.configs:
            registry = self.configs["public_network_registry"]
            print(f"   📋 Processing public_network_registry.json")
            
            # Extract RPKI node prefixes (legitimate, verified ASes)
            if "rpki_nodes" in registry:
                print(f"   🔐 Processing RPKI nodes...")
                for as_str, as_info in registry["rpki_nodes"].items():
                    as_num = int(as_str)  # Convert "1" -> 1
                    
                    if "owned_prefixes" in as_info:
                        self.prefix_ownership[as_num] = as_info["owned_prefixes"]
                        print(f"      📍 AS{as_num:02d}: {len(as_info['owned_prefixes'])} prefixes (RPKI verified)")
                        
                        # Record in ground truth - simple format for blockchain state
                        for prefix in as_info["owned_prefixes"]:
                            self.ground_truth_data["ip_asn_mappings"][prefix] = as_num
            
            # Extract Non-RPKI node prefixes (potentially malicious ASes)
            if "non_rpki_nodes" in registry:
                print(f"   ⚠️  Processing non-RPKI nodes...")
                for as_str, as_info in registry["non_rpki_nodes"].items():
                    as_num = int(as_str)
                    
                    if "owned_prefixes" in as_info:
                        self.prefix_ownership[as_num] = as_info["owned_prefixes"]
                        rpki_status = as_info.get("status", "unverified")
                        print(f"      📍 AS{as_num:02d}: {len(as_info['owned_prefixes'])} prefixes ({rpki_status})")
                        
                        # Record in ground truth - simple format
                        for prefix in as_info["owned_prefixes"]:
                            self.ground_truth_data["ip_asn_mappings"][prefix] = as_num
        
        # If no configuration found, create fallback data for testing
        if not self.prefix_ownership:
            print(f"   ⚠️  No prefix ownership data found, creating fallback data...")
            self._create_fallback_network_data()
        
        print(f"   📊 Total ASes with prefixes: {len(self.prefix_ownership)}")
        print(f"   📊 Total prefixes in ground truth: {len(self.ground_truth_data['ip_asn_mappings'])}")
    
    def _create_fallback_network_data(self):
        """
        Create fallback network data when configuration files are missing
        
        This generates a basic network topology for testing purposes with:
        - RPKI verified ASes (1, 3, 5, 7, 9, 11, 13, 15, 17)
        - Non-verified potential attackers (666, 31337, 8888, etc.)
        - Realistic IP prefix assignments
        """
        print(f"      🔄 Creating fallback network topology...")
        
        # RPKI verified ASes with legitimate prefixes
        rpki_verified_ases = {
            1: ["10.1.0.0/16", "192.168.1.0/24"],
            3: ["10.3.0.0/16", "192.168.3.0/24"],
            5: ["10.5.0.0/16", "192.168.5.0/24"],
            7: ["10.7.0.0/16", "192.168.7.0/24"],
            9: ["10.9.0.0/16", "192.168.9.0/24"],
            11: ["10.11.0.0/16", "192.168.11.0/24"],
            13: ["10.13.0.0/16", "192.168.13.0/24"],
            15: ["10.15.0.0/16", "192.168.15.0/24"],
            17: ["10.17.0.0/16", "192.168.17.0/24"]
        }
        
        # Potential attacker ASes (not RPKI verified)
        attacker_ases = {
            666: ["192.168.666.0/24"],      # Classic malicious ASN
            31337: ["172.31.33.0/24"],      # Hacker culture reference
            8888: ["8.8.8.0/25"],          # Attempting to hijack Google DNS
            9999: ["1.1.1.0/25"]           # Attempting to hijack Cloudflare DNS
        }
        
        # Combine all ASes
        all_ases = {**rpki_verified_ases, **attacker_ases}
        
        for as_num, prefixes in all_ases.items():
            self.prefix_ownership[as_num] = prefixes
            
            # Determine RPKI status
            rpki_status = "verified" if as_num in rpki_verified_ases else "unverified"
            
            # Record in ground truth - simple format for blockchain state
            for prefix in prefixes:
                self.ground_truth_data["ip_asn_mappings"][prefix] = as_num
            
            print(f"         AS{as_num}: {len(prefixes)} prefixes ({rpki_status})")
    
    def extract_relationships(self):
        """
        Extract AS relationships from configuration files
        
        AS relationships define how ASes connect to each other:
        - customer-provider: Customer pays provider for transit
        - peer-peer: ASes exchange traffic at no cost
        - sibling-sibling: ASes under same organization
        
        These relationships determine valid BGP paths and help detect anomalies.
        """
        print(f"\n🔗 Extracting AS relationships...")
        
        # Try to get relationships from as_relationships configuration
        if "as_relationships" in self.configs:
            rel_config = self.configs["as_relationships"]
            print(f"   📋 Processing as_relationships.json")
            
            if "relationships" in rel_config:
                self.relationships = rel_config["relationships"]
                print(f"   📊 Found {len(self.relationships)} AS relationships")
                
                # Record relationships in ground truth
                self.ground_truth_data["as_relationships"] = self.relationships.copy()
                
                # Display some example relationships
                for rel_key, rel_type in list(self.relationships.items())[:5]:
                    print(f"      🔗 {rel_key}: {rel_type}")
                
                if len(self.relationships) > 5:
                    print(f"      ... and {len(self.relationships) - 5} more")
        
        # Create default relationships if none found
        if not self.relationships:
            print(f"   📋 No relationships found, creating default topology...")
            self._create_default_relationships()
        
        print(f"   📊 Total relationships loaded: {len(self.relationships)}")
    
    def _create_default_relationships(self):
        """
        Create a default AS relationship topology for testing
        
        This creates a realistic network topology with:
        - Provider-customer hierarchies
        - Peer-to-peer connections
        - Regional interconnections
        """
        print(f"      🔄 Building default AS relationship topology...")
        
        # Define a realistic network topology
        default_relationships = {
            # Tier 1 provider relationships
            "1-2": "peer-peer",              # Major ISPs peer with each other
            "1-3": "customer-provider",      # AS1 provides transit to AS3
            "2-4": "customer-provider",      # AS2 provides transit to AS4
            
            # Regional provider relationships
            "3-5": "peer-peer",              # Regional ISPs peer
            "4-6": "customer-provider",
            "5-7": "customer-provider",
            "6-8": "peer-peer",
            
            # Customer networks
            "7-9": "customer-provider",
            "8-10": "customer-provider",
            "9-11": "peer-peer",
            "10-12": "customer-provider",
            "11-13": "customer-provider",
            "12-14": "peer-peer",
            "13-15": "customer-provider",
            "14-16": "customer-provider",
            "15-17": "peer-peer",
            "16-18": "customer-provider",
            
            # Cross-connections for redundancy
            "1-5": "peer-peer",              # Cross-regional peering
            "7-11": "peer-peer",             # Regional interconnection
            "13-17": "peer-peer"             # Edge network peering
        }
        
        self.relationships = default_relationships
        self.ground_truth_data["as_relationships"] = default_relationships.copy()
        
        print(f"      📊 Created {len(default_relationships)} default relationships")
    
    # =========================================================================
    # RPKI NODE DISCOVERY METHODS
    # =========================================================================
    
    def discover_rpki_folders(self) -> bool:
        """
        Discover and analyze RPKI node folders in the project structure
        
        This method:
        1. Scans for AS directories (as01, as03, as05, etc.)
        2. Checks for required subdirectories (network_stack)
        3. Identifies existing bgpd.json files
        4. Prepares folder information for data generation
        
        Returns:
            bool: True if RPKI folders found, False otherwise
        """
        print(f"\n🔍 Discovering RPKI node folders...")
        
        # Check if RPKI nodes directory exists
        if not self.rpki_nodes_dir.exists():
            print(f"❌ RPKI nodes directory not found: {self.rpki_nodes_dir}")
            print(f"💡 Expected structure: nodes/rpki_nodes/as01/, nodes/rpki_nodes/as03/, etc.")
            return False
        
        # Look for AS folders matching pattern: as01, as03, as05, etc.
        as_folders = [d for d in self.rpki_nodes_dir.iterdir() 
                      if d.is_dir() and d.name.startswith("as") and d.name[2:].isdigit()]
        
        if not as_folders:
            print(f"❌ No AS folders found in {self.rpki_nodes_dir}")
            return False
        
        # Sort folders by AS number for consistent processing order
        as_folders.sort(key=lambda x: int(x.name[2:]))
        
        print(f"📂 Found {len(as_folders)} RPKI AS folders:")
        
        # Analyze each AS folder structure
        for as_folder in as_folders:
            as_num = int(as_folder.name[2:])  # Extract AS number from folder name
            
            # Define expected file paths
            network_stack_dir = as_folder / "network_stack"
            bgpd_file = network_stack_dir / "bgpd.json"
            
            # Create folder information record
            folder_info = {
                "as_number": as_num,
                "folder_path": as_folder,
                "network_stack_path": network_stack_dir,
                "bgpd_file_path": bgpd_file,
                "network_stack_exists": network_stack_dir.exists(),
                "bgpd_file_exists": bgpd_file.exists(),
                "ready_for_generation": network_stack_dir.exists()
            }
            
            self.rpki_node_folders.append(folder_info)
            
            # Create status display with appropriate icons
            status_icons = []
            if folder_info["network_stack_exists"]:
                status_icons.append("📁")  # Network stack directory exists
            else:
                status_icons.append("❌")  # Missing network stack
            
            if folder_info["bgpd_file_exists"]:
                status_icons.append("📄")  # BGP data file exists (will overwrite)
            else:
                status_icons.append("➕")  # Will create new BGP data file
            
            print(f"   {''.join(status_icons)} AS{as_num:02d}: {as_folder.relative_to(self.project_root)}")
        
        ready_count = sum(1 for folder in self.rpki_node_folders if folder["ready_for_generation"])
        print(f"   📊 {ready_count}/{len(self.rpki_node_folders)} folders ready for data generation")
        
        return len(self.rpki_node_folders) > 0
    
    # =========================================================================
    # DATA GENERATION PLANNING AND DISPLAY
    # =========================================================================
    
    def show_generation_plan(self):
        """
        Display comprehensive data generation plan to user
        
        Shows:
        - Target RPKI nodes and their status
        - Generation parameters and settings
        - Sample data structure
        - Data sources being used
        """
        print(f"\n📋 BGP Data Generation Plan:")
        print(f"=" * 50)
        
        # Show target RPKI nodes and their readiness status
        print(f"🎯 Target RPKI Nodes: {len(self.rpki_node_folders)}")
        for folder_info in self.rpki_node_folders:
            as_num = folder_info["as_number"]
            
            # Determine status messages
            if folder_info["ready_for_generation"]:
                status = "✅ Ready"
            else:
                status = "❌ Missing network_stack directory"
            
            if folder_info["bgpd_file_exists"]:
                action = "🔄 Will overwrite existing bgpd.json"
            else:
                action = "➕ Will create new bgpd.json"
            
            print(f"   AS{as_num:02d}: {status} | {action}")
        
        # Show generation parameters
        print(f"\n📊 Generation Settings:")
        print(f"   • Announcements per router: {self.generation_settings['announcements_per_router']}")
        print(f"   • Legitimate scenarios: {self.generation_settings['legitimate_percentage']}%")
        print(f"   • Attack scenarios: {self.generation_settings['attack_percentage']}%")
        print(f"   • Time window: {self.generation_settings['time_window_minutes']} minutes")
        print(f"   • Blockchain recording: {'✅ Enabled' if self.generation_settings['enable_blockchain_recording'] else '❌ Disabled'}")
        
        # Show data sources
        print(f"\n📈 Data Sources:")
        print(f"   • AS relationships: {len(self.relationships)} connections")
        print(f"   • Prefix ownership: {len(self.prefix_ownership)} ASes")
        print(f"   • Ground truth entries: {len(self.ground_truth_data['ip_asn_mappings'])} prefixes")
        
        # Show sample BGP announcement structure
        print(f"\n📝 Sample BGP Announcement Structure:")
        sample_announcement = {
            "sender_asn": 2,
            "announced_prefix": "192.168.2.0/24",
            "as_path": [2],
            "timestamp": "2025-07-30T15:30:00Z",
            "message_type": "UPDATE",
            "next_hop": "192.168.1.1"
        }
        print(f"   {json.dumps(sample_announcement, indent=6)}")
        
        # Calculate total data to be generated
        ready_nodes = sum(1 for folder in self.rpki_node_folders if folder["ready_for_generation"])
        total_announcements = ready_nodes * self.generation_settings['announcements_per_router']
        legitimate_count = int(total_announcements * self.generation_settings['legitimate_percentage'] / 100)
        attack_count = total_announcements - legitimate_count
        
        print(f"\n📊 Generation Summary:")
        print(f"   • Total announcements to generate: {total_announcements}")
        print(f"   • Expected legitimate announcements: {legitimate_count}")
        print(f"   • Expected attack scenarios: {attack_count}")
        print(f"   • Ready RPKI nodes: {ready_nodes}")
    
    # =========================================================================
    # NETWORK TOPOLOGY ANALYSIS METHODS
    # =========================================================================
    
    def get_neighbors(self, as_num: int) -> List[int]:
        """
        Get direct neighbors of an AS based on configured relationships
        
        Args:
            as_num: AS number to find neighbors for
            
        Returns:
            List of neighbor AS numbers
            
        This is used to determine realistic BGP paths and routing relationships.
        """
        neighbors = []
        
        # Scan all relationships to find connections to this AS
        for relationship_key in self.relationships:
            as1, as2 = map(int, relationship_key.split('-'))
            
            if as1 == as_num:
                neighbors.append(as2)
            elif as2 == as_num:
                neighbors.append(as1)
        
        return neighbors
    
    def get_relationship_type(self, as1: int, as2: int) -> Optional[str]:
        """
        Get the relationship type between two ASes
        
        Args:
            as1, as2: AS numbers to check relationship for
            
        Returns:
            Relationship type string or None if no relationship exists
        """
        # Try both possible key formats
        key1 = f"{as1}-{as2}"
        key2 = f"{as2}-{as1}"
        
        if key1 in self.relationships:
            return self.relationships[key1]
        elif key2 in self.relationships:
            # Reverse the relationship for the opposite direction
            rel_type = self.relationships[key2]
            if rel_type == "customer-provider":
                return "provider-customer"
            elif rel_type == "provider-customer":
                return "customer-provider"
            else:
                return rel_type
        
        return None
    
    # =========================================================================
    # BGP ANNOUNCEMENT GENERATION METHODS
    # =========================================================================
    
    def generate_legitimate_announcement(self, sender_as: int, observer_as: int) -> Optional[Dict[str, Any]]:
        """
        Generate a legitimate BGP announcement
        
        Args:
            sender_as: AS that originated the announcement
            observer_as: AS that observes this announcement
            
        Returns:
            Dictionary containing BGP announcement data or None if generation fails
            
        A legitimate announcement means:
        - Sender AS actually owns the announced prefix
        - AS path follows realistic routing policies
        - Timing and format are realistic
        """
        # Get prefixes that the sender AS legitimately owns
        sender_prefixes = self.prefix_ownership.get(sender_as, [])
        if not sender_prefixes:
            return None  # Sender has no prefixes to announce
        
        # Randomly select one of the sender's legitimate prefixes
        announced_prefix = random.choice(sender_prefixes)
        
        # Generate realistic AS path based on network relationships
        neighbors = self.get_neighbors(observer_as)
        
        if sender_as in neighbors:
            # Direct neighbor - single hop path
            as_path = [sender_as]
            next_hop_as = sender_as
        else:
            # Multi-hop path via intermediate AS
            if neighbors:
                # Route through a neighbor (realistic BGP behavior)
                intermediate_as = random.choice(neighbors)
                as_path = [intermediate_as, sender_as]
                next_hop_as = intermediate_as
            else:
                # No neighbors defined, use direct path
                as_path = [sender_as]
                next_hop_as = sender_as
        
        # Create the BGP announcement
        announcement = {
            "sender_asn": as_path[0],           # First AS in path (next hop)
            "origin_asn": sender_as,            # AS that originated the prefix
            "announced_prefix": announced_prefix,
            "prefix": announced_prefix,         # Duplicate for compatibility
            "as_path": as_path,                 # Complete AS path
            "timestamp": self.generate_timestamp(),
            "message_type": "UPDATE",
            "next_hop": f"192.168.{next_hop_as}.1",  # Simulated next hop IP
            "announcement_type": "legitimate"
        }
        
        return announcement
    
    def generate_attack_announcement(self, observer_as: int) -> Optional[Dict[str, Any]]:
        """
        Generate a BGP attack scenario announcement
        
        Args:
            observer_as: AS that observes this attack
            
        Returns:
            Dictionary containing attack announcement data or None if generation fails
            
        Attack types generated:
        - Prefix hijacking: Attacker announces victim's prefix
        - Sub-prefix hijacking: More specific route than legitimate
        - Route leak: AS announces prefix it shouldn't
        """
        all_ases = list(self.prefix_ownership.keys())
        if len(all_ases) < 2:
            return None  # Need at least victim and attacker
        
        # Select attack type randomly
        attack_types = ["prefix_hijack", "sub_prefix_hijack", "route_leak"]
        attack_type = random.choice(attack_types)
        
        if attack_type == "prefix_hijack":
            return self._generate_prefix_hijack(observer_as, all_ases)
        elif attack_type == "sub_prefix_hijack":
            return self._generate_sub_prefix_hijack(observer_as, all_ases)
        else:  # route_leak
            return self._generate_route_leak(observer_as, all_ases)
    
    def _generate_prefix_hijack(self, observer_as: int, all_ases: List[int]) -> Optional[Dict[str, Any]]:
        """
        Generate a prefix hijacking attack scenario
        
        In this attack:
        - Attacker announces a prefix legitimately owned by victim
        - Attacker claims to be the origin of the prefix
        - Traffic gets misdirected to attacker
        """
        # Choose victim AS and one of their prefixes
        victim_as = random.choice(all_ases)
        victim_prefixes = self.prefix_ownership.get(victim_as, [])
        if not victim_prefixes:
            return None
        
        hijacked_prefix = random.choice(victim_prefixes)
        
        # Choose attacker from observer's neighbors (more realistic)
        neighbors = self.get_neighbors(observer_as)
        if not neighbors:
            return None
        
        # Ensure attacker is different from victim
        available_attackers = [n for n in neighbors if n != victim_as]
        if not available_attackers:
            # Fall back to any AS that's not the victim
            available_attackers = [a for a in all_ases if a != victim_as and a != observer_as]
            if not available_attackers:
                return None
        
        attacker_as = random.choice(available_attackers)
        
        # Create hijacking announcement
        announcement = {
            "sender_asn": attacker_as,
            "origin_asn": attacker_as,          # Attacker claims to originate prefix
            "announced_prefix": hijacked_prefix,
            "prefix": hijacked_prefix,
            "as_path": [attacker_as],           # Short path (looks attractive)
            "timestamp": self.generate_timestamp(),
            "message_type": "UPDATE",
            "next_hop": f"192.168.{attacker_as}.1",
            "announcement_type": "prefix_hijack",
            "legitimate_owner": victim_as,      # Ground truth information
            "attack_severity": "HIGH"
        }
        
        return announcement
    
    def _generate_sub_prefix_hijack(self, observer_as: int, all_ases: List[int]) -> Optional[Dict[str, Any]]:
        """
        Generate a sub-prefix hijacking attack
        
        In this attack:
        - Attacker announces a more specific prefix (longer subnet mask)
        - More specific routes have priority in BGP routing
        - Partial traffic gets hijacked to attacker
        """
        # Choose victim and their prefix
        victim_as = random.choice(all_ases)
        victim_prefixes = self.prefix_ownership.get(victim_as, [])
        if not victim_prefixes:
            return None
        
        # Select a prefix that can be made more specific
        base_prefix = random.choice(victim_prefixes)
        
        # Create more specific prefix
        if "/24" in base_prefix:
            hijacked_prefix = base_prefix.replace("/24", "/25")  # /24 -> /25
        elif "/16" in base_prefix:
            hijacked_prefix = base_prefix.replace("/16", "/24")  # /16 -> /24
        elif "/22" in base_prefix:
            hijacked_prefix = base_prefix.replace("/22", "/24")  # /22 -> /24
        else:
            # Can't make more specific, fall back to regular hijack
            hijacked_prefix = base_prefix
        
        # Choose attacker
        neighbors = self.get_neighbors(observer_as)
        available_attackers = [n for n in neighbors if n != victim_as] if neighbors else [a for a in all_ases if a != victim_as and a != observer_as]
        
        if not available_attackers:
            return None
        
        attacker_as = random.choice(available_attackers)
        
        announcement = {
            "sender_asn": attacker_as,
            "origin_asn": attacker_as,
            "announced_prefix": hijacked_prefix,
            "prefix": hijacked_prefix,
            "as_path": [attacker_as],
            "timestamp": self.generate_timestamp(),
            "message_type": "UPDATE",
            "next_hop": f"192.168.{attacker_as}.1",
            "announcement_type": "sub_prefix_hijack",
            "parent_prefix": base_prefix,       # Original legitimate prefix
            "legitimate_owner": victim_as,
            "attack_severity": "CRITICAL"       # More specific = higher priority
        }
        
        return announcement
    
    def _generate_route_leak(self, observer_as: int, all_ases: List[int]) -> Optional[Dict[str, Any]]:
        """
        Generate a route leak scenario
        
        In this attack:
        - Legitimate AS announces prefix it shouldn't (violates routing policies)
        - Often happens due to misconfiguration
        - Can cause traffic to flow through unauthorized paths
        """
        # Choose a legitimate AS as the "leaker"
        rpki_verified_ases = [asn for asn in all_ases if asn in [1, 3, 5, 7, 9, 11, 13, 15, 17]]
        if not rpki_verified_ases:
            return None
        
        leaker_as = random.choice(rpki_verified_ases)
        
        # Choose a prefix the leaker shouldn't announce (belongs to someone else)
        other_ases = [asn for asn in all_ases if asn != leaker_as and asn != observer_as]
        if not other_ases:
            return None
        
        victim_as = random.choice(other_ases)
        victim_prefixes = self.prefix_ownership.get(victim_as, [])
        if not victim_prefixes:
            return None
        
        leaked_prefix = random.choice(victim_prefixes)
        
        announcement = {
            "sender_asn": leaker_as,
            "origin_asn": leaker_as,            # Leaker incorrectly claims origin
            "announced_prefix": leaked_prefix,
            "prefix": leaked_prefix,
            "as_path": [leaker_as],
            "timestamp": self.generate_timestamp(),
            "message_type": "UPDATE",
            "next_hop": f"192.168.{leaker_as}.1",
            "announcement_type": "route_leak",
            "legitimate_owner": victim_as,
            "attack_severity": "MEDIUM",        # Less severe than hijacks
            "leak_type": "unauthorized_announcement"
        }
        
        return announcement
    
    def generate_timestamp(self) -> str:
        """
        Generate realistic timestamp within configured time window
        
        Returns:
            ISO format timestamp string
            
        Timestamps are scattered across the time window to simulate
        realistic BGP announcement timing.
        """
        now = datetime.now()
        minutes_ago = random.randint(1, self.generation_settings["time_window_minutes"])
        timestamp = now - timedelta(minutes=minutes_ago)
        return timestamp.isoformat() + "Z"
    
    # =========================================================================
    # BGP OBSERVATION GENERATION FOR RPKI NODES
    # =========================================================================
    
    def generate_bgp_observations(self, observer_as: int) -> List[Dict[str, Any]]:
        """
        Generate complete set of BGP observations for one RPKI router
        
        Args:
            observer_as: AS number of the observing RPKI router
            
        Returns:
            List of BGP announcements observed by this router
            
        This simulates what a real RPKI router would see:
        - Mix of legitimate announcements and attacks
        - Realistic timing distribution
        - Proper AS path information
        """
        total_count = self.generation_settings["announcements_per_router"]
        legitimate_percentage = self.generation_settings["legitimate_percentage"]
        
        # Calculate announcement distribution
        legitimate_count = int(total_count * legitimate_percentage / 100)
        attack_count = total_count - legitimate_count
        
        announcements = []
        all_ases = list(self.prefix_ownership.keys())
        
        print(f"      🔧 Generating {total_count} observations (✅{legitimate_count} legit, 🚨{attack_count} attacks)")
        
        # Generate legitimate announcements
        legitimate_generated = 0
        attempts = 0
        max_attempts = legitimate_count * 3  # Prevent infinite loops
        
        while legitimate_generated < legitimate_count and attempts < max_attempts:
            attempts += 1
            
            # Choose random sender (excluding observer itself)
            possible_senders = [as_num for as_num in all_ases if as_num != observer_as]
            if not possible_senders:
                break
            
            sender = random.choice(possible_senders)
            announcement = self.generate_legitimate_announcement(sender, observer_as)
            
            if announcement:
                announcements.append(announcement)
                legitimate_generated += 1
        
        # Generate attack announcements
        attack_generated = 0
        attempts = 0
        max_attempts = attack_count * 3
        
        while attack_generated < attack_count and attempts < max_attempts:
            attempts += 1
            
            announcement = self.generate_attack_announcement(observer_as)
            
            if announcement:
                announcements.append(announcement)
                attack_generated += 1
        
        # Fill to required count with additional legitimate traffic if needed
        while len(announcements) < total_count and all_ases:
            sender = random.choice([as_num for as_num in all_ases if as_num != observer_as])
            announcement = self.generate_legitimate_announcement(sender, observer_as)
            if announcement:
                announcements.append(announcement)
        
        # Sort announcements by timestamp for realistic chronological order
        announcements.sort(key=lambda x: x['timestamp'])
        
        # Trim to exact count if we generated too many
        announcements = announcements[:total_count]
        
        print(f"      ✅ Generated {len(announcements)} total observations")
        
        return announcements
    
    # =========================================================================
    # BLOCKCHAIN STATE MANAGEMENT METHODS
    # =========================================================================
    
    def load_existing_ip_asn_mapping(self) -> Dict[str, Any]:
        """
        Load existing IP-ASN mapping from blockchain state file
        
        Returns:
            Dict containing existing IP-ASN mappings or empty dict if file doesn't exist
            
        This loads the authoritative ground truth from:
        /nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/ip_asn_mapping.json
        """
        if not self.ip_asn_mapping_file.exists():
            print(f"   ℹ️  IP-ASN mapping file not found: {self.ip_asn_mapping_file}")
            print(f"      Will create new mapping file")
            return {}
        
        try:
            with open(self.ip_asn_mapping_file, 'r') as f:
                existing_mapping = json.load(f)
                print(f"   ✅ Loaded existing IP-ASN mapping with {len(existing_mapping)} entries")
                return existing_mapping
        except Exception as e:
            print(f"   ⚠️  Error loading existing IP-ASN mapping: {e}")
            return {}
    
    def merge_with_existing_mappings(self, existing_mappings: Dict[str, Any]):
        """
        Merge generated ground truth with existing blockchain state
        
        Args:
            existing_mappings: Existing IP-ASN mappings from blockchain state
            
        Maintains the simple format: {"prefix": asn_number}
        RPKI verification status comes from separate registry files.
        """
        merged_count = 0
        updated_count = 0
        
        print(f"   🔍 Merging with existing simple format mappings...")
        
        # Merge existing mappings (simple format)
        for prefix, asn_value in existing_mappings.items():
            if prefix not in self.ground_truth_data["ip_asn_mappings"]:
                # Add existing mapping we don't have
                self.ground_truth_data["ip_asn_mappings"][prefix] = int(asn_value)
                merged_count += 1
            else:
                # Keep our generated mapping (it might be more current)
                updated_count += 1
        
        print(f"   🔄 Merged {merged_count} existing mappings, kept {updated_count} generated mappings")
    
    def save_ip_asn_mapping_to_blockchain(self):
        """
        Save IP-ASN mapping to blockchain state file in simple format
        
        This updates the authoritative ground truth file:
        /nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/ip_asn_mapping.json
        
        Maintains the existing simple format: {"prefix": asn_number}
        RPKI verification status is handled by separate registry files.
        """
        if not self.generation_settings["enable_blockchain_recording"]:
            print(f"   📋 Blockchain recording disabled, skipping IP-ASN mapping save")
            return
        
        # Load existing mappings first
        existing_mappings = self.load_existing_ip_asn_mapping()
        
        # Merge with existing data
        if existing_mappings:
            self.merge_with_existing_mappings(existing_mappings)
        
        # Ensure blockchain state directory exists
        self.blockchain_state_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save in simple format to maintain compatibility
            # Format: {"prefix": asn_number}
            simple_mapping = {}
            
            for prefix, asn in self.ground_truth_data["ip_asn_mappings"].items():
                simple_mapping[prefix] = asn
            
            # Save to blockchain state file
            with open(self.ip_asn_mapping_file, 'w') as f:
                json.dump(simple_mapping, f, indent=2)
            
            print(f"   📝 IP-ASN mapping saved to: {self.ip_asn_mapping_file.relative_to(self.project_root)}")
            print(f"      └─ Total prefixes: {len(simple_mapping)} (simple format: prefix -> ASN)")
            
        except Exception as e:
            print(f"   ❌ Error saving IP-ASN mapping: {e}")
    
    def save_simple_compatibility_mapping(self, formatted_mapping: Dict[str, Any]):
        """
        No longer needed - we're keeping the simple format as the primary format
        """
        pass
    
    def record_ground_truth_to_blockchain(self, announcements: List[Dict[str, Any]], observer_as: int):
        """
        Record ground truth data to blockchain for verification purposes
        
        Args:
            announcements: List of generated BGP announcements
            observer_as: AS number of the observer
            
        This creates an authoritative record of what is legitimate vs attack
        for later verification of detection accuracy. The data is stored in the
        existing blockchain state structure.
        """
        if not self.generation_settings["enable_blockchain_recording"]:
            return
        
        # Process each announcement and categorize it
        for announcement in announcements:
            # Verify the announced prefix against our IP-ASN mapping (simple format)
            announced_prefix = announcement.get("announced_prefix")
            origin_asn = announcement.get("origin_asn")
            
            # Check if this prefix exists in our ground truth mapping
            if announced_prefix in self.ground_truth_data["ip_asn_mappings"]:
                legitimate_owner = self.ground_truth_data["ip_asn_mappings"][announced_prefix]
                is_legitimate = (origin_asn == legitimate_owner)
            else:
                # Prefix not in mapping - treat as legitimate if it's from prefix owner
                is_legitimate = self._is_announcement_legitimate(announcement)
            
            announcement_record = {
                "id": self._generate_announcement_id(announcement),
                "observer_asn": observer_as,
                "sender_asn": announcement.get("sender_asn"),
                "origin_asn": origin_asn,
                "announced_prefix": announced_prefix,
                "as_path": announcement.get("as_path", []),
                "timestamp": announcement.get("timestamp"),
                "is_legitimate": is_legitimate,
                "attack_type": announcement.get("announcement_type", "legitimate"),
                "attack_severity": announcement.get("attack_severity", "NONE"),
                "legitimate_owner": self.ground_truth_data["ip_asn_mappings"].get(announced_prefix),
                "ground_truth_timestamp": datetime.now().isoformat()
            }
            
            # Add to appropriate category
            if announcement_record["is_legitimate"]:
                self.ground_truth_data["legitimate_announcements"].append(announcement_record)
                self.ground_truth_data["metadata"]["legitimate_count"] += 1
            else:
                self.ground_truth_data["attack_scenarios"].append(announcement_record)
                self.ground_truth_data["metadata"]["attack_count"] += 1
            
            self.ground_truth_data["metadata"]["total_announcements"] += 1
    
    def _generate_announcement_id(self, announcement: Dict[str, Any]) -> str:
        """
        Generate unique ID for BGP announcement
        
        Args:
            announcement: BGP announcement data
            
        Returns:
            Unique hash-based identifier
        """
        # Create hash from key announcement fields
        id_data = f"{announcement.get('sender_asn')}:{announcement.get('announced_prefix')}:{announcement.get('timestamp')}"
        return hashlib.md5(id_data.encode()).hexdigest()[:12]
    
    def _is_announcement_legitimate(self, announcement: Dict[str, Any]) -> bool:
        """
        Determine if an announcement is legitimate based on ground truth
        
        Args:
            announcement: BGP announcement to check
            
        Returns:
            True if legitimate, False if attack
        """
        announcement_type = announcement.get("announcement_type", "legitimate")
        return announcement_type == "legitimate"
    
    def save_blockchain_ground_truth(self):
        """
        Save ground truth data to blockchain state files
        
        This saves to two locations:
        1. IP-ASN mapping to: shared_data/state/ip_asn_mapping.json (authoritative)
        2. Additional ground truth to: shared_data/state/ground_truth_metadata.json (for verification)
        """
        if not self.generation_settings["enable_blockchain_recording"]:
            print(f"   📋 Blockchain recording disabled, skipping ground truth save")
            return
        
        # Save IP-ASN mapping to blockchain state
        self.save_ip_asn_mapping_to_blockchain()
        
        # Save additional ground truth metadata for verification
        ground_truth_metadata_file = self.blockchain_state_dir / "ground_truth_metadata.json"
        
        try:
            # Prepare metadata (without duplicating IP-ASN mapping)
            metadata = {
                "generation_timestamp": self.ground_truth_data["generation_timestamp"],
                "legitimate_announcements": self.ground_truth_data["legitimate_announcements"],
                "attack_scenarios": self.ground_truth_data["attack_scenarios"],
                "as_relationships": self.ground_truth_data["as_relationships"],
                "metadata": self.ground_truth_data["metadata"]
            }
            
            with open(ground_truth_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"   📝 Ground truth metadata saved to: {ground_truth_metadata_file.relative_to(self.project_root)}")
            print(f"      ├─ Total announcements: {self.ground_truth_data['metadata']['total_announcements']}")
            print(f"      ├─ Legitimate: {self.ground_truth_data['metadata']['legitimate_count']}")
            print(f"      └─ Attacks: {self.ground_truth_data['metadata']['attack_count']}")
            
        except Exception as e:
            print(f"   ❌ Error saving ground truth metadata: {e}")
    
    # =========================================================================
    # DATA WRITING AND FILE MANAGEMENT
    # =========================================================================
    
    def write_bgp_data(self):
        """
        Write generated BGP data to all RPKI node folders
        
        This method:
        1. Generates BGP observations for each RPKI node
        2. Writes data to bgpd.json files
        3. Records ground truth to blockchain
        4. Provides detailed statistics and verification info
        """
        print(f"\n🚀 Generating and writing BGP data...")
        print(f"=" * 60)
        
        successful_writes = 0
        failed_writes = 0
        total_legitimate = 0
        total_attacks = 0
        
        # Process each RPKI node folder
        for folder_info in self.rpki_node_folders:
            as_num = folder_info["as_number"]
            network_stack_dir = folder_info["network_stack_path"]
            bgpd_file = folder_info["bgpd_file_path"]
            
            print(f"\n🔧 Processing AS{as_num:02d}...")
            
            # Verify network_stack directory exists
            if not network_stack_dir.exists():
                print(f"   ❌ network_stack directory missing: {network_stack_dir}")
                print(f"   💡 Expected: {network_stack_dir.relative_to(self.project_root)}")
                failed_writes += 1
                continue
            
            try:
                # Generate BGP observations for this AS
                observations = self.generate_bgp_observations(as_num)
                
                # Create complete BGP data structure
                bgp_data = {
                    "metadata": {
                        "observer_asn": as_num,
                        "generation_timestamp": datetime.now().isoformat(),
                        "generator_version": "2.0",
                        "total_announcements": len(observations)
                    },
                    "bgp_announcements": observations
                }
                
                # Write BGP data to file
                with open(bgpd_file, 'w') as f:
                    json.dump(bgp_data, f, indent=2)
                
                # Record ground truth data to blockchain
                self.record_ground_truth_to_blockchain(observations, as_num)
                
                # Analyze announcement types for statistics
                legitimate_count = 0
                attack_count = 0
                
                for announcement in observations:
                    if self._is_announcement_legitimate(announcement):
                        legitimate_count += 1
                    else:
                        attack_count += 1
                
                total_legitimate += legitimate_count
                total_attacks += attack_count
                
                # Display success information
                print(f"   ✅ Generated {len(observations)} announcements")
                print(f"   📊 Breakdown: ✅{legitimate_count} legitimate, 🚨{attack_count} attacks")
                print(f"   📁 Saved to: {bgpd_file.relative_to(self.project_root)}")
                
                successful_writes += 1
                
            except Exception as e:
                print(f"   ❌ Error generating data for AS{as_num:02d}: {e}")
                failed_writes += 1
        
        # Save blockchain ground truth data
        print(f"\n📝 Recording ground truth to blockchain...")
        self.save_blockchain_ground_truth()
        
        # Display comprehensive summary
        print(f"\n🎉 BGP Data Generation Complete!")
        print(f"=" * 50)
        print(f"✅ Successful: {successful_writes} RPKI nodes")
        print(f"❌ Failed: {failed_writes} RPKI nodes")
        print(f"📊 Total legitimate announcements: {total_legitimate}")
        print(f"📊 Total attack scenarios: {total_attacks}")
        print(f"📊 Total announcements generated: {total_legitimate + total_attacks}")
        
        if successful_writes > 0:
            # Provide verification commands
            print(f"\n🔍 Verify generated data:")
            sample_as = self.rpki_node_folders[0]["as_number"]
            print(f"   # Count announcements in sample file:")
            print(f"   cat nodes/rpki_nodes/as{sample_as:02d}/network_stack/bgpd.json | jq '.bgp_announcements | length'")
            print(f"   ")
            print(f"   # View sample announcement:")
            print(f"   cat nodes/rpki_nodes/as{sample_as:02d}/network_stack/bgpd.json | jq '.bgp_announcements[0]'")
            print(f"   ")
            print(f"   # Check IP-ASN mapping (simple format):")
            print(f"   cat nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/ip_asn_mapping.json | jq 'keys | length'")
            print(f"   ")
            print(f"   # View sample IP-ASN mapping:")
            print(f"   cat nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/ip_asn_mapping.json | jq 'to_entries[0]'")
            print(f"   ")
            print(f"   # Check ground truth metadata:")
            print(f"   cat nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/ground_truth_metadata.json | jq '.metadata'")
            
            # Provide next steps
            print(f"\n🚀 Next Steps:")
            print(f"   1. Run BGP-Sentry simulation: python bgp_sentry_main.py")
            print(f"   2. Verify attack detection accuracy against ground truth")
            print(f"   3. Analyze consensus voting results")
            print(f"   4. Review blockchain verification data")
    
    # =========================================================================
    # MAIN EXECUTION METHOD
    # =========================================================================
    
    def run(self):
        """
        Execute the complete BGP data generation process
        
        This is the main orchestration method that:
        1. Loads network configurations
        2. Discovers RPKI node folders
        3. Shows generation plan to user
        4. Generates and writes BGP data
        5. Records ground truth to blockchain
        """
        print(f"🎯 Starting BGP Test Data Generation Process...")
        
        # Step 1: Load network configurations from shared registry
        print(f"\n" + "="*60)
        print(f"📋 STEP 1: Loading Network Configurations")
        print(f"="*60)
        
        if not self.load_configurations():
            print(f"❌ Failed to load configurations. Cannot proceed.")
            print(f"💡 Ensure shared_registry directory exists with valid JSON files")
            return
        
        # Step 2: Discover RPKI node folders in project structure
        print(f"\n" + "="*60)
        print(f"📋 STEP 2: Discovering RPKI Node Structure")
        print(f"="*60)
        
        if not self.discover_rpki_folders():
            print(f"❌ No RPKI folders found. Cannot proceed.")
            print(f"💡 Ensure RPKI nodes exist in nodes/rpki_nodes/ directory")
            return
        
        # Step 3: Display comprehensive generation plan
        print(f"\n" + "="*60)
        print(f"📋 STEP 3: Generation Plan Review")
        print(f"="*60)
        
        self.show_generation_plan()
        
        # Step 4: Get user confirmation before proceeding
        print(f"\n" + "="*60)
        print(f"📋 STEP 4: User Confirmation")
        print(f"="*60)
        
        print(f"❓ Ready to generate BGP test data?")
        print(f"   This will:")
        print(f"   • Write bgpd.json files to {len([f for f in self.rpki_node_folders if f['ready_for_generation']])} RPKI node folders")
        print(f"   • Generate {sum(1 for f in self.rpki_node_folders if f['ready_for_generation']) * self.generation_settings['announcements_per_router']} total BGP announcements")
        print(f"   • Record ground truth data to blockchain")
        print(f"   • {'Overwrite existing bgpd.json files' if any(f['bgpd_file_exists'] for f in self.rpki_node_folders) else 'Create new bgpd.json files'}")
        
        response = input(f"\n   Type 'y' to continue, any other key to cancel: ").lower().strip()
        
        if response == 'y':
            # Step 5: Execute data generation
            print(f"\n" + "="*60)
            print(f"📋 STEP 5: BGP Data Generation")
            print(f"="*60)
            
            self.write_bgp_data()
            
            print(f"\n✨ BGP test data generation completed successfully!")
        else:
            print(f"❌ Data generation cancelled by user.")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main entry point for BGP test data generation
    
    Creates and runs the BGP data generator with comprehensive
    network topology simulation and blockchain ground truth recording.
    """
    generator = BGPTestDataGenerator()
    generator.run()

if __name__ == "__main__":
    main()