#!/usr/bin/env python3
"""
Test Suite Runner
Run individual test suites or all tests
"""

import sys
import subprocess
from pathlib import Path
import argparse

def run_test_folder(folder_name):
    """Run tests in a specific folder"""
    test_path = Path(__file__).parent / folder_name
    
    if not test_path.exists():
        print(f"❌ Test folder {folder_name} not found")
        return False
    
    print(f"🔍 Running tests in {folder_name}...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', str(test_path), '-v'
        ], cwd=Path(__file__).parent)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests in {folder_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run BGP-Sentry test suites')
    parser.add_argument('folder', nargs='?', help='Test folder to run (e.g., 00_directory_structure)')
    parser.add_argument('--list', action='store_true', help='List available test folders')
    
    args = parser.parse_args()
    
    # Get available test folders
    test_folders = [d.name for d in Path(__file__).parent.iterdir() 
                   if d.is_dir() and d.name.startswith(('0', '1')) and d.name != 'data_generator']
    test_folders.sort()
    
    if args.list:
        print("📋 Available test suites:")
        for folder in test_folders:
            print(f"  {folder}")
        return
    
    if not args.folder:
        print("🔬 Running all test suites...")
        success_count = 0
        for folder in test_folders:
            if run_test_folder(folder):
                success_count += 1
        
        print(f"\n📊 Results: {success_count}/{len(test_folders)} test suites passed")
        return success_count == len(test_folders)
    
    else:
        return run_test_folder(args.folder)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
