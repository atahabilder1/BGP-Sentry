#!/usr/bin/env python3
import sys
import os
import time
from pathlib import Path

class BlockchainNode:
    def __init__(self):
        # Get AS number from file path
        current_path = Path(__file__).resolve()
        as_dir = current_path.parent.parent.name  # Get as01, as03, etc.
        self.as_number = int(as_dir.replace('as', '').lstrip('0'))
        self.node_id = f"AS{self.as_number:02d}"
        
        print(f"Starting {self.node_id} blockchain node...")
        
        # Import and initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize the two main services"""
        try:
            # Fix import paths - shared_blockchain_stack is at rpki_nodes level
            shared_stack = Path(__file__).parent.parent.parent / "shared_blockchain_stack"
            sys.path.insert(0, str(shared_stack))
            
            # Try importing your services
            from services.rpki_observer_service.observer_main import RPKIObserverService
            from services.consensus_service.consensus_main import ConsensusService
            
            # Initialize services
            self.observer_service = RPKIObserverService(
                as_number=self.as_number,
                network_stack_path="../network_stack",
                private_key_path="private_key.pem"
            )
            
            self.consensus_service = ConsensusService(
                as_number=self.as_number,
                consensus_threshold=0.33  # 3/9 nodes needed
            )
            
            print(f"{self.node_id}: Services initialized successfully")
            
        except Exception as e:
            print(f"{self.node_id}: Service initialization failed - {e}")
            print(f"{self.node_id}: Using simplified blockchain node")
            self._initialize_simple_node()
    
    def _initialize_simple_node(self):
        """Fallback simple node implementation"""
        self.observer_service = None
        self.consensus_service = None
    
    def run(self):
        """Main node execution"""
        if self.observer_service and self.consensus_service:
            self._run_full_node()
        else:
            self._run_simple_node()
    
    def _run_full_node(self):
        """Run full blockchain node with observer and consensus services"""
        print(f"{self.node_id}: Starting full blockchain node...")
        
        try:
            self.observer_service.start_service()
            self.consensus_service.start_service()
            
            print(f"{self.node_id}: Both services running - monitoring BGP and participating in consensus")
            
            while True:
                time.sleep(30)
                
        except KeyboardInterrupt:
            print(f"{self.node_id}: Shutting down...")
            if self.observer_service:
                self.observer_service.stop_service()
            if self.consensus_service:
                self.consensus_service.stop_service()
    
    def _run_simple_node(self):
        """Run simplified blockchain node for testing"""
        print(f"{self.node_id}: Running simplified blockchain node...")
        
        block_count = 0
        try:
            while block_count < 10:
                print(f"{self.node_id}: Processing BGP data - block {block_count}")
                
                if block_count % 3 == 0:
                    print(f"{self.node_id}: Participating in consensus voting")
                
                block_count += 1
                time.sleep(5)
                
        except KeyboardInterrupt:
            print(f"{self.node_id}: Interrupted, shutting down...")
        
        print(f"{self.node_id}: Processed {block_count} blocks, shutting down")

if __name__ == "__main__":
    node = BlockchainNode()
    node.run()
