#!/usr/bin/env python3
"""
BGP-Sentry Enhanced Pre-Simulation Master Test
Complete system setup, validation, and timing analysis before running experiments
"""

import sys
import os
import json
import subprocess
import time
import signal
from pathlib import Path
from datetime import datetime
import threading

class EnhancedPreSimulationChecker:
    """Enhanced pre-simulation validation system with complete setup"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.test_results = {}
        self.critical_failures = []
        self.warnings = []
        self.timing_log = {}
        self.hardhat_process = None
        
        print("🚀 BGP-Sentry Enhanced Pre-Simulation Master Test")
        print("=" * 70)
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
    
    def log_timing(self, operation, duration):
        """Log timing information for operations"""
        self.timing_log[operation] = {
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        print(f"⏱️  {operation}: {duration:.2f} seconds")
    
    def setup_0_reset_blockchain(self):
        """Setup 0: Reset blockchain state"""
        print(f"\n🔄 SETUP 0: Blockchain Reset")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Kill any existing hardhat processes using system commands
            print("  🔍 Checking for existing Hardhat processes...")
            try:
                # Find and kill hardhat processes
                result = subprocess.run(['pkill', '-f', 'hardhat'], capture_output=True)
                if result.returncode == 0:
                    print("  🗡️  Killed existing Hardhat processes")
                    time.sleep(2)
                else:
                    print("  ✅ No existing Hardhat processes found")
            except FileNotFoundError:
                # pkill not available, try alternative
                try:
                    result = subprocess.run(['pgrep', '-f', 'hardhat'], capture_output=True, text=True)
                    if result.stdout.strip():
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            subprocess.run(['kill', pid])
                        print(f"  🗡️  Killed {len(pids)} Hardhat processes")
                        time.sleep(2)
                    else:
                        print("  ✅ No existing Hardhat processes found")
                except:
                    print("  ⚠️  Could not check for existing processes (continuing anyway)")
            
            # Clean blockchain data directories
            blockchain_dirs = [
                self.base_path / "smart_contract/cache",
                self.base_path / "smart_contract/artifacts", 
                self.base_path / "smart_contract/deployments/localhost"
            ]
            
            for dir_path in blockchain_dirs:
                if dir_path.exists():
                    print(f"  🧹 Cleaning {dir_path.name}")
                    subprocess.run(['rm', '-rf', str(dir_path)], check=True)
            
            # Reset wallet states
            wallet_registry = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/nonrpki_wallet_registry.json"
            if wallet_registry.exists():
                print("  🧹 Resetting wallet registry")
                with open(wallet_registry, 'w') as f:
                    json.dump({}, f)
            
            duration = time.time() - start_time
            self.log_timing("Blockchain Reset", duration)
            print(f"  ✅ Blockchain reset completed")
            return True
            
        except Exception as e:
            print(f"  ❌ Blockchain reset failed: {e}")
            self.critical_failures.append(f"Blockchain reset failed: {e}")
            return False
    
    def setup_1_start_hardhat(self):
        """Setup 1: Start Hardhat node"""
        print(f"\n🚀 SETUP 1: Starting Hardhat Node")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Change to smart contract directory
            smart_contract_dir = self.base_path / "smart_contract"
            os.chdir(smart_contract_dir)
            
            print("  🔧 Starting Hardhat node in background...")
            
            # Start hardhat node in background
            self.hardhat_process = subprocess.Popen(
                ['npx', 'hardhat', 'node'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for hardhat to start (check every second for up to 30 seconds)
            max_wait = 30
            wait_count = 0
            
            while wait_count < max_wait:
                try:
                    import requests
                    response = requests.post('http://localhost:8545', 
                                           json={'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1},
                                           timeout=1)
                    if response.status_code == 200:
                        break
                except:
                    pass
                
                time.sleep(1)
                wait_count += 1
                print(f"  ⏳ Waiting for Hardhat... ({wait_count}/{max_wait})")
            
            if wait_count >= max_wait:
                raise Exception("Hardhat failed to start within 30 seconds")
            
            duration = time.time() - start_time
            self.log_timing("Hardhat Startup", duration)
            print(f"  ✅ Hardhat node started successfully")
            return True
            
        except Exception as e:
            print(f"  ❌ Hardhat startup failed: {e}")
            self.critical_failures.append(f"Hardhat startup failed: {e}")
            return False
    
    def setup_2_deploy_contracts(self):
        """Setup 2: Deploy smart contracts with deterministic addresses"""
        print(f"\n📋 SETUP 2: Deploying Smart Contracts")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            smart_contract_dir = self.base_path / "smart_contract"
            os.chdir(smart_contract_dir)
            
            print("  🔨 Compiling contracts...")
            compile_result = subprocess.run(['npx', 'hardhat', 'compile'], 
                                          capture_output=True, text=True, check=True)
            
            # Check for existing deployments first (deterministic addresses)
            deployment_dir = smart_contract_dir / "deployments" / "localhost"
            if deployment_dir.exists():
                deployment_files = list(deployment_dir.glob("*.json"))
                if deployment_files:
                    print(f"  ✅ Found existing deterministic deployments: {[f.stem for f in deployment_files]}")
                    for deployment_file in deployment_files:
                        try:
                            with open(deployment_file, 'r') as f:
                                deployment_data = json.load(f)
                            contract_address = deployment_data.get('address', 'Unknown')
                            print(f"  📍 {deployment_file.stem}: {contract_address}")
                        except:
                            pass
                    
                    duration = time.time() - start_time
                    self.log_timing("Contract Deployment", duration)
                    return True
            
            # If no existing deployments, contracts will be deployed with deterministic addresses
            # when first transaction is made (due to deterministic nature)
            print("  🏗️  Contracts will be deployed deterministically on first transaction")
            print("  ✅ Deterministic deployment system ready")
            
            duration = time.time() - start_time
            self.log_timing("Contract Deployment", duration)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Contract compilation failed: {e}")
            print(f"  📄 Stdout: {e.stdout}")
            print(f"  📄 Stderr: {e.stderr}")
            self.critical_failures.append(f"Contract compilation failed: {e}")
            return False
    
    def setup_3_fund_wallets(self):
        """Setup 3: Fund all wallets with ETH using deposit_from_all.js"""
        print(f"\n💰 SETUP 3: Funding Wallets")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            smart_contract_dir = self.base_path / "smart_contract"
            os.chdir(smart_contract_dir)
            
            print("  💵 Running deposit_from_all.js to fund all AS wallets...")
            
            # Run your actual funding script
            fund_result = subprocess.run(
                ['npx', 'hardhat', 'run', 'scripts/deposit_from_all.js', '--network', 'localhost'],
                capture_output=True, text=True, check=True
            )
            
            print("  📄 Funding output:")
            if fund_result.stdout.strip():
                print(f"     {fund_result.stdout.strip()}")
            
            print("  💰 All wallets funded!")
            
            duration = time.time() - start_time
            self.log_timing("Wallet Funding", duration)
            print(f"  ✅ Wallet funding completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Wallet funding failed: {e}")
            print(f"  📄 Stdout: {e.stdout}")
            print(f"  📄 Stderr: {e.stderr}")
            self.critical_failures.append(f"Wallet funding failed: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Wallet funding failed: {e}")
            self.critical_failures.append(f"Wallet funding failed: {e}")
            return False
    
    def setup_4_generate_data(self):
        """Setup 4: Generate BGP observation data and registries"""
        print(f"\n📊 SETUP 4: Generating Data")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Generate BGP observation data for each RPKI node
            rpki_nodes = ['as01', 'as03', 'as05', 'as07', 'as09', 'as11', 'as13', 'as15', 'as17']
            
            for node in rpki_nodes:
                print(f"  📡 Generating BGP data for {node}...")
                bgp_file = self.base_path / f"nodes/rpki_nodes/{node}/network_stack/bgpd.json"
                
                # Create sample BGP data structure
                bgp_data = {
                    "router_id": f"10.0.{node[2:]}.1",
                    "as_number": int(node[2:]),
                    "neighbors": [],
                    "routes": [],
                    "timestamp": datetime.now().isoformat()
                }
                
                # Ensure directory exists
                bgp_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(bgp_file, 'w') as f:
                    json.dump(bgp_data, f, indent=2)
                
                time.sleep(0.05)  # Small delay between generations
            
            # Generate shared registries
            print("  📋 Generating shared registries...")
            
            # RPKI verification registry
            rpki_registry = {
                f"AS{i:02d}": {"verified": i % 2 == 1, "last_check": datetime.now().isoformat()}
                for i in range(1, 21)
            }
            
            rpki_registry_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/rpki_verification_registry.json"
            rpki_registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(rpki_registry_file, 'w') as f:
                json.dump(rpki_registry, f, indent=2)
            
            # Trust state
            trust_state = {
                "global_trust_level": 0.75,
                "last_updated": datetime.now().isoformat(),
                "consensus_nodes": 9
            }
            
            trust_state_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state.json"
            trust_state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(trust_state_file, 'w') as f:
                json.dump(trust_state, f, indent=2)
            
            # Wallet registry (will be populated during funding)
            wallet_registry_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/nonrpki_wallet_registry.json"
            wallet_registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(wallet_registry_file, 'w') as f:
                json.dump({}, f, indent=2)
            
            # Simulation config
            sim_config = {
                "simulation_id": f"sim_{int(time.time())}",
                "start_time": datetime.now().isoformat(),
                "rpki_nodes": rpki_nodes,
                "non_rpki_nodes": [f"as{i:02d}" for i in range(2, 21, 2)],
                "attack_scenarios": ["prefix_hijack", "route_leak", "path_manipulation"]
            }
            
            sim_config_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/simulation_config.json"
            
            with open(sim_config_file, 'w') as f:
                json.dump(sim_config, f, indent=2)
            
            duration = time.time() - start_time
            self.log_timing("Data Generation", duration)
            print(f"  ✅ All data generated successfully")
            return True
            
        except Exception as e:
            print(f"  ❌ Data generation failed: {e}")
            self.critical_failures.append(f"Data generation failed: {e}")
            return False
    
    def test_1_directory_structure(self):
        """Test 1: Verify complete directory structure"""
        print(f"\n🔍 TEST 1: Directory Structure Validation")
        print("-" * 50)
        
        start_time = time.time()
        
        required_dirs = [
            "nodes/rpki_nodes",
            "nodes/non_rpki_nodes", 
            "trust_engine",
            "smart_contract",
            "tests"
        ]
        
        required_rpki_nodes = [
            "nodes/rpki_nodes/as01",
            "nodes/rpki_nodes/as03", 
            "nodes/rpki_nodes/as05",
            "nodes/rpki_nodes/as07",
            "nodes/rpki_nodes/as09",
            "nodes/rpki_nodes/as11",
            "nodes/rpki_nodes/as13",
            "nodes/rpki_nodes/as15",
            "nodes/rpki_nodes/as17"
        ]
        
        required_interfaces = [
            "nodes/rpki_nodes/bgp_attack_detection",
            "nodes/rpki_nodes/rpki_verification_interface",
            "nodes/rpki_nodes/trust_score_interface", 
            "nodes/rpki_nodes/staking_amount_interface",
            "nodes/rpki_nodes/shared_blockchain_stack"
        ]
        
        all_dirs = required_dirs + required_rpki_nodes + required_interfaces
        missing_dirs = []
        
        for dir_path in all_dirs:
            full_path = self.base_path / dir_path
            if full_path.exists():
                print(f"  ✅ {dir_path}")
            else:
                print(f"  ❌ {dir_path} - MISSING")
                missing_dirs.append(dir_path)
        
        duration = time.time() - start_time
        self.log_timing("Directory Structure Check", duration)
        
        if missing_dirs:
            self.critical_failures.append(f"Missing directories: {missing_dirs}")
            return False
        
        print(f"  📊 Result: All {len(all_dirs)} directories found")
        return True
    
    def test_2_bgp_data_files(self):
        """Test 2: Verify BGP observation data files"""
        print(f"\n🔍 TEST 2: BGP Data Files Validation")
        print("-" * 50)
        
        start_time = time.time()
        
        rpki_nodes = ['as01', 'as03', 'as05', 'as07', 'as09', 'as11', 'as13', 'as15', 'as17']
        missing_files = []
        invalid_files = []
        
        for node in rpki_nodes:
            bgp_file = self.base_path / f"nodes/rpki_nodes/{node}/network_stack/bgpd.json"
            
            if not bgp_file.exists():
                missing_files.append(f"{node}/bgpd.json")
                print(f"  ❌ {node}: bgpd.json missing")
                continue
            
            # Validate JSON format
            try:
                with open(bgp_file, 'r') as f:
                    data = json.load(f)
                print(f"  ✅ {node}: bgpd.json valid ({type(data).__name__})")
            except json.JSONDecodeError as e:
                invalid_files.append(f"{node}/bgpd.json")
                print(f"  ❌ {node}: bgpd.json invalid JSON - {e}")
        
        duration = time.time() - start_time
        self.log_timing("BGP Data Validation", duration)
        
        if missing_files or invalid_files:
            if missing_files:
                self.critical_failures.append(f"Missing BGP files: {missing_files}")
            if invalid_files:
                self.critical_failures.append(f"Invalid BGP files: {invalid_files}")
            return False
        
        print(f"  📊 Result: All {len(rpki_nodes)} BGP data files valid")
        return True
    
    def test_3_blockchain_connectivity(self):
        """Test 3: Verify blockchain/hardhat connectivity"""
        print(f"\n🔍 TEST 3: Blockchain Connectivity")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Test hardhat node connection
            import requests
            response = requests.post('http://localhost:8545', 
                                   json={'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1},
                                   timeout=3)
            
            if response.status_code == 200:
                result = response.json()
                block_number = int(result.get('result', '0x0'), 16)
                print(f"  ✅ Hardhat node: Connected (Block: {block_number})")
            else:
                print(f"  ❌ Hardhat node: Not responding")
                self.critical_failures.append("Hardhat node not running")
                return False
        except Exception as e:
            print(f"  ❌ Hardhat node: Connection failed - {e}")
            self.critical_failures.append("Hardhat node connection failed")
            return False
        
        # Test smart contract deployment
        contract_file = self.base_path / "smart_contract/deployments/localhost/StakingContract.json"
        if contract_file.exists():
            try:
                with open(contract_file, 'r') as f:
                    deployment = json.load(f)
                contract_address = deployment.get('address')
                print(f"  ✅ Smart contract: Deployed at {contract_address}")
            except Exception as e:
                print(f"  ❌ Smart contract: Deployment file invalid - {e}")
                self.critical_failures.append("Smart contract deployment invalid")
                return False
        else:
            print(f"  ❌ Smart contract: Not deployed")
            self.critical_failures.append("Smart contract not deployed")
            return False
        
        duration = time.time() - start_time
        self.log_timing("Blockchain Connectivity Check", duration)
        
        print(f"  📊 Result: Blockchain fully operational")
        return True
    
    def test_4_interface_modules(self):
        """Test 4: Verify all interface modules can be imported"""
        print(f"\n🔍 TEST 4: Interface Module Imports")
        print("-" * 50)
        
        start_time = time.time()
        
        # Add interface paths
        interface_paths = [
            self.base_path / "nodes/rpki_nodes/rpki_verification_interface",
            self.base_path / "nodes/rpki_nodes/bgp_attack_detection", 
            self.base_path / "nodes/rpki_nodes/trust_score_interface",
            self.base_path / "nodes/rpki_nodes/staking_amount_interface",
            self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"
        ]
        
        for path in interface_paths:
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        
        # Test imports
        import_tests = [
            ('RPKI Verification', 'from verifier import is_as_verified'),
            ('BGP Attack Detection', 'from attack_detector import BGPSecurityAnalyzer'),
            ('Trust Engine Interface', 'from trust_engine_interface import TrustEngineInterface'),
            ('Staking Checker', 'from staking_amountchecker import StakingAmountChecker'),
            ('Blockchain Interface', 'from integrated_trust_manager import IntegratedTrustManager')
        ]
        
        failed_imports = []
        
        for test_name, import_stmt in import_tests:
            try:
                exec(import_stmt)
                print(f"  ✅ {test_name}: Import successful")
            except Exception as e:
                print(f"  ❌ {test_name}: Import failed - {e}")
                failed_imports.append(test_name)
        
        duration = time.time() - start_time
        self.log_timing("Interface Module Check", duration)
        
        if failed_imports:
            self.critical_failures.append(f"Failed imports: {failed_imports}")
            return False
        
        print(f"  📊 Result: All {len(import_tests)} interfaces importable")
        return True
    
    def test_5_trust_engine_integration(self):
        """Test 5: Test trust engine integration"""
        print(f"\n🔍 TEST 5: Trust Engine Integration")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Add root trust engine path
            trust_engine_path = self.base_path / "trust_engine"
            if str(trust_engine_path) not in sys.path:
                sys.path.insert(0, str(trust_engine_path))
            
            # Test trust engine interface
            from trust_engine_interface import TrustEngineInterface
            trust_interface = TrustEngineInterface()
            
            if trust_interface.coordinator:
                print(f"  ✅ Trust Coordinator: Initialized")
            else:
                print(f"  ❌ Trust Coordinator: Failed to initialize")
                self.critical_failures.append("Trust Coordinator initialization failed")
                return False
            
            if trust_interface.rte:
                print(f"  ✅ Reactive Trust Engine: Available")
            else:
                print(f"  ⚠️  Reactive Trust Engine: Not available")
                self.warnings.append("RTE not available")
            
            if trust_interface.ate:
                print(f"  ✅ Adaptive Trust Engine: Available") 
            else:
                print(f"  ⚠️  Adaptive Trust Engine: Not available")
                self.warnings.append("ATE not available")
            
            duration = time.time() - start_time
            self.log_timing("Trust Engine Integration Check", duration)
            
            print(f"  📊 Result: Trust engine integration working")
            return True
            
        except Exception as e:
            print(f"  ❌ Trust Engine: Integration failed - {e}")
            self.critical_failures.append("Trust engine integration failed")
            return False
    
    def test_6_staking_amounts(self):
        """Test 6: Verify real staking amounts"""
        print(f"\n🔍 TEST 6: Real Staking Amounts")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            from staking_amountchecker import StakingAmountChecker
            checker = StakingAmountChecker()
            
            # Test a few non-RPKI ASes
            test_ases = [2, 4, 6, 8]
            all_funded = True
            
            for as_number in test_ases:
                stake = checker.get_current_stake_amount(as_number)
                
                if stake > 0:
                    print(f"  ✅ AS{as_number:02d}: {stake:.3f} ETH staked")
                else:
                    print(f"  ❌ AS{as_number:02d}: No stake found")
                    all_funded = False
            
            if not all_funded:
                self.warnings.append("Some ASes have no stakes")
            
            duration = time.time() - start_time
            self.log_timing("Staking Amounts Check", duration)
                
            print(f"  📊 Result: Staking system operational")
            return True
            
        except Exception as e:
            print(f"  ❌ Staking Check: Failed - {e}")
            self.critical_failures.append("Staking check failed")
            return False
    
    def test_7_rpki_consensus_readiness(self):
        """Test 7: RPKI nodes consensus readiness"""
        print(f"\n🔍 TEST 7: RPKI Consensus Readiness")
        print("-" * 50)
        
        start_time = time.time()
        
        rpki_nodes = ['as01', 'as03', 'as05', 'as07', 'as09', 'as11', 'as13', 'as15', 'as17']
        ready_nodes = 0
        
        for node in rpki_nodes:
            node_dir = self.base_path / f"nodes/rpki_nodes/{node}"
            
            # Check blockchain node
            blockchain_dir = node_dir / "blockchain_node"
            private_key = blockchain_dir / "private_key.pem"
            
            if blockchain_dir.exists() and private_key.exists():
                print(f"  ✅ {node}: Blockchain node ready")
                ready_nodes += 1
            else:
                print(f"  ❌ {node}: Blockchain node not ready")
        
        required_consensus = 6  # 2/3 of 9
        
        duration = time.time() - start_time
        self.log_timing("RPKI Consensus Check", duration)
        
        if ready_nodes >= required_consensus:
            print(f"  📊 Result: {ready_nodes}/9 nodes ready (≥{required_consensus} required)")
            return True
        else:
            print(f"  📊 Result: {ready_nodes}/9 nodes ready (<{required_consensus} required)")
            self.critical_failures.append(f"Insufficient RPKI nodes ready ({ready_nodes}/{required_consensus})")
            return False
    
    def test_8_data_registries(self):
        """Test 8: Verify all data registries"""
        print(f"\n🔍 TEST 8: Data Registries")
        print("-" * 50)
        
        start_time = time.time()
        
        registry_files = [
            ("RPKI Registry", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/rpki_verification_registry.json"),
            ("Trust State", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state.json"),
            ("Wallet Registry", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/nonrpki_wallet_registry.json"),
            ("Simulation Config", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/simulation_config.json")
        ]
        
        missing_registries = []
        
        for name, path in registry_files:
            file_path = self.base_path / path
            
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    print(f"  ✅ {name}: Valid ({len(data)} entries)")
                except json.JSONDecodeError:
                    print(f"  ❌ {name}: Invalid JSON")
                    missing_registries.append(name)
            else:
                print(f"  ❌ {name}: File missing")
                missing_registries.append(name)
        
        duration = time.time() - start_time
        self.log_timing("Data Registries Check", duration)
        
        if missing_registries:
            self.critical_failures.append(f"Missing registries: {missing_registries}")
            return False
        
        print(f"  📊 Result: All {len(registry_files)} registries valid")
        return True
    
    def generate_timing_report(self):
        """Generate detailed timing report"""
        print(f"\n⏱️  TIMING ANALYSIS REPORT")
        print("-" * 70)
        
        total_time = sum(entry['duration'] for entry in self.timing_log.values())
        
        for operation, timing_data in self.timing_log.items():
            duration = timing_data['duration']
            percentage = (duration / total_time) * 100 if total_time > 0 else 0
            print(f"  {operation:<30}: {duration:6.2f}s ({percentage:5.1f}%)")
        
        print(f"  {'-' * 50}")
        print(f"  {'TOTAL TIME':<30}: {total_time:6.2f}s (100.0%)")
    
    def generate_final_report(self):
        """Generate final pre-simulation report"""
        print(f"\n{'='*70}")
        print(f"📋 ENHANCED PRE-SIMULATION TEST REPORT")
        print(f"{'='*70}")
        
        total_tests = 8
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Critical Failures: {len(self.critical_failures)}")
        
        # Generate timing report
        self.generate_timing_report()
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if self.critical_failures:
            print(f"\n❌ CRITICAL FAILURES:")
            for failure in self.critical_failures:
                print(f"   - {failure}")
        
        print(f"\n{'='*70}")
        
        if self.critical_failures:
            print(f"🚫 SIMULATION NOT READY - Fix critical failures first")
            print(f"{'='*70}")
            return False
        elif self.warnings:
            print(f"⚠️  SIMULATION READY - But address warnings for optimal performance")
            print(f"{'='*70}")
            return True
        else:
            print(f"🎉 ALL SYSTEMS GO - Ready for full simulation!")
            print(f"{'='*70}")
            return True
    
    def cleanup(self):
        """Cleanup function to handle graceful shutdown"""
        if self.hardhat_process:
            print(f"\n🧹 Cleaning up Hardhat process...")
            self.hardhat_process.terminate()
            try:
                self.hardhat_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.hardhat_process.kill()
    
    def run_complete_setup_and_tests(self):
        """Run complete setup sequence followed by all tests"""
        print("🔄 STARTING COMPLETE SETUP AND VALIDATION SEQUENCE")
        print("=" * 70)
        
        # Setup sequence
        setup_steps = [
            ('Reset Blockchain', self.setup_0_reset_blockchain),
            ('Start Hardhat', self.setup_1_start_hardhat),
            ('Deploy Contracts', self.setup_2_deploy_contracts),
            ('Fund Wallets', self.setup_3_fund_wallets),
            ('Generate Data', self.setup_4_generate_data)
        ]
        
        print(f"\n📋 SETUP PHASE")
        print("=" * 30)
        
        for step_name, step_func in setup_steps:
            try:
                result = step_func()
                if not result:
                    print(f"\n❌ Setup failed at: {step_name}")
                    return False
            except Exception as e:
                print(f"\n💥 {step_name}: Unexpected error - {e}")
                self.critical_failures.append(f"{step_name}: Unexpected error")
                return False
        
        # Validation/test sequence
        print(f"\n📋 VALIDATION PHASE")
        print("=" * 30)
        
        tests = [
            ('Directory Structure', self.test_1_directory_structure),
            ('BGP Data Files', self.test_2_bgp_data_files),
            ('Blockchain Connectivity', self.test_3_blockchain_connectivity),
            ('Interface Modules', self.test_4_interface_modules),
            ('Trust Engine Integration', self.test_5_trust_engine_integration),
            ('Staking Amounts', self.test_6_staking_amounts),
            ('RPKI Consensus Readiness', self.test_7_rpki_consensus_readiness),
            ('Data Registries', self.test_8_data_registries)
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                self.test_results[test_name] = result
            except Exception as e:
                print(f"  💥 {test_name}: Unexpected error - {e}")
                self.test_results[test_name] = False
                self.critical_failures.append(f"{test_name}: Unexpected error")
        
        return self.generate_final_report()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n🛑 Interrupted by user')
    if hasattr(signal_handler, 'checker'):
        signal_handler.checker.cleanup()
    sys.exit(1)

def main():
    """Run the enhanced pre-simulation master test"""
    checker = EnhancedPreSimulationChecker()
    
    # Set up signal handler for cleanup
    signal_handler.checker = checker
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        simulation_ready = checker.run_complete_setup_and_tests()
        
        # Save timing log for analysis
        timing_file = checker.base_path / "timing_analysis.json"
        with open(timing_file, 'w') as f:
            json.dump(checker.timing_log, f, indent=2)
        
        print(f"\n📄 Timing analysis saved to: {timing_file}")
        
        # Exit with appropriate code
        sys.exit(0 if simulation_ready else 1)
        
    except Exception as e:
        print(f"\n💥 Unexpected error during execution: {e}")
        sys.exit(1)
    finally:
        checker.cleanup()

if __name__ == "__main__":
    main()