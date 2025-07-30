#!/usr/bin/env python3
"""
BGP Test Data Generator
Located: /home/anik/code/BGP-Sentry/tests/data_generator/generatedata.py
Reads configurations from shared_registry and generates BGP test data for RPKI nodes
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

class BGPTestDataGenerator:
    def __init__(self):
        # Set up paths
        self.tests_dir = Path(__file__).parent.parent  # tests/
        self.project_root = self.tests_dir.parent      # BGP-Sentry/
        self.shared_registry_dir = self.project_root / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry"
        self.rpki_nodes_dir = self.project_root / "nodes/rpki_nodes"
        
        print("🎯 BGP Test Data Generator")
        print("=" * 50)
        print(f"📁 Project Root: {self.project_root}")
        print(f"📁 Shared Registry: {self.shared_registry_dir}")
        print(f"📁 RPKI Nodes: {self.rpki_nodes_dir}")
        
        # Initialize data structures
        self.configs = {}
        self.rpki_node_folders = []
        self.prefix_ownership = {}
        self.relationships = {}
        self.generation_settings = {
            "announcements_per_router": 10,
            "legitimate_percentage": 70,
            "attack_percentage": 30,
            "time_window_minutes": 60
        }
    
    def load_configurations(self):
        """Load configurations from shared_registry"""
        print(f"\n🔍 Loading configurations from shared_registry...")
        
        if not self.shared_registry_dir.exists():
            print(f"❌ Shared registry directory not found: {self.shared_registry_dir}")
            return False
        
        # List available config files
        config_files = list(self.shared_registry_dir.glob("*.json"))
        print(f"📋 Found {len(config_files)} configuration files:")
        
        for config_file in config_files:
            print(f"   📄 {config_file.name}")
            try:
                with open(config_file, 'r') as f:
                    self.configs[config_file.stem] = json.load(f)
                print(f"   ✅ Loaded successfully")
            except Exception as e:
                print(f"   ❌ Error loading: {e}")
        
        # Extract specific configurations
        self.extract_network_info()
        self.extract_relationships()
        
        return len(self.configs) > 0
    
    def extract_network_info(self):
        """Extract network information and prefix ownership"""
        print(f"\n📊 Extracting network information...")
        
        # Try to get from public_network_registry
        if "public_network_registry" in self.configs:
            registry = self.configs["public_network_registry"]
            
            # Extract RPKI node prefixes
            if "rpki_nodes" in registry:
                for as_str, as_info in registry["rpki_nodes"].items():
                    as_num = int(as_str)
                    if "owned_prefixes" in as_info:
                        self.prefix_ownership[as_num] = as_info["owned_prefixes"]
                        print(f"   📍 AS{as_num:02d}: {len(as_info['owned_prefixes'])} prefixes")
            
            # Extract Non-RPKI node prefixes
            if "non_rpki_nodes" in registry:
                for as_str, as_info in registry["non_rpki_nodes"].items():
                    as_num = int(as_str)
                    if "owned_prefixes" in as_info:
                        self.prefix_ownership[as_num] = as_info["owned_prefixes"]
                        print(f"   📍 AS{as_num:02d}: {len(as_info['owned_prefixes'])} prefixes")
        
        print(f"   📊 Total ASes with prefixes: {len(self.prefix_ownership)}")
    
    def extract_relationships(self):
        """Extract AS relationships"""
        print(f"\n🔗 Extracting AS relationships...")
        
        # Try to get from as_relationships
        if "as_relationships" in self.configs:
            rel_config = self.configs["as_relationships"]
            if "relationships" in rel_config:
                self.relationships = rel_config["relationships"]
                print(f"   📊 Found {len(self.relationships)} AS relationships")
        
        # Default relationships if none found
        if not self.relationships:
            print(f"   📋 Creating default AS relationships...")
            self.relationships = {
                "1-2": "peer-peer", "1-3": "customer-provider", "2-4": "customer-provider",
                "3-5": "peer-peer", "4-6": "customer-provider", "5-7": "customer-provider",
                "6-8": "peer-peer", "7-9": "customer-provider", "8-10": "customer-provider",
                "9-11": "peer-peer", "10-12": "customer-provider", "11-13": "customer-provider",
                "12-14": "peer-peer", "13-15": "customer-provider", "14-16": "customer-provider",
                "15-17": "peer-peer", "16-18": "customer-provider", "1-5": "peer-peer",
                "7-11": "peer-peer", "13-17": "peer-peer"
            }
            print(f"   📊 Created {len(self.relationships)} default relationships")
    
    def discover_rpki_folders(self):
        """Discover RPKI node folders"""
        print(f"\n🔍 Discovering RPKI node folders...")
        
        if not self.rpki_nodes_dir.exists():
            print(f"❌ RPKI nodes directory not found: {self.rpki_nodes_dir}")
            return False
        
        # Look for AS folders (as01, as03, as05, etc.)
        as_folders = [d for d in self.rpki_nodes_dir.iterdir() 
                      if d.is_dir() and d.name.startswith("as") and d.name[2:].isdigit()]
        
        # Sort by AS number
        as_folders.sort(key=lambda x: int(x.name[2:]))
        
        print(f"📂 Found {len(as_folders)} RPKI AS folders:")
        
        for as_folder in as_folders:
            as_num = int(as_folder.name[2:])
            network_stack_dir = as_folder / "network_stack"
            bgpd_file = network_stack_dir / "bgpd.json"
            
            folder_info = {
                "as_number": as_num,
                "folder_path": as_folder,
                "network_stack_path": network_stack_dir,
                "bgpd_file_path": bgpd_file,
                "network_stack_exists": network_stack_dir.exists(),
                "bgpd_file_exists": bgpd_file.exists()
            }
            
            self.rpki_node_folders.append(folder_info)
            
            # Display folder status
            status_icons = []
            if folder_info["network_stack_exists"]:
                status_icons.append("📁")
            else:
                status_icons.append("❌")
            
            if folder_info["bgpd_file_exists"]:
                status_icons.append("📄")
            else:
                status_icons.append("➕")
            
            print(f"   {''.join(status_icons)} AS{as_num:02d}: {as_folder.relative_to(self.project_root)}")
        
        return len(self.rpki_node_folders) > 0
    
    def show_generation_plan(self):
        """Show what will be generated"""
        print(f"\n📋 BGP Data Generation Plan:")
        print(f"=" * 40)
        
        print(f"🎯 Target RPKI Nodes: {len(self.rpki_node_folders)}")
        for folder_info in self.rpki_node_folders:
            as_num = folder_info["as_number"]
            status = "✅ Ready" if folder_info["network_stack_exists"] else "❌ Missing network_stack"
            overwrite = "🔄 Overwrite" if folder_info["bgpd_file_exists"] else "➕ Create new"
            
            print(f"   AS{as_num:02d}: {status} | {overwrite}")
        
        print(f"\n📊 Generation Settings:")
        print(f"   • Announcements per router: {self.generation_settings['announcements_per_router']}")
        print(f"   • Legitimate scenarios: {self.generation_settings['legitimate_percentage']}%")
        print(f"   • Attack scenarios: {self.generation_settings['attack_percentage']}%")
        print(f"   • Time window: {self.generation_settings['time_window_minutes']} minutes")
        
        print(f"\n📈 Data Sources:")
        print(f"   • AS relationships: {len(self.relationships)} connections")
        print(f"   • Prefix ownership: {len(self.prefix_ownership)} ASes")
        
        # Show sample data that will be generated
        print(f"\n📝 Sample BGP Announcement Structure:")
        sample = {
            "sender_asn": 2,
            "announced_prefix": "192.168.2.0/24",
            "as_path": [2],
            "timestamp": "2025-07-30T15:30:00Z"
        }
        print(f"   {json.dumps(sample, indent=6)}")
    
    def get_neighbors(self, as_num):
        """Get direct neighbors of an AS"""
        neighbors = []
        for relationship in self.relationships:
            as1, as2 = map(int, relationship.split('-'))
            if as1 == as_num:
                neighbors.append(as2)
            elif as2 == as_num:
                neighbors.append(as1)
        return neighbors
    
    def generate_legitimate_announcement(self, sender_as, observer_as):
        """Generate legitimate BGP announcement"""
        sender_prefixes = self.prefix_ownership.get(sender_as, [])
        if not sender_prefixes:
            return None
        
        prefix = random.choice(sender_prefixes)
        
        # Generate AS path based on relationships
        neighbors = self.get_neighbors(observer_as)
        if sender_as in neighbors:
            # Direct neighbor - 1 hop
            as_path = [sender_as]
        else:
            # Via intermediate - 2 hops
            if neighbors:
                intermediate = random.choice(neighbors)
                as_path = [intermediate, sender_as]
            else:
                as_path = [sender_as]
        
        return {
            "sender_asn": as_path[0],
            "announced_prefix": prefix,
            "as_path": as_path,
            "timestamp": self.generate_timestamp()
        }
    
    def generate_attack_announcement(self, observer_as):
        """Generate attack scenario (prefix hijack)"""
        all_ases = list(self.prefix_ownership.keys())
        if len(all_ases) < 2:
            return None
        
        # Choose victim and hijacked prefix
        victim_as = random.choice(all_ases)
        victim_prefixes = self.prefix_ownership.get(victim_as, [])
        if not victim_prefixes:
            return None
        
        # Choose attacker from observer's neighbors
        neighbors = self.get_neighbors(observer_as)
        if not neighbors:
            return None
        
        # Make sure attacker is different from victim
        available_attackers = [n for n in neighbors if n != victim_as]
        if not available_attackers:
            return None
        
        attacker_as = random.choice(available_attackers)
        hijacked_prefix = random.choice(victim_prefixes)
        
        return {
            "sender_asn": attacker_as,
            "announced_prefix": hijacked_prefix,
            "as_path": [attacker_as],  # Attacker claims to originate
            "timestamp": self.generate_timestamp()
        }
    
    def generate_timestamp(self):
        """Generate random timestamp within time window"""
        now = datetime.now()
        minutes_ago = random.randint(1, self.generation_settings["time_window_minutes"])
        timestamp = now - timedelta(minutes=minutes_ago)
        return timestamp.isoformat() + "Z"
    
    def generate_bgp_observations(self, observer_as):
        """Generate BGP observations for one RPKI router"""
        count = self.generation_settings["announcements_per_router"]
        legitimate_count = int(count * self.generation_settings["legitimate_percentage"] / 100)
        attack_count = count - legitimate_count
        
        announcements = []
        all_ases = list(self.prefix_ownership.keys())
        
        # Generate legitimate announcements
        for _ in range(legitimate_count):
            possible_senders = [as_num for as_num in all_ases if as_num != observer_as]
            if possible_senders:
                sender = random.choice(possible_senders)
                announcement = self.generate_legitimate_announcement(sender, observer_as)
                if announcement:
                    announcements.append(announcement)
        
        # Generate attack announcements
        for _ in range(attack_count):
            announcement = self.generate_attack_announcement(observer_as)
            if announcement:
                announcements.append(announcement)
        
        # Fill to required count if needed
        while len(announcements) < count and all_ases:
            sender = random.choice([as_num for as_num in all_ases if as_num != observer_as])
            announcement = self.generate_legitimate_announcement(sender, observer_as)
            if announcement:
                announcements.append(announcement)
        
        # Sort by timestamp
        announcements.sort(key=lambda x: x['timestamp'])
        return announcements[:count]
    
    def write_bgp_data(self):
        """Write BGP data to all RPKI node folders"""
        print(f"\n🚀 Generating and writing BGP data...")
        print(f"=" * 50)
        
        successful_writes = 0
        failed_writes = 0
        
        for folder_info in self.rpki_node_folders:
            as_num = folder_info["as_number"]
            network_stack_dir = folder_info["network_stack_path"]
            bgpd_file = folder_info["bgpd_file_path"]
            
            print(f"\n🔧 Processing AS{as_num:02d}...")
            
            # Check if network_stack directory exists
            if not network_stack_dir.exists():
                print(f"   ❌ network_stack directory missing: {network_stack_dir}")
                failed_writes += 1
                continue
            
            # Generate BGP observations
            try:
                observations = self.generate_bgp_observations(as_num)
                bgp_data = {"bgp_announcements": observations}
                
                # Write to bgpd.json
                with open(bgpd_file, 'w') as f:
                    json.dump(bgp_data, f, indent=2)
                
                # Count legitimate vs attack scenarios
                legitimate = 0
                attacks = 0
                for ann in observations:
                    # Check if announcement is legitimate (sender owns the prefix)
                    sender_prefixes = self.prefix_ownership.get(ann["as_path"][-1], [])
                    if ann["announced_prefix"] in sender_prefixes:
                        legitimate += 1
                    else:
                        attacks += 1
                
                print(f"   ✅ Generated {len(observations)} announcements")
                print(f"   📊 Legitimate: {legitimate}, Attacks: {attacks}")
                print(f"   📁 Saved to: {bgpd_file.relative_to(self.project_root)}")
                
                successful_writes += 1
                
            except Exception as e:
                print(f"   ❌ Error generating data: {e}")
                failed_writes += 1
        
        # Summary
        print(f"\n🎉 BGP Data Generation Complete!")
        print(f"=" * 40)
        print(f"✅ Successful: {successful_writes} RPKI nodes")
        print(f"❌ Failed: {failed_writes} RPKI nodes")
        
        if successful_writes > 0:
            print(f"\n🔍 Verify generated data:")
            sample_as = self.rpki_node_folders[0]["as_number"]
            print(f"   cat nodes/rpki_nodes/as{sample_as:02d}/network_stack/bgpd.json | jq '.bgp_announcements | length'")
            print(f"   cat nodes/rpki_nodes/as{sample_as:02d}/network_stack/bgpd.json | jq '.bgp_announcements[0]'")
    
    def run(self):
        """Run the complete data generation process"""
        # Load configurations
        if not self.load_configurations():
            print(f"❌ Failed to load configurations. Exiting.")
            return
        
        # Discover RPKI folders
        if not self.discover_rpki_folders():
            print(f"❌ No RPKI folders found. Exiting.")
            return
        
        # Show generation plan
        self.show_generation_plan()
        
        # Ask for confirmation
        print(f"\n❓ Do you want to proceed with BGP data generation?")
        print(f"   This will write bgpd.json files to {len(self.rpki_node_folders)} RPKI node folders.")
        
        response = input(f"   Type 'y' to continue, any other key to cancel: ").lower().strip()
        
        if response == 'y':
            self.write_bgp_data()
        else:
            print(f"❌ Data generation cancelled.")

def main():
    generator = BGPTestDataGenerator()
    generator.run()

if __name__ == "__main__":
    main()
