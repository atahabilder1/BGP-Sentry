#!/usr/bin/env python3
"""
========================================================
BGP-Sentry Enhanced Pre-Simulation Master Test
File Location: tests/enhanced_pre_simulation.py
========================================================

Complete system setup, validation, and timing analysis before running experiments
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

class EnhancedPreSimulationChecker:
    """Enhanced pre-simulation validation system with complete setup"""
    
    def __init__(self, run_extended_tests=False, data_source='test'):
        self.base_path = Path(__file__).parent.parent
        self.test_results = {}
        self.critical_failures = []
        self.warnings = []
        self.timing_log = {}
        self.hardhat_process = None
        self.run_extended_tests = run_extended_tests
        self.data_source = data_source
        
        print("🚀 BGP-Sentry Enhanced Pre-Simulation Master Test")
        print("=" * 70)
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Data Source: {data_source}")
        if self.run_extended_tests:
            print(f"🔬 Extended Test Mode: Will run specialized test suites")
        print("=" * 70)
    
    def log_timing(self, operation, duration):
        """Log timing information for operations"""
        self.timing_log[operation] = {
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        print(f"⏱️  {operation}: {duration:.2f} seconds")
    
    def test_1_system_environment(self):
        """Test 1: System environment and dependencies"""
        print(f"\n🔍 TEST 1: System Environment")
        print("-" * 50)
        
        start_time = time.time()
        
        # Check Python version
        python_version = sys.version_info
        print(f"  ✅ Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version < (3, 8):
            self.critical_failures.append("Python 3.8+ required")
            print(f"  ❌ Python version too old (need 3.8+)")
        
        # Check virtual environment
        venv_active = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        if venv_active:
            print(f"  ✅ Virtual Environment: Active")
        else:
            print(f"  ⚠️  Virtual Environment: Not active (recommended)")
            self.warnings.append("Virtual environment not active")
        
        # Check key packages
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
        
        return len(self.critical_failures) == 0
    
    def test_2_directory_structure(self):
        """Test 2: Complete directory structure validation"""
        print(f"\n🔍 TEST 2: Directory Structure")
        print("-" * 50)
        
        start_time = time.time()
        
        # Essential directories
        essential_dirs = [
            "nodes/rpki_nodes",
            "nodes/non_rpki_nodes", 
            "trust_engine",
            "smart_contract",
            "tests"
        ]
        
        # RPKI nodes
        rpki_nodes = [
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
        
        # Interface directories
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
        
        # Check smart contract deployment
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
        
        # Add interface paths
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
        
        # Test imports
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
        self.log_timing("Module Import Check", duration)
        
        if failed_imports:
            self.warnings.append(f"Failed imports: {failed_imports}")
        
        print(f"  📊 Result: {len(import_tests) - len(failed_imports)}/{len(import_tests)} imports successful")
        return True  # Don't fail on import issues, just warn
    
    def test_5_data_files(self):
        """Test 5: Essential data files validation"""
        print(f"\n🔍 TEST 5: Data Files")
        print("-" * 50)
        
        start_time = time.time()
        
        # Check BGP data files for a few nodes
        test_nodes = ['as01', 'as03', 'as05']
        missing_files = []
        invalid_files = []
        
        for node in test_nodes:
            suffix = f"_{self.data_source}" if self.data_source == 'test' else ""
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
        ]
        
        for name, path in registry_files:
            file_path = self.base_path / path
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    print(f"  ✅ {name}: Valid ({len(data)} entries)")
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
    
    def run_extended_test_suites(self):
        """Run extended test suites from individual folders"""
        if not self.run_extended_tests:
            return True
        
        print(f"\n🔬 EXTENDED TEST SUITES")
        print("=" * 50)
        
        # Get available test folders
        test_folders = [d.name for d in Path(__file__).parent.iterdir() 
                       if d.is_dir() and d.name.startswith(('0', '1')) and d.name != 'data_generator']
        test_folders.sort()
        
        if not test_folders:
            print("  ⚠️  No extended test suites found")
            return True
        
        success_count = 0
        for folder in test_folders[:3]:  # Run first 3 for now
            print(f"  🧪 Running {folder}...")
            try:
                result = subprocess.run([
                    sys.executable, '-m', 'pytest', str(Path(__file__).parent / folder), '-v', '--tb=short'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"    ✅ {folder}: Passed")
                    success_count += 1
                else:
                    print(f"    ❌ {folder}: Failed")
                    if result.stdout:
                        print(f"       {result.stdout.split()[-1] if result.stdout.split() else 'No output'}")
                    
            except subprocess.TimeoutExpired:
                print(f"    ⏰ {folder}: Timeout")
            except Exception as e:
                print(f"    💥 {folder}: Error - {e}")
        
        print(f"  📊 Extended Tests: {success_count}/{len(test_folders[:3])} suites passed")
        return True
    
    def generate_final_report(self):
        """Generate final pre-simulation report"""
        print(f"\n{'='*70}")
        print(f"📋 ENHANCED PRE-SIMULATION TEST REPORT")
        print(f"{'='*70}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Critical Failures: {len(self.critical_failures)}")
        
        # Generate timing report
        if self.timing_log:
            print(f"\n⏱️  TIMING ANALYSIS:")
            total_time = sum(entry['duration'] for entry in self.timing_log.values())
            for operation, timing_data in self.timing_log.items():
                duration = timing_data['duration']
                percentage = (duration / total_time) * 100 if total_time > 0 else 0
                print(f"   {operation:<25}: {duration:5.2f}s ({percentage:4.1f}%)")
            print(f"   {'TOTAL TIME':<25}: {total_time:5.2f}s (100.0%)")
        
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
            print(f"🚫 SYSTEM NOT READY - Fix critical failures first")
            return False
        elif self.warnings:
            print(f"⚠️  SYSTEM READY - Address warnings for optimal performance")
            return True
        else:
            print(f"🎉 ALL SYSTEMS GO - Ready for experiments!")
            return True
    
    def run_comprehensive_tests(self):
        """Run comprehensive validation tests"""
        print("🔄 RUNNING COMPREHENSIVE VALIDATION")
        print("=" * 70)
        
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

def main():
    """Run the enhanced pre-simulation master test"""
    parser = argparse.ArgumentParser(description='BGP-Sentry Enhanced Pre-Simulation Test')
    parser.add_argument('--run-extended-tests', action='store_true', 
                       help='Run extended test suites from specialized folders')
    parser.add_argument('--data-source', choices=['test', 'original'], default='test',
                       help='Data source: test (self-generated) or original (production data)')
    
    args = parser.parse_args()
    
    checker = EnhancedPreSimulationChecker(
        run_extended_tests=args.run_extended_tests,
        data_source=args.data_source
    )
    
    try:
        simulation_ready = checker.run_comprehensive_tests()
        
        # Save timing log
        timing_file = checker.base_path / "timing_analysis.json"
        with open(timing_file, 'w') as f:
            json.dump(checker.timing_log, f, indent=2)
        
        if checker.timing_log:
            print(f"\n📄 Timing analysis saved to: {timing_file}")
        
        sys.exit(0 if simulation_ready else 1)
        
    except Exception as e:
        print(f"\n💥 Unexpected error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
