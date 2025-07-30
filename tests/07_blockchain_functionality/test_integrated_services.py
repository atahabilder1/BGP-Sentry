#!/usr/bin/env python3
"""
Integration tests for BGP-Sentry RPKI Observer and Consensus Services
"""

import sys
import time
import unittest
from pathlib import Path

# Add project paths for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "nodes" / "rpki_nodes"))

from shared_blockchain_stack.services.rpki_observer_service.observer_main import RPKIObserverService
from shared_blockchain_stack.services.consensus_service.consensus_main import ConsensusService

class TestIntegratedServices(unittest.TestCase):
    """Integration tests for Observer and Consensus services working together"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.as_number = 5
        self.observer = RPKIObserverService(as_number=self.as_number)
        self.consensus = ConsensusService(as_number=self.as_number)
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'observer'):
            self.observer.stop_service()
        if hasattr(self, 'consensus'):
            self.consensus.stop_service()
    
    def test_service_initialization(self):
        """Test that both services initialize correctly"""
        self.assertEqual(self.observer.as_number, 5)
        self.assertEqual(self.consensus.as_number, 5)
        self.assertFalse(self.observer.running)
        self.assertFalse(self.consensus.running)
    
    def test_service_startup_shutdown(self):
        """Test service startup and shutdown process"""
        # Start services
        self.observer.start_service()
        self.consensus.start_service()
        
        # Verify running state
        self.assertTrue(self.observer.running)
        self.assertTrue(self.consensus.running)
        
        # Stop services
        self.observer.stop_service()
        self.consensus.stop_service()
        
        # Verify stopped state
        self.assertFalse(self.observer.running)
        self.assertFalse(self.consensus.running)

def run_manual_test():
    """Manual test function for development testing"""
    print("🚀 Starting BGP-Sentry Dual Service Integration Test")
    
    # Initialize services for AS05
    observer = RPKIObserverService(as_number=5)
    consensus = ConsensusService(as_number=5)
    
    try:
        # Start both services
        observer.start_service()
        consensus.start_service()
        
        print("✅ Both services started successfully")
        print("🔍 Observer: Monitoring BGP announcements...")
        print("⚖️  Consensus: Validating transactions...")
        
        # Run for 2 minutes
        time.sleep(120)
        
        # Show status
        print("\n📊 Service Status:")
        print(f"Observer: {observer.get_service_status()}")
        print(f"Consensus: {consensus.get_service_status()}")
        print(f"Voting Stats: {consensus.get_voting_statistics()}")
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    finally:
        observer.stop_service()
        consensus.stop_service()
        print("✅ All services stopped")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BGP-Sentry Service Tests")
    parser.add_argument("--manual", action="store_true", help="Run manual integration test")
    parser.add_argument("--unittest", action="store_true", help="Run unit tests")
    
    args = parser.parse_args()
    
    if args.manual:
        run_manual_test()
    elif args.unittest:
        unittest.main()
    else:
        # Default: run manual test
        run_manual_test()