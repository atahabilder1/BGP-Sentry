#!/usr/bin/env python3
"""
BGP-Sentry Full Simulation - Fully Automated
Automatically starts Hardhat, deploys contracts, funds wallets, and runs simulation
"""

import sys
import subprocess
import time
import signal
import os
from pathlib import Path

# Add interface paths
base_path = Path(__file__).parent.parent.parent
interfaces = [
    'nodes/rpki_nodes/bgp_attack_detection',
    'nodes/rpki_nodes/rpki_verification_interface', 
    'nodes/rpki_nodes/trust_score_interface',
    'nodes/rpki_nodes/staking_amount_interface',
    'nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils'
]

for interface in interfaces:
    sys.path.insert(0, str(base_path / interface))

class HardhatManager:
    """Manages Hardhat node lifecycle"""
    
    def __init__(self):
        self.hardhat_process = None
        self.smart_contract_path = base_path / "smart_contract"
    
    def start_hardhat(self):
        """Start Hardhat node in background"""
        print("🔧 Starting Hardhat node...")
        
        try:
            self.hardhat_process = subprocess.Popen(
                ['npx', 'hardhat', 'node'],
                cwd=str(self.smart_contract_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Wait for node to start
            print("⏳ Waiting for Hardhat to initialize...")
            
            for attempt in range(30):
                time.sleep(1)
                if self._test_connection():
                    print(f"✅ Hardhat node ready after {attempt + 1} seconds")
                    return True
                
                # Check if process died
                if self.hardhat_process.poll() is not None:
                    stdout, stderr = self.hardhat_process.communicate()
                    print(f"❌ Hardhat process failed: {stderr.decode()}")
                    return False
                
                if attempt % 5 == 0 and attempt > 0:
                    print(f"⏳ Still starting... ({attempt}/30 seconds)")
            
            print("❌ Hardhat failed to start within 30 seconds")
            self.stop_hardhat()
            return False
            
        except Exception as e:
            print(f"❌ Error starting Hardhat: {e}")
            return False
    
    def _test_connection(self):
        """Test if Hardhat is responding"""
        try:
            import requests
            response = requests.post('http://localhost:8545', 
                                   json={'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1},
                                   timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def fund_wallets(self):
        """Fund all wallets with ETH"""
        print("💰 Funding wallets...")
        
        try:
            result = subprocess.run(
                ['npx', 'hardhat', 'run', 'scripts/deposit_from_all.js', '--network', 'localhost'],
                cwd=str(self.smart_contract_path),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✅ All wallets funded successfully!")
                
                # Show funding summary
                lines = result.stdout.strip().split('\n')
                funded_count = sum(1 for line in lines if 'staked' in line and 'ETH' in line)
                
                # Extract total from last line
                for line in reversed(lines):
                    if 'Final Contract Balance:' in line:
                        total_eth = line.split(':')[1].strip()
                        print(f"   📊 {funded_count} accounts funded - Total: {total_eth}")
                        break
                
                return True
            else:
                print(f"❌ Wallet funding failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error funding wallets: {e}")
            return False
    
    def stop_hardhat(self):
        """Stop Hardhat node"""
        if self.hardhat_process:
            try:
                os.killpg(os.getpgid(self.hardhat_process.pid), signal.SIGTERM)
                self.hardhat_process = None
                print("🔧 Hardhat node stopped")
            except Exception as e:
                print(f"⚠️  Could not stop Hardhat: {e}")
    
    def __del__(self):
        """Cleanup on exit"""
        self.stop_hardhat()

def run_full_simulation():
    """Run complete BGP-Sentry simulation"""
    
    print("\n🚀 BGP-Sentry Full Simulation Starting...")
    print("=" * 60)
    
    # Import all modules
    from verifier import is_as_verified
    from attack_detector_fixed import BGPSecurityAnalyzer
    from trust_engine_interface import TrustEngineInterface
    from staking_amountchecker import StakingAmountChecker
    
    # Initialize systems
    print("\n🔧 Initializing Systems...")
    analyzer = BGPSecurityAnalyzer()
    trust_engine = TrustEngineInterface()
    staking_checker = StakingAmountChecker()
    
    print("✅ All systems initialized")
    
    # Check current system status
    print("\n💰 Economic Participation Status:")
    print("-" * 40)
    
    eligibility_summary = staking_checker.get_participation_summary()
    
    can_participate = sum(1 for r in eligibility_summary if r['can_participate'])
    total = len(eligibility_summary)
    
    print(f"Eligible ASes: {can_participate}/{total}")
    
    for result in eligibility_summary:
        status_icon = "✅" if result['can_participate'] else "❌"
        trust = result['trust_score']
        stake = result['current_stake']
        required = result['required_stake']
        
        print(f"{status_icon} AS{result['as_number']:02d}: Trust={trust:2.0f}, Stake={stake:.3f}/{required:.3f} ETH")
    
    # Simulate BGP announcements
    print(f"\n📡 Simulating BGP Announcements:")
    print("-" * 40)
    
    # Test announcements from different AS types
    test_announcements = [
        {'as_number': 1, 'prefix': '192.0.2.0/24', 'description': 'RPKI-valid AS (should pass)'},
        {'as_number': 2, 'prefix': '203.0.113.0/24', 'description': 'Non-RPKI AS (good behavior)'},
        {'as_number': 4, 'prefix': '192.0.2.0/24', 'description': 'Non-RPKI AS (prefix hijack attempt)'},
        {'as_number': 6, 'prefix': '203.0.113.128/25', 'description': 'Non-RPKI AS (subprefix hijack)'},
        {'as_number': 8, 'prefix': '10.0.0.0/8', 'description': 'Non-RPKI AS (route leak)'}
    ]
    
    results = []
    
    for announcement in test_announcements:
        print(f"\n🔍 Testing: AS{announcement['as_number']:02d} announces {announcement['prefix']}")
        print(f"   Scenario: {announcement['description']}")
        
        # Check RPKI status
        if is_as_verified(announcement['as_number']):
            print(f"   ✅ RPKI-valid AS → Automatically approved")
            results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'RPKI valid'})
            continue
        
        # Check economic eligibility
        eligibility = staking_checker.check_participation_eligibility(announcement['as_number'])
        
        if not eligibility['can_participate']:
            print(f"   ❌ Economic eligibility failed: {eligibility['reason']}")
            print(f"   �� Needs {eligibility['stake_deficit']:.3f} more ETH")
            results.append({'as': announcement['as_number'], 'result': 'rejected', 'reason': 'insufficient stake'})
            continue
        
        print(f"   ✅ Economic eligibility passed: {eligibility['current_stake']:.3f} ETH staked")
        
        # Attack detection
        detection_result = analyzer.analyze_announcement(announcement)
        
        if detection_result['legitimate']:
            print(f"   ✅ Attack detection: Clean announcement")
            results.append({'as': announcement['as_number'], 'result': 'approved', 'reason': 'clean'})
        else:
            attacks = detection_result['attacks_detected']
            print(f"   🚨 Attack detection: {len(attacks)} attack(s) detected")
            for attack in attacks:
                print(f"      - {attack.get('type', 'unknown')} attack")
            results.append({'as': announcement['as_number'], 'result': 'rejected', 'reason': 'attack detected'})
    
    # Simulation summary
    print(f"\n" + "=" * 60)
    print(f"📋 SIMULATION SUMMARY")
    print(f"=" * 60)
    
    approved = sum(1 for r in results if r['result'] == 'approved')
    rejected = sum(1 for r in results if r['result'] == 'rejected')
    
    print(f"📊 Results: {approved} approved, {rejected} rejected out of {len(results)} announcements")
    
    print(f"\n📈 Detailed Results:")
    for result in results:
        status_icon = "✅" if result['result'] == 'approved' else "❌"
        print(f"   {status_icon} AS{result['as']:02d}: {result['result'].upper()} ({result['reason']})")
    
    print(f"\n🎯 Key Insights:")
    print(f"   • RPKI-valid ASes: Automatically trusted")
    print(f"   • Non-RPKI ASes: Subject to economic + behavioral validation")
    print(f"   • Attack detection: {len([r for r in results if r['reason'] == 'attack detected'])} attacks prevented")
    print(f"   • Economic security: {len([r for r in results if r['reason'] == 'insufficient stake'])} ASes blocked for insufficient stakes")
    
    print(f"\n🎉 Simulation Complete!")
    print(f"=" * 60)

def main():
    """Fully automated simulation"""
    
    print("🚀 BGP-Sentry Fully Automated Simulation")
    print("=" * 60)
    
    hardhat = HardhatManager()
    
    try:
        # Step 1: Start Hardhat
        if not hardhat.start_hardhat():
            print("🚫 Failed to start Hardhat node")
            return
        
        # Step 2: Fund wallets
        if not hardhat.fund_wallets():
            print("🚫 Failed to fund wallets")
            return
        
        # Step 3: Wait for transactions to settle
        print("\n⏳ Waiting for blockchain to settle...")
        time.sleep(3)
        
        # Step 4: Run simulation
        run_full_simulation()
        
        # Step 5: Ask user about cleanup
        print(f"\n🔧 Hardhat is still running (PID: {hardhat.hardhat_process.pid})")
        response = input("Stop Hardhat node? (y/N): ").lower().strip()
        
        if response == 'y':
            hardhat.stop_hardhat()
        else:
            print("Hardhat node left running for additional testing")
            hardhat.hardhat_process = None  # Don't auto-cleanup
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Simulation interrupted")
        hardhat.stop_hardhat()
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        hardhat.stop_hardhat()

if __name__ == "__main__":
    main()
