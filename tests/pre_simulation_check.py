#!/usr/bin/env python3
"""
BGP-Sentry Pre-Simulation Master Test
Comprehensive system validation before running experiments
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

class PreSimulationChecker:
    """Master pre-simulation validation system"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.test_results = {}
        self.critical_failures = []
        self.warnings = []
        
        print("🚀 BGP-Sentry Pre-Simulation Master Test")
        print("=" * 70)
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
    
    def test_1_directory_structure(self):
        """Test 1: Verify complete directory structure"""
        print(f"\n🔍 TEST 1: Directory Structure Validation")
        print("-" * 50)
        
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
        
        if missing_dirs:
            self.critical_failures.append(f"Missing directories: {missing_dirs}")
            return False
        
        print(f"  📊 Result: All {len(all_dirs)} directories found")
        return True
    
    def test_2_bgp_data_files(self):
        """Test 2: Verify BGP observation data files"""
        print(f"\n🔍 TEST 2: BGP Data Files Validation")
        print("-" * 50)
        
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
        
        print(f"  📊 Result: Blockchain fully operational")
        return True
    
    def test_4_interface_modules(self):
        """Test 4: Verify all interface modules can be imported"""
        print(f"\n🔍 TEST 4: Interface Module Imports")
        print("-" * 50)
        
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
            ('BGP Attack Detection', 'from attack_detector_fixed import BGPSecurityAnalyzer'),
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
        
        if failed_imports:
            self.critical_failures.append(f"Failed imports: {failed_imports}")
            return False
        
        print(f"  📊 Result: All {len(import_tests)} interfaces importable")
        return True
    
    def test_5_trust_engine_integration(self):
        """Test 5: Test trust engine integration"""
        print(f"\n🔍 TEST 5: Trust Engine Integration")
        print("-" * 50)
        
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
        
        if missing_registries:
            self.critical_failures.append(f"Missing registries: {missing_registries}")
            return False
        
        print(f"  📊 Result: All {len(registry_files)} registries valid")
        return True
    
    def generate_final_report(self):
        """Generate final pre-simulation report"""
        print(f"\n{'='*70}")
        print(f"📋 PRE-SIMULATION TEST REPORT")
        print(f"{'='*70}")
        
        total_tests = 8
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Critical Failures: {len(self.critical_failures)}")
        
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
    
    def run_all_tests(self):
        """Run all pre-simulation tests"""
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

def main():
    """Run the pre-simulation master test"""
    checker = PreSimulationChecker()
    simulation_ready = checker.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if simulation_ready else 1)

if __name__ == "__main__":
    main()
