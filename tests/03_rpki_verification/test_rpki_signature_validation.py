#!/usr/bin/env python3
"""
Unit Tests: RPKI Verification
Tests RPKI validation logic
"""

import unittest
import sys
from pathlib import Path

# Add module paths
base_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_path / "nodes/rpki_nodes/rpki_verification_interface"))

class TestRPKIVerification(unittest.TestCase):
    """Test RPKI verification functionality"""
    
    def setUp(self):
        """Set up test environment"""
        from verifier import is_as_verified, get_all_verified_ases, get_all_unverified_ases
        self.is_as_verified = is_as_verified
        self.get_all_verified_ases = get_all_verified_ases
        self.get_all_unverified_ases = get_all_unverified_ases
    
    def test_rpki_valid_as(self):
        """Test RPKI valid AS numbers"""
        # Test known valid ASes (odd numbers: 1, 3, 5, etc.)
        valid_ases = [1, 3, 5, 7, 9]
        
        for as_number in valid_ases:
            with self.subTest(as_number=as_number):
                result = self.is_as_verified(as_number)
                self.assertTrue(result, f"AS{as_number} should be RPKI valid")
    
    def test_rpki_invalid_as(self):
        """Test RPKI invalid AS numbers"""
        # Test known invalid ASes (even numbers: 2, 4, 6, etc.)
        invalid_ases = [2, 4, 6, 8, 10]
        
        for as_number in invalid_ases:
            with self.subTest(as_number=as_number):
                result = self.is_as_verified(as_number)
                self.assertFalse(result, f"AS{as_number} should be RPKI invalid")
    
    def test_string_as_format(self):
        """Test string AS number format"""
        result = self.is_as_verified("as01")
        self.assertTrue(result, "AS01 string format should work")
        
        result = self.is_as_verified("as02")
        self.assertFalse(result, "AS02 string format should work")
    
    def test_numeric_as_format(self):
        """Test numeric AS number format"""
        result = self.is_as_verified(1)
        self.assertTrue(result, "AS1 numeric format should work")
        
        result = self.is_as_verified(2)
        self.assertFalse(result, "AS2 numeric format should work")
    
    def test_get_verified_ases(self):
        """Test getting all verified ASes"""
        verified = self.get_all_verified_ases()
        self.assertIsInstance(verified, list)
        self.assertGreater(len(verified), 0, "Should have some verified ASes")
        
        # Should contain odd numbered ASes
        self.assertIn('as01', verified)
        self.assertIn('as03', verified)
    
    def test_get_unverified_ases(self):
        """Test getting all unverified ASes"""
        unverified = self.get_all_unverified_ases()
        self.assertIsInstance(unverified, list)
        self.assertGreater(len(unverified), 0, "Should have some unverified ASes")
        
        # Should contain even numbered ASes  
        self.assertIn('as02', unverified)
        self.assertIn('as04', unverified)
    
    def test_invalid_as_number(self):
        """Test invalid AS number handling"""
        result = self.is_as_verified(999)
        self.assertFalse(result, "Unknown AS should return False")
        
        result = self.is_as_verified("invalid")
        self.assertFalse(result, "Invalid AS format should return False")

if __name__ == '__main__':
    print("🧪 Running RPKI Verification Tests...")
    unittest.main(verbosity=2)
