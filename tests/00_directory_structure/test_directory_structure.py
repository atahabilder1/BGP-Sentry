#!/usr/bin/env python3
"""
Directory Structure Validation Tests
Split from enhanced_pre_simulation.py test_1_directory_structure()
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

class TestDirectoryStructure:
    """Test suite for directory structure validation"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.base_path = Path(__file__).parent.parent.parent
        
    def test_main_directories_exist(self):
        """Test that main directories exist"""
        required_dirs = [
            "nodes/rpki_nodes",
            "nodes/non_rpki_nodes", 
            "trust_engine",
            "smart_contract",
            "tests"
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
        
        assert len(missing_dirs) == 0, f"Missing directories: {missing_dirs}"
    
    def test_rpki_nodes_exist(self):
        """Test that all RPKI nodes exist"""
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
        
        missing_dirs = []
        for dir_path in required_rpki_nodes:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
        
        assert len(missing_dirs) == 0, f"Missing RPKI nodes: {missing_dirs}"
    
    def test_interface_directories_exist(self):
        """Test that interface directories exist"""
        required_interfaces = [
            "nodes/rpki_nodes/bgp_attack_detection",
            "nodes/rpki_nodes/rpki_verification_interface",
            "nodes/rpki_nodes/trust_score_interface", 
            "nodes/rpki_nodes/staking_amount_interface",
            "nodes/rpki_nodes/shared_blockchain_stack"
        ]
        
        missing_dirs = []
        for dir_path in required_interfaces:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
        
        assert len(missing_dirs) == 0, f"Missing interfaces: {missing_dirs}"

if __name__ == "__main__":
    pytest.main([__file__])
