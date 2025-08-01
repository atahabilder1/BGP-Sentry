#!/usr/bin/env python3
"""
System Initialization Tests
Basic system connectivity and environment checks
"""

import pytest
import sys
import os
from pathlib import Path

class TestInitialization:
    """Test suite for system initialization"""
    
    def test_python_environment(self):
        """Test Python environment is properly set up"""
        assert sys.version_info >= (3, 8), "Python 3.8+ required"
    
    def test_virtual_environment(self):
        """Test virtual environment is active"""
        # This is optional but recommended
        venv_active = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        if not venv_active:
            pytest.skip("Virtual environment not active (recommended but not required)")
    
    def test_project_structure_basic(self):
        """Test basic project structure exists"""
        base_path = Path(__file__).parent.parent.parent
        essential_paths = [
            "nodes",
            "trust_engine", 
            "smart_contract",
            "tests"
        ]
        
        for path in essential_paths:
            assert (base_path / path).exists(), f"Missing essential directory: {path}"

if __name__ == "__main__":
    pytest.main([__file__])
