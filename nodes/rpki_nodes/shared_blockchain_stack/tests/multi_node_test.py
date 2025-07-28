#!/usr/bin/env python3
"""
Multi-Node RPKI Test
"""

import sys
import time
import threading
sys.path.append('../services/rpki_observer_service')
sys.path.append('../utils_common')

from observer_main import RPKIObserverService

def run_node(as_number, duration=10):
    """Run a single RPKI node"""
    try:
        print(f'🟢 Starting AS{as_number:02d}...')
        observer = RPKIObserverService(as_number)
        observer.start()
        time.sleep(duration)
        observer.stop()
        print(f'🔴 AS{as_number:02d} stopped')
    except Exception as e:
        print(f'❌ AS{as_number:02d} error: {e}')

def multi_node_test():
    """Test multiple RPKI nodes simultaneously"""
    
    print("🔄 Starting Multi-Node Test...")
    
    # Test nodes AS01, AS03, AS05
    nodes = [1, 3, 5]
    threads = []
    
    # Start each node in a separate thread
    for as_num in nodes:
        thread = threading.Thread(target=run_node, args=(as_num, 8))
        thread.start()
        threads.append(thread)
        time.sleep(2)  # Stagger startup
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("✅ Multi-node test completed!")
    
    # Check generated data
    try:
        import json
        with open('../shared_data/chain/transaction_pool.json', 'r') as f:
            data = json.load(f)
        
        print(f"\n📊 Results:")
        print(f"Total transactions: {len(data['transactions'])}")
        
        # Group by observer
        observers = {}
        for tx in data['transactions']:
            obs = tx.get('observer_as', 'unknown')
            observers[obs] = observers.get(obs, 0) + 1
        
        for obs, count in observers.items():
            print(f"  AS{obs}: {count} transactions")
            
    except Exception as e:
        print(f"Error reading results: {e}")

if __name__ == "__main__":
    multi_node_test()
