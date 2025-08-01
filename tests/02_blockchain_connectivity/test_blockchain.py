#!/usr/bin/env python3
"""
Blockchain Connectivity Tests
Split from enhanced_pre_simulation.py test_3_blockchain_connectivity()
"""

import pytest
import requests
import json
from pathlib import Path

class TestBlockchainConnectivity:
    """Test suite for blockchain connectivity"""
    
    def test_hardhat_node_running(self):
        """Test that Hardhat node is running and responsive"""
        try:
            response = requests.post('http://localhost:8545', 
                                   json={'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1},
                                   timeout=3)
            assert response.status_code == 200, "Hardhat node not responding"
            
            result = response.json()
            assert 'result' in result, "Invalid response from Hardhat node"
            
            block_number = int(result.get('result', '0x0'), 16)
            assert block_number >= 0, "Invalid block number"
            
        except requests.exceptions.ConnectionError:
            pytest.fail("Cannot connect to Hardhat node at localhost:8545")
        except requests.exceptions.Timeout:
            pytest.fail("Hardhat node connection timeout")
    
    def test_smart_contract_deployed(self):
        """Test that smart contract is deployed"""
        base_path = Path(__file__).parent.parent.parent
        contract_file = base_path / "smart_contract/deployments/localhost/StakingContract.json"
        
        assert contract_file.exists(), "Smart contract deployment file not found"
        
        with open(contract_file, 'r') as f:
            deployment = json.load(f)
        
        assert 'address' in deployment, "Contract address not found in deployment file"
        assert deployment['address'].startswith('0x'), "Invalid contract address format"

if __name__ == "__main__":
    pytest.main([__file__])
