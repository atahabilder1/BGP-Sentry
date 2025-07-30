#!/usr/bin/env python3
"""
Blockchain Status Checker
Verifies if the blockchain/hardhat node is actually running
"""

import subprocess
import json
import os
from pathlib import Path

def check_hardhat_node_status():
    """Check if hardhat node is running"""
    print("🔍 Checking Hardhat Node Status...")
    
    try:
        # Try to connect to localhost:8545 (default hardhat port)
        import requests
        response = requests.post('http://localhost:8545', 
                               json={'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1},
                               timeout=2)
        
        if response.status_code == 200:
            result = response.json()
            block_number = int(result.get('result', '0x0'), 16)
            print(f"✅ Hardhat node is running (Block: {block_number})")
            return True
        else:
            print(f"❌ Hardhat node not responding (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Hardhat node not accessible: {e}")
        return False

def check_smart_contract_deployment():
    """Check if StakingContract is deployed"""
    print("\n�� Checking Smart Contract Deployment...")
    
    contract_path = Path(__file__).parent.parent.parent.parent / "smart_contract/deployments/localhost/StakingContract.json"
    
    if not contract_path.exists():
        print(f"❌ Contract deployment file not found: {contract_path}")
        return False
    
    try:
        with open(contract_path, 'r') as f:
            deployment = json.load(f)
        
        contract_address = deployment.get('address')
        print(f"✅ StakingContract deployed at: {contract_address}")
        return True
        
    except Exception as e:
        print(f"❌ Error reading deployment file: {e}")
        return False

def test_real_stake_query():
    """Test querying real stake amount"""
    print("\n🔍 Testing Real Stake Query...")
    
    smart_contract_path = Path(__file__).parent.parent.parent.parent / "smart_contract"
    
    # Test with AS02 wallet address
    test_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    
    try:
        env = os.environ.copy()
        env['ADDRESS'] = test_address
        
        result = subprocess.run(
            ['npx', 'hardhat', 'run', 'scripts/check_single_stake.js', '--network', 'localhost'],
            cwd=str(smart_contract_path),
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ Real blockchain query successful:")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Blockchain query failed:")
            print(f"   Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Error running blockchain query: {e}")
        return False

def main():
    """Run comprehensive blockchain status check"""
    print("🚀 BGP-Sentry Blockchain Status Check")
    print("=" * 50)
    
    # Check all components
    node_running = check_hardhat_node_status()
    contract_deployed = check_smart_contract_deployment()
    
    if node_running and contract_deployed:
        stake_query_works = test_real_stake_query()
    else:
        stake_query_works = False
    
    print(f"\n📊 Status Summary:")
    print(f"   Hardhat Node: {'✅ Running' if node_running else '❌ Not Running'}")
    print(f"   Smart Contract: {'✅ Deployed' if contract_deployed else '❌ Not Deployed'}")
    print(f"   Stake Queries: {'✅ Working' if stake_query_works else '❌ Using Mock Data'}")
    
    if not (node_running and contract_deployed and stake_query_works):
        print(f"\n⚠️  IMPORTANT: Staking interface is using MOCK DATA")
        print(f"   To use real blockchain data:")
        print(f"   1. Start hardhat node: cd smart_contract && npx hardhat node")
        print(f"   2. Deploy contract: npx hardhat run scripts/deploy.js --network localhost")
        print(f"   3. Verify deployment: npx hardhat run scripts/check_single_stake.js --network localhost")
    else:
        print(f"\n🎉 Blockchain is fully operational!")

if __name__ == "__main__":
    main()
