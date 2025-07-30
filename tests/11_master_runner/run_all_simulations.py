#!/usr/bin/env python3
"""
BGP-Sentry Master Test & Simulation Runner
"""

import subprocess
import sys
from pathlib import Path

def run_test(test_name, test_path):
    """Run a test file"""
    print(f"\n{'='*50}")
    print(f"🧪 {test_name}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run([sys.executable, str(test_path)], 
                              capture_output=True, text=True, 
                              cwd=test_path.parent)
        
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"❌ Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all BGP-Sentry tests and simulations"""
    print("🚀 BGP-Sentry Complete Test & Simulation Suite")
    print("=" * 60)
    
    # Get the tests directory (parent of this script's directory)
    tests_dir = Path(__file__).parent.parent
    
    # Test sequence with folder structure
    tests = [
        ("00 - Pre-Simulation Check", tests_dir / "pre_simulation_check.py"),
        ("01 - Unit Tests", tests_dir / "run_unit_tests.py"),
        ("08 - Full Simulation", tests_dir / "08_full_simulation" / "run_full_simulation.py"),
        ("09 - Attack Scenarios", tests_dir / "09_attack_scenarios" / "test_attack_scenarios.py"),
        ("10 - Economic System", tests_dir / "10_economic_tests" / "test_economic_system.py")
    ]
    
    results = []
    
    for test_name, test_path in tests:
        if test_path.exists():
            success = run_test(test_name, test_path)
            results.append((test_name, success))
        else:
            print(f"⚠️  {test_name}: File not found - {test_path}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📋 FINAL SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"📊 Overall Results: {passed}/{total} test categories passed")
    print()
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {test_name}")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED - BGP-Sentry fully operational!")
    else:
        print(f"\n⚠️  Some tests need attention - Check results above")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
