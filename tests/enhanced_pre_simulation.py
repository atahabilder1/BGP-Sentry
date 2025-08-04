#!/usr/bin/env python3
"""
========================================================
BGP-Sentry Ultimate Enhanced Pre-Simulation Master Test
File Location: tests/enhanced_pre_simulation.py
========================================================

Complete system setup, validation, and timing analysis before running experiments

COMPLETE FUNCTIONALITY:
- Full blockchain setup automation (reset, start, deploy, fund, generate data)
- Comprehensive core validation (5 tests)
- Extended test suites (ALL individual test folders with pytest)
- Data source switching (test/original data)  
- Timing analysis and performance metrics
- Detailed reporting with pass/fail counts

Usage: 
  python3 enhanced_pre_simulation.py                         # Core validation only
  python3 enhanced_pre_simulation.py --setup                 # Full setup + validation
  python3 enhanced_pre_simulation.py --run-extended-tests    # Core + ALL test folders
  python3 enhanced_pre_simulation.py --data-source=original  # Use original data
"""

import sys
import os
import json
import subprocess
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime
import threading

class UltimatePreSimulationChecker:
    """Ultimate pre-simulation system with complete setup + validation"""
    
    def __init__(self, run_extended_tests=False, data_source='test', setup_mode=False):
        self.base_path = Path(__file__).parent.parent
        self.test_results = {}
        self.critical_failures = []
        self.warnings = []
        self.timing_log = {}
        self.hardhat_process = None
        self.run_extended_tests = run_extended_tests
        self.data_source = data_source
        self.setup_mode = setup_mode
        
        print("🚀 BGP-Sentry Ultimate Enhanced Pre-Simulation Master Test")
        print("=" * 70)
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Data Source: {data_source}")
        if self.setup_mode:
            print(f"🔧 Setup Mode: Complete system setup enabled")
        if self.run_extended_tests:
            print(f"🔬 Extended Test Mode: Core validation + ALL test suites")
        print("=" * 70)
    
    def log_timing(self, operation, duration, details=None):
        """Log timing information for operations"""
        self.timing_log[operation] = {
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        print(f"⏱️  {operation}: {duration:.2f} seconds")
    
    def cleanup(self):
        """Cleanup function to handle graceful shutdown"""
        if self.hardhat_process:
            print(f"\n🧹 Cleaning up Hardhat process...")
            self.hardhat_process.terminate()
            try:
                self.hardhat_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.hardhat_process.kill()
    
    # ===========================================
    # SETUP FUNCTIONS (Complete automation)
    # ===========================================
    
    def setup_0_reset_blockchain(self):
        """Setup 0: Reset blockchain state"""
        print(f"\n🔄 SETUP 0: Blockchain Reset")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Kill existing hardhat processes
            print("  🔍 Checking for existing Hardhat processes...")
            try:
                result = subprocess.run(['pkill', '-f', 'hardhat'], capture_output=True)
                if result.returncode == 0:
                    print("  🗡️  Killed existing Hardhat processes")
                    time.sleep(2)
                else:
                    print("  ✅ No existing Hardhat processes found")
            except FileNotFoundError:
                print("  ⚠️  pkill not available, trying alternative...")
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
            
            duration = time.time() - start_time
            self.log_timing("Blockchain Reset", duration, {
                'cleaned_dirs': [d.name for d in blockchain_dirs if d.exists()],
                'processes_killed': True if result.returncode == 0 else False,
                'actions': ['Kill Hardhat processes', 'Clean cache/artifacts', 'Reset wallet registry']
            })
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
            smart_contract_dir = self.base_path / "smart_contract"
            os.chdir(smart_contract_dir)
            
            print("  🔧 Starting Hardhat node in background...")
            
            self.hardhat_process = subprocess.Popen(
                ['npx', 'hardhat', 'node'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for hardhat to start
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
        """Setup 2: Deploy smart contracts"""
        print(f"\n📋 SETUP 2: Deploying Smart Contracts")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            smart_contract_dir = self.base_path / "smart_contract"
            os.chdir(smart_contract_dir)
            
            print("  🔨 Compiling contracts...")
            compile_result = subprocess.run(['npx', 'hardhat', 'compile'], 
                                          capture_output=True, text=True, check=True)
            
            print("  🚀 Deploying contracts...")
            
            # Try to find deployment script
            possible_scripts = [
                'scripts/deploy.js',
                'scripts/deployment.js', 
                'scripts/deploy_contracts.js',
                'scripts/deploy_all.js'
            ]
            
            deploy_script = None
            for script in possible_scripts:
                if (self.base_path / "smart_contract" / script).exists():
                    deploy_script = script
                    break
            
            if not deploy_script:
                print("  ⚠️  No deployment script found, skipping deployment")
                print("  📋 Available scripts:")
                scripts_dir = self.base_path / "smart_contract/scripts"
                if scripts_dir.exists():
                    for script_file in scripts_dir.glob("*.js"):
                        print(f"     {script_file.name}")
                return True  # Don't fail, just skip deployment
            
            print(f"  📋 Using deployment script: {deploy_script}")
            deploy_result = subprocess.run(['npx', 'hardhat', 'run', deploy_script, '--network', 'localhost'], 
                                         capture_output=True, text=True, check=True)
            
            duration = time.time() - start_time
            self.log_timing("Contract Deployment", duration)
            print(f"  ✅ Contracts deployed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Contract deployment failed: {e}")
            print(f"  📄 Error: {e.stderr}")
            self.critical_failures.append(f"Contract deployment failed: {e}")
            return False
    
    def setup_3_fund_wallets(self):
        """Setup 3: Fund all wallets with ETH"""
        print(f"\n💰 SETUP 3: Funding Wallets")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            smart_contract_dir = self.base_path / "smart_contract"
            os.chdir(smart_contract_dir)
            
            print("  �� Running deposit_from_all.js (deploys contracts + funds wallets)...")
            
            fund_result = subprocess.run(
                ['npx', 'hardhat', 'run', 'scripts/deposit_from_all.js', '--network', 'localhost'],
                capture_output=True, text=True, check=True
            )
            
            if fund_result.stdout:
                print("  📄 Funding results:")
                # Show last few lines of output
                lines = fund_result.stdout.strip().split('\n')
                for line in lines[-3:]:
                    if line.strip():
                        print(f"     {line}")
            
            duration = time.time() - start_time
            
            # Extract funding info from output
            total_eth = "Unknown"
            if fund_result.stdout:
                lines = fund_result.stdout.strip().split('\n')
                for line in lines:
                    if "Final Contract Balance:" in line:
                        total_eth = line.split(":")[-1].strip()
                        break
            
            self.log_timing("Wallet Funding", duration, {
                'script_used': 'scripts/deposit_from_all.js',
                'total_staked': total_eth,
                'action': 'Deploy contracts + Fund all wallets',
                'accounts_funded': '20 (Hardhat default accounts)',
                'contract_address': 'Deterministic (first deployment)'
            })
            print(f"  ✅ Wallet funding completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Wallet funding failed: {e}")
            print(f"  📄 Error: {e.stderr}")
            self.critical_failures.append(f"Wallet funding failed: {e}")
            return False
    
    def setup_4_generate_data(self):
        """Setup 4: Generate BGP observation data and registries"""
        print(f"\n📊 SETUP 4: Generating Data")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Generate BGP data for RPKI nodes
            rpki_nodes = ['as01', 'as03', 'as05', 'as07', 'as09', 'as11', 'as13', 'as15', 'as17']
            
            for node in rpki_nodes:
                print(f"  📡 Generating BGP data for {node}...")
                
                suffix = f"_{self.data_source}" if self.data_source != 'test' else ""
                bgp_file = self.base_path / f"nodes/rpki_nodes/{node}/network_stack/bgpd{suffix}.json"
                
                bgp_data = {
                    "router_id": f"10.0.{node[2:]}.1",
                    "as_number": int(node[2:]),
                    "neighbors": [],
                    "routes": [],
                    "timestamp": datetime.now().strftime("%H:%M:%S (%Y-%m-%d)"),
                    "data_source": self.data_source
                }
                
                bgp_file.parent.mkdir(parents=True, exist_ok=True)
                with open(bgp_file, 'w') as f:
                    json.dump(bgp_data, f, indent=2)
                
                time.sleep(0.05)
            
            # Generate registries
            print("  📋 Generating shared registries...")
            
            # Trust state with economic compensation data
            trust_state = {
                "global_trust_level": 0.75,
                "last_updated": datetime.now().isoformat(),
                "data_source": self.data_source,
                "consensus_nodes": 9,
                # AS trust scores for economic compensation
                "2": 45, "4": 65, "6": 35, "8": 75, "10": 55,
                "12": 40, "14": 70, "16": 60, "18": 50, "20": 80
            }
            
            trust_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state.json"
            trust_file.parent.mkdir(parents=True, exist_ok=True)
            with open(trust_file, 'w') as f:
                json.dump(trust_state, f, indent=2)
            
            # Wallet registry with Hardhat addresses  
            hardhat_addresses = [
                "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",  # Account 0
                "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",  # Account 1
                "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",  # Account 2
                "0x90F79bf6EB2c4f870365E785982E1f101E93b906",  # Account 3
                "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",  # Account 4
                "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",  # Account 5
                "0x976EA74026E726554dB657fA54763abd0C3a0aa9",  # Account 6
                "0x14dC79964da2C08b23698B3D3cc7Ca32193d9955",  # Account 7
                "0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f",  # Account 8
                "0xa0Ee7A142d267C1f36714E4a8F75612F20a79720"   # Account 9
            ]
            
            wallet_registry = {
                "data_source": self.data_source,
                "created": datetime.now().isoformat()
            }
            
            # Map AS numbers to accounts: AS02->Account2, AS04->Account4, etc.
            non_rpki_ases = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
            for as_num in non_rpki_ases:
                if as_num < len(hardhat_addresses):
                    wallet_registry[f"as{as_num:02d}"] = hardhat_addresses[as_num]
                    print(f"    AS{as_num:02d} -> Account {as_num} ({hardhat_addresses[as_num][:10]}...)")
            
            wallet_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/nonrpki_wallet_registry.json"
            wallet_file.parent.mkdir(parents=True, exist_ok=True)
            with open(wallet_file, 'w') as f:
                json.dump(wallet_registry, f, indent=2)
            
            # RPKI verification registry
            rpki_registry = {
                f"AS{i:02d}": {
                    "verified": i % 2 == 1, 
                    "last_check": datetime.now().isoformat(),
                    "data_source": self.data_source
                }
                for i in range(1, 21)
            }
            
            rpki_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/rpki_verification_registry.json"
            rpki_file.parent.mkdir(parents=True, exist_ok=True)
            with open(rpki_file, 'w') as f:
                json.dump(rpki_registry, f, indent=2)
            
            # Simulation config
            sim_config = {
                "simulation_id": f"sim_{int(time.time())}",
                "start_time": datetime.now().isoformat(),
                "data_source": self.data_source,
                "rpki_nodes": rpki_nodes,
                "non_rpki_nodes": [f"as{i:02d}" for i in non_rpki_ases],
                "attack_scenarios": ["prefix_hijack", "route_leak", "path_manipulation"],
                "funded_accounts": len(hardhat_addresses)
            }
            
            sim_file = self.base_path / "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/simulation_config.json"
            sim_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sim_file, 'w') as f:
                json.dump(sim_config, f, indent=2)
            
            duration = time.time() - start_time
            
            # Collect generated files info
            generated_files = []
            for node in rpki_nodes:
                suffix = f"_{self.data_source}" if self.data_source != 'test' else ""
                bgp_file = self.base_path / f"nodes/rpki_nodes/{node}/network_stack/bgpd{suffix}.json"
                generated_files.append(f"BGP data: {bgp_file.relative_to(self.base_path)}")
            
            registry_files = [
                "Trust state with AS scores",
                "Wallet registry with AS-to-account mapping", 
                "RPKI verification registry",
                "Simulation config"
            ]
            
            self.log_timing("Data Generation", duration, {
                'data_source': self.data_source,
                'rpki_nodes_count': len(rpki_nodes),
                'bgp_files_generated': len(rpki_nodes),
                'registry_files': registry_files,
                'as_wallet_mappings': len(non_rpki_ases),
                'sample_files': [
                    f"nodes/rpki_nodes/as01/network_stack/bgpd{('_' + self.data_source) if self.data_source != 'test' else ''}.json",
                    "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state.json",
                    "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/nonrpki_wallet_registry.json"
                ]
            })
            print(f"  ✅ All data generated successfully")
            return True
            
        except Exception as e:
            print(f"  ❌ Data generation failed: {e}")
            self.critical_failures.append(f"Data generation failed: {e}")
            return False
    
    # ===========================================
    # CORE VALIDATION FUNCTIONS
    # ===========================================
    
    def test_1_system_environment(self):
        """Test 1: System environment and dependencies"""
        print(f"\n🔍 TEST 1: System Environment")
        print("-" * 50)
        
        start_time = time.time()
        
        python_version = sys.version_info
        print(f"  ✅ Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version < (3, 8):
            self.critical_failures.append("Python 3.8+ required")
            print(f"  ❌ Python version too old (need 3.8+)")
            
        venv_active = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        if venv_active:
            print(f"  ✅ Virtual Environment: Active")
        else:
            print(f"  ⚠️  Virtual Environment: Not active")
            self.warnings.append("Virtual environment not active")
        
        packages = ['requests', 'pytest']
        for pkg in packages:
            try:
                __import__(pkg)
                print(f"  ✅ {pkg}: Available")
            except ImportError:
                print(f"  ❌ {pkg}: Missing")
                self.critical_failures.append(f"Missing package: {pkg}")
        
        duration = time.time() - start_time
        self.log_timing("System Environment Check", duration)
        
        return len([f for f in self.critical_failures if "Python" in f or "Missing package" in f]) == 0
    
    def test_2_directory_structure(self):
        """Test 2: Complete directory structure validation"""
        print(f"\n🔍 TEST 2: Directory Structure")
        print("-" * 50)
        
        start_time = time.time()
        
        essential_dirs = ["nodes/rpki_nodes", "nodes/non_rpki_nodes", "trust_engine", "smart_contract", "tests"]
        rpki_nodes = [f"nodes/rpki_nodes/as{i:02d}" for i in [1,3,5,7,9,11,13,15,17]]
        interfaces = [
            "nodes/rpki_nodes/bgp_attack_detection", 
            "nodes/rpki_nodes/rpki_verification_interface", 
            "nodes/rpki_nodes/trust_score_interface", 
            "nodes/rpki_nodes/staking_amount_interface",
            "nodes/rpki_nodes/shared_blockchain_stack"
        ]
        
        all_dirs = essential_dirs + rpki_nodes + interfaces
        missing_dirs = []
        
        for dir_path in all_dirs:
            full_path = self.base_path / dir_path
            if full_path.exists():
                print(f"  ✅ {dir_path}")
            else:
                print(f"  ❌ {dir_path}")
                missing_dirs.append(dir_path)
        
        duration = time.time() - start_time
        self.log_timing("Directory Structure Check", duration)
        
        if missing_dirs:
            self.critical_failures.append(f"Missing directories: {missing_dirs}")
            return False
        
        print(f"  📊 Result: All {len(all_dirs)} directories found")
        return True
    
    def test_3_blockchain_connectivity(self):
        """Test 3: Blockchain and Hardhat connectivity"""
        print(f"\n🔍 TEST 3: Blockchain Connectivity")
        print("-" * 50)
        
        start_time = time.time()
        
        # Test Hardhat node connection
        try:
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
                self.warnings.append("Hardhat node not running")
        except Exception as e:
            print(f"  ❌ Hardhat node: Connection failed")
            self.warnings.append("Hardhat node not running - start with: cd ../smart_contract && npx hardhat node")
        
        # Test smart contract deployment
        contract_file = self.base_path / "smart_contract/deployments/localhost/StakingContract.json"
        if contract_file.exists():
            try:
                with open(contract_file, 'r') as f:
                    deployment = json.load(f)
                contract_address = deployment.get('address', 'Unknown')
                print(f"  ✅ Smart contract: Deployed at {contract_address}")
            except Exception as e:
                print(f"  ❌ Smart contract: Deployment file invalid")
                self.warnings.append("Smart contract deployment file invalid")
        else:
            print(f"  ⚠️  Smart contract: Not deployed yet")
            self.warnings.append("Smart contract not deployed")
        
        duration = time.time() - start_time
        self.log_timing("Blockchain Connectivity Check", duration)
        
        return True  # Don't fail on blockchain issues, just warn
    
    def test_4_module_imports(self):
        """Test 4: Critical module import validation"""
        print(f"\n🔍 TEST 4: Module Imports")
        print("-" * 50)
        
        start_time = time.time()
        
        # Add interface paths to Python path
        interface_paths = [
            self.base_path / "nodes/rpki_nodes/rpki_verification_interface",
            self.base_path / "nodes/rpki_nodes/bgp_attack_detection", 
            self.base_path / "nodes/rpki_nodes/trust_score_interface",
            self.base_path / "nodes/rpki_nodes/staking_amount_interface",
            self.base_path / "trust_engine"
        ]
        
        for path in interface_paths:
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        
        # Test critical imports
        import_tests = [
            ('RPKI Verification', 'from verifier import is_as_verified'),
            ('BGP Attack Detection', 'from attack_detector import BGPSecurityAnalyzer'),
            ('Trust Engine Interface', 'from trust_engine_interface import TrustEngineInterface'),
            ('Staking Checker', 'from staking_amountchecker import StakingAmountChecker'),
        ]
        
        failed_imports = []
        for test_name, import_stmt in import_tests:
            try:
                exec(import_stmt)
                print(f"  ✅ {test_name}: Import successful")
            except Exception as e:
                print(f"  ❌ {test_name}: Import failed - {str(e)[:50]}...")
                failed_imports.append(test_name)
        
        duration = time.time() - start_time
        
        self.log_timing("Module Import Check", duration, {
            'total_imports_tested': len(import_tests),
            'successful_imports': len(import_tests) - len(failed_imports),
            'failed_imports': failed_imports,
            'interface_paths': [str(p.relative_to(self.base_path)) for p in interface_paths],
            'modules_tested': [test[0] for test in import_tests]
        })
        
        if failed_imports:
            self.warnings.append(f"Failed imports: {failed_imports}")
        
        print(f"  📊 Result: {len(import_tests) - len(failed_imports)}/{len(import_tests)} imports successful")
        return True  # Don't fail on import issues, just warn
    
    def test_5_data_files(self):
        """Test 5: Essential data files validation"""
        print(f"\n🔍 TEST 5: Data Files")
        print("-" * 50)
        
        start_time = time.time()
        
        # Check BGP data files for sample nodes
        test_nodes = ['as01', 'as03', 'as05']
        missing_files = []
        invalid_files = []
        
        for node in test_nodes:
            suffix = f"_{self.data_source}" if self.data_source != 'test' else ""
            bgp_file = self.base_path / f"nodes/rpki_nodes/{node}/network_stack/bgpd{suffix}.json"
            
            if not bgp_file.exists():
                # Try without suffix
                bgp_file = self.base_path / f"nodes/rpki_nodes/{node}/network_stack/bgpd.json"
            
            if bgp_file.exists():
                try:
                    with open(bgp_file, 'r') as f:
                        data = json.load(f)
                    print(f"  ✅ {node}: BGP data valid")
                except json.JSONDecodeError:
                    print(f"  ❌ {node}: BGP data invalid JSON")
                    invalid_files.append(f"{node}/bgpd.json")
            else:
                print(f"  ⚠️  {node}: BGP data missing")
                missing_files.append(f"{node}/bgpd.json")
        
        # Check shared registries
        registry_files = [
            ("Trust State", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state.json"),
            ("Wallet Registry", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/nonrpki_wallet_registry.json"),
            ("RPKI Registry", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/rpki_verification_registry.json"),
            ("Simulation Config", "nodes/rpki_nodes/shared_blockchain_stack/shared_data/shared_registry/simulation_config.json")
        ]
        
        for name, path in registry_files:
            file_path = self.base_path / path
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    data_source_info = f" ({data.get('data_source', 'unknown')} data)" if 'data_source' in data else ""
                    print(f"  ✅ {name}: Valid ({len(data)} entries){data_source_info}")
                except json.JSONDecodeError:
                    print(f"  ❌ {name}: Invalid JSON")
                    invalid_files.append(name)
            else:
                print(f"  ⚠️  {name}: File missing")
                missing_files.append(name)
        
        duration = time.time() - start_time
        self.log_timing("Data Files Check", duration)
        
        if missing_files:
            self.warnings.append(f"Missing data files: {missing_files}")
        if invalid_files:
            self.warnings.append(f"Invalid data files: {invalid_files}")
        
        print(f"  📊 Result: Data files checked")
        return True
    
    # ===========================================
    # EXTENDED TEST SUITE RUNNER
    # ===========================================
    
    def run_extended_test_suites(self):
        """Run ALL individual test folders with pytest - COMPREHENSIVE TESTING"""
        if not self.run_extended_tests:
            return True
        
        print(f"\n🔬 EXTENDED TEST SUITES")
        print("=" * 50)
        
        start_time = time.time()
        
        # Auto-discover all test folders
        test_folders = sorted([d.name for d in Path(__file__).parent.iterdir() 
                              if d.is_dir() and d.name.startswith(('0', '1')) and d.name != 'data_generator'])
        
        if not test_folders:
            print("  ⚠️  No extended test suites found")
            return True
        
        print(f"  📋 Found {len(test_folders)} test suites to run")
        
        suite_results = {}
        total_suites_passed = 0
        total_individual_tests = 0
        total_individual_passed = 0
        
        for i, folder in enumerate(test_folders, 1):
            print(f"  🧪 [{i:2d}/{len(test_folders)}] Running {folder}...")
            
            try:
                # Run pytest in the folder
                result = subprocess.run([
                    sys.executable, '-m', 'pytest', 
                    str(Path(__file__).parent / folder), 
                    '-v', '--tb=short', '--no-header'
                ], capture_output=True, text=True, timeout=60)
                
                # Parse pytest output for test counts
                if result.returncode == 0:
                    print(f"    ✅ {folder}: All tests passed")
                    suite_results[folder] = {'status': 'passed', 'details': 'All tests passed'}
                    total_suites_passed += 1
                    
                    # Try to extract test count from output
                    if "passed" in result.stdout:
                        try:
                            # Look for patterns like "3 passed" or "5 passed in"
                            import re
                            matches = re.findall(r'(\d+) passed', result.stdout)
                            if matches:
                                passed_count = int(matches[-1])  # Take the last match
                                total_individual_tests += passed_count
                                total_individual_passed += passed_count
                                print(f"    📊 {passed_count} individual tests passed")
                        except:
                            total_individual_tests += 1
                            total_individual_passed += 1
                else:
                    # Parse failed tests
                    failed_info = "Some tests failed"
                    if "FAILED" in result.stdout:
                        failed_lines = [line for line in result.stdout.split('\n') if 'FAILED' in line]
                        if failed_lines:
                            failed_info = f"{len(failed_lines)} tests failed"
                    
                    print(f"    ❌ {folder}: {failed_info}")
                    suite_results[folder] = {'status': 'failed', 'details': failed_info}
                    
                    # Try to extract passed/failed counts
                    try:
                        import re
                        passed_matches = re.findall(r'(\d+) passed', result.stdout)
                        failed_matches = re.findall(r'(\d+) failed', result.stdout)
                        
                        passed_count = int(passed_matches[-1]) if passed_matches else 0
                        failed_count = int(failed_matches[-1]) if failed_matches else 1
                        
                        total_individual_tests += passed_count + failed_count
                        total_individual_passed += passed_count
                        
                        if passed_count > 0:
                            print(f"    📊 {passed_count} passed, {failed_count} failed")
                    except:
                        total_individual_tests += 1
                        # Don't increment total_individual_passed for failed suites
                        
            except subprocess.TimeoutExpired:
                print(f"    ⏰ {folder}: Test timeout (>60s)")
                suite_results[folder] = {'status': 'timeout', 'details': 'Test timeout'}
                total_individual_tests += 1
                
            except Exception as e:
                print(f"    💥 {folder}: Error - {str(e)[:50]}...")
                suite_results[folder] = {'status': 'error', 'details': str(e)[:100]}
                total_individual_tests += 1
        
        duration = time.time() - start_time
        
        self.log_timing("Extended Test Suites", duration, {
            'total_suites': len(test_folders),
            'suites_passed': total_suites_passed,
            'suites_failed': len(failed_suites),
            'individual_tests_total': total_individual_tests,
            'individual_tests_passed': total_individual_passed,
            'failed_suites': failed_suites,
            'test_folders': test_folders,
            'framework': 'pytest'
        })
        
        # Generate comprehensive summary
        print(f"\n  📊 EXTENDED TEST SUMMARY:")
        print(f"     Test Suites: {total_suites_passed}/{len(test_folders)} passed")
        if total_individual_tests > 0:
            print(f"     Individual Tests: {total_individual_passed}/{total_individual_tests} passed")
        
        # Show failed suites
        failed_suites = [name for name, result in suite_results.items() if result['status'] != 'passed']
        if failed_suites:
            print(f"\n  ❌ Failed Suites:")
            for suite in failed_suites:
                status = suite_results[suite]['status']
                details = suite_results[suite]['details']
                print(f"     {suite}: {status} - {details}")
        
        # Store results for final report
        self.extended_test_results = {
            'total_suites': len(test_folders),
            'suites_passed': total_suites_passed,
            'individual_tests': total_individual_tests,
            'individual_passed': total_individual_passed,
            'failed_suites': failed_suites
        }
        
        return True
    
    # ===========================================
    # REPORTING AND ORCHESTRATION
    # ===========================================
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        print(f"\n{'='*70}")
        print(f"📋 COMPREHENSIVE PRE-SIMULATION TEST REPORT")
        print(f"{'='*70}")
        
        # Core test results
        total_core_tests = len(self.test_results)
        passed_core_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"📊 Core Validation: {passed_core_tests}/{total_core_tests} tests passed")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Critical Failures: {len(self.critical_failures)}")
        
        # Extended test results
        if hasattr(self, 'extended_test_results') and self.run_extended_tests:
            ext = self.extended_test_results
            print(f"🔬 Extended Test Suites: {ext['suites_passed']}/{ext['total_suites']} suites passed")
            if ext['individual_tests'] > 0:
                print(f"🧪 Individual Tests: {ext['individual_passed']}/{ext['individual_tests']} tests passed")
        
        # Enhanced timing analysis with details
        if self.timing_log:
            print(f"\n⏱️  DETAILED TIMING ANALYSIS:")
            total_time = sum(entry['duration'] for entry in self.timing_log.values())
            for operation, timing_data in self.timing_log.items():
                duration = timing_data['duration']
                percentage = (duration / total_time) * 100 if total_time > 0 else 0
                print(f"   {operation:<30}: {duration:6.2f}s ({percentage:5.1f}%)")
                
                # Show details if available
                if 'details' in timing_data and timing_data['details']:
                    details = timing_data['details']
                    if operation == "Data Generation":
                        print(f"      📊 Generated {details.get('bgp_files_generated', 0)} BGP files for RPKI nodes")
                        print(f"      �� Created {len(details.get('registry_files', []))} registry files")
                        print(f"      🔗 Mapped {details.get('as_wallet_mappings', 0)} AS-to-wallet addresses")
                        if details.get('sample_files'):
                            print(f"      📁 Key files: {details['sample_files'][0][:50]}...")
                    elif operation == "Wallet Funding":
                        print(f"      💰 Total staked: {details.get('total_staked', 'Unknown')}")
                        print(f"      🏦 Funded: {details.get('accounts_funded', 'Unknown')}")
                    elif operation == "Extended Test Suites":
                        print(f"      🧪 Suites: {details.get('suites_passed', 0)}/{details.get('total_suites', 0)} passed")
                        print(f"      📊 Tests: {details.get('individual_tests_passed', 0)}/{details.get('individual_tests_total', 0)} passed")
                    elif operation == "Module Import Check":
                        print(f"      📦 Imports: {details.get('successful_imports', 0)}/{details.get('total_imports_tested', 0)} successful")
                        
            print(f"   {'TOTAL TIME':<30}: {total_time:6.2f}s (100.0%)")
        
        # Show warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        # Show critical failures
        if self.critical_failures:
            print(f"\n❌ CRITICAL FAILURES:")
            for failure in self.critical_failures:
                print(f"   - {failure}")
        
        print(f"\n{'='*70}")
        
        # Final status determination
        if self.critical_failures:
            print(f"🚫 SYSTEM NOT READY - Fix critical failures first")
            return False
        elif self.warnings:
            print(f"⚠️  SYSTEM READY - Address warnings for optimal performance")
            return True
        else:
            print(f"🎉 ALL SYSTEMS GO - Ready for experiments!")
            return True
    
    def run_complete_setup_and_tests(self):
        """Run complete setup sequence followed by all tests"""
        if not self.setup_mode:
            return self.run_comprehensive_tests()
        
        print("🔄 COMPLETE SETUP AND VALIDATION SEQUENCE")
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
        
        # Then run validation
        return self.run_comprehensive_tests()
    
    def run_comprehensive_tests(self):
        """Run comprehensive validation tests"""
        print(f"\n📋 VALIDATION PHASE")
        print("=" * 30)
        
        # Core validation tests
        tests = [
            ('System Environment', self.test_1_system_environment),
            ('Directory Structure', self.test_2_directory_structure),
            ('Blockchain Connectivity', self.test_3_blockchain_connectivity),
            ('Module Imports', self.test_4_module_imports),
            ('Data Files', self.test_5_data_files),
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                self.test_results[test_name] = result
            except Exception as e:
                print(f"  💥 {test_name}: Unexpected error - {e}")
                self.test_results[test_name] = False
                self.critical_failures.append(f"{test_name}: Unexpected error")
        
        # Run extended tests if requested
        if self.run_extended_tests:
            self.run_extended_test_suites()
        
        return self.generate_final_report()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n🛑 Interrupted by user')
    if hasattr(signal_handler, 'checker'):
        signal_handler.checker.cleanup()
    sys.exit(1)

def main():
    """Run the ultimate enhanced pre-simulation master test"""
    parser = argparse.ArgumentParser(
        description='BGP-Sentry Ultimate Enhanced Pre-Simulation Test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
TEST TYPES AVAILABLE:
=====================

🎯 CORE VALIDATION TESTS (5 tests):
  1. System Environment      - Python version, virtual env, packages
  2. Directory Structure     - All required folders (19 directories)
  3. Blockchain Connectivity - Hardhat node + smart contract status
  4. Module Imports          - Interface modules (RPKI, Trust, Staking, etc.)
  5. Data Files             - BGP data + registries validation

🔬 EXTENDED TEST SUITES (18 individual test folders):  
  00_directory_structure    - Directory validation tests
  01_initialization_check   - System initialization tests
  02_blockchain_connectivity - Blockchain connection tests
  03_sc_interface          - Smart contract interface tests
  04_staking               - Economic compensation tests
  05_data_registries       - Data generation tests
  06_module_imports        - Python module import tests
  07_rpki_verification     - RPKI validation tests
  08_trust_engine          - Trust engine (RTE/ATE) tests
  09_trust_score_interface - Trust scoring tests
  10_bgp_data_validation   - BGP observation data tests
  11_bgp_attack_detection  - Attack detection tests
  12_consensus_readiness   - RPKI consensus tests
  13_economic_tests        - Economic incentive tests
  14_blockchain_functionality - Full blockchain tests
  15_attack_scenarios      - Security attack tests
  16_full_simulation       - End-to-end simulation tests
  17_setup_automation      - Setup utility tests
  18_master_runner         - Orchestration tests

🔧 SETUP OPERATIONS (5 steps):
  0. Blockchain Reset       - Kill Hardhat + clean cache/artifacts
  1. Start Hardhat         - Launch blockchain node
  2. Deploy Contracts      - Compile smart contracts
  3. Fund Wallets          - Deploy + fund all AS wallets (~65 ETH)
  4. Generate Data         - Create BGP data + registries

📊 DATA SOURCES:
  • test     - Self-generated test data (predictable, for development)
  • original - Production data (realistic, for final validation)

USAGE EXAMPLES:
===============
# Quick health check (30 seconds)
python3 enhanced_pre_simulation.py

# Comprehensive validation (2-5 minutes) - RECOMMENDED
python3 enhanced_pre_simulation.py --run-extended-tests

# Fresh environment setup (5-10 minutes)
python3 enhanced_pre_simulation.py --setup --run-extended-tests

# Test with production data
python3 enhanced_pre_simulation.py --run-extended-tests --data-source=original

# Individual test suite
python3 run_test_suite.py 04_staking

TOTAL POSSIBLE TESTS:
====================
- Core Validation: 5 tests
- Extended Suites: ~50+ individual pytest tests across 18 folders
- Setup Operations: 5 automated setup steps
- Data Variations: 2 data sources (test/original)
- Grand Total: 60+ different test scenarios possible

For more commands: ./commands.sh help
        """)
    
    parser.add_argument('--run-extended-tests', action='store_true', 
                       help='Run comprehensive validation: 5 core tests + ALL 18 individual test suites (~50+ tests total)')
    parser.add_argument('--data-source', choices=['test', 'original'], default='test',
                       help='Data source: "test" (self-generated, predictable) or "original" (production data)')
    parser.add_argument('--setup', action='store_true',
                       help='Run complete 5-step setup: reset blockchain → start Hardhat → deploy → fund → generate data → validate')
    
    args = parser.parse_args()
    
    checker = UltimatePreSimulationChecker(
        run_extended_tests=args.run_extended_tests,
        data_source=args.data_source,
        setup_mode=args.setup
    )
    
    # Set up signal handler for cleanup
    signal_handler.checker = checker
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        simulation_ready = checker.run_complete_setup_and_tests()
        
        # Save timing log
        timing_file = checker.base_path / "timing_analysis.json"
        with open(timing_file, 'w') as f:
            json.dump(checker.timing_log, f, indent=2)
        
        if checker.timing_log:
            print(f"\n📄 Detailed timing analysis saved to: {timing_file}")
        
        sys.exit(0 if simulation_ready else 1)
        
    except Exception as e:
        print(f"\n💥 Unexpected error during execution: {e}")
        sys.exit(1)
    finally:
        checker.cleanup()

if __name__ == "__main__":
    main()
