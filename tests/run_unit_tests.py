#!/usr/bin/env python3
"""
Unit Test Runner
Runs all unit tests with proper reporting
"""

import unittest
import sys
from pathlib import Path

def discover_and_run_tests():
    """Discover and run all unit tests"""
    
    print("🧪 BGP-Sentry Unit Test Runner")
    print("=" * 50)
    
    # Test directories with unit tests
    test_dirs = [
        '00_initialization_check',
        '01_staking', 
        '02_trust_engine',
        '03_rpki_verification',
        '06_bgp_attack_detection'
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for test_dir in test_dirs:
        print(f"\n🔍 Running tests in {test_dir}...")
        print("-" * 40)
        
        # Create test loader
        loader = unittest.TestLoader()
        
        # Discover tests in directory
        test_path = Path(__file__).parent / test_dir
        if test_path.exists():
            suite = loader.discover(str(test_path), pattern='test_*.py')
            
            # Run tests
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            # Track results
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
        else:
            print(f"⚠️  Directory {test_dir} not found")
    
    # Final report
    print(f"\n{'='*50}")
    print(f"📊 UNIT TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests Run: {total_tests}")
    print(f"Failures: {total_failures}")
    print(f"Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print(f"🎉 ALL UNIT TESTS PASSED!")
        return True
    else:
        print(f"❌ Some unit tests failed")
        return False

if __name__ == '__main__':
    success = discover_and_run_tests()
    sys.exit(0 if success else 1)
