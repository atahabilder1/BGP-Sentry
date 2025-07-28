#!/usr/bin/env python3
"""
=============================================================================
RPKI Observer Service - BGP Monitoring and Transaction Creation
=============================================================================

File: services/rpki_observer_service/observer_main.py
Purpose: Main service class for RPKI nodes to observe BGP announcements
         and create blockchain transactions for behavioral assessment

What this service does:
- Monitors local BGP announcements from network_stack/bgpd.json
- Validates BGP announcements against RPKI/IRR registries
- Creates and signs blockchain transactions for observed behavior
- Submits transactions to shared transaction pool for consensus

Components used:
- bgp_monitor.py - Parses BGP logs from network_stack
- transaction_creator.py - Creates and signs transactions
- utils_common/transaction_pool.py - Shared transaction queue
- shared_data/shared_registry/public_key_registry.json - Public keys
- private_key.pem - Node's private key for signing

External dependencies:
- network_stack/bgpd.json - BGP announcement data from router
- shared_data/state/trust_state.json - Current trust scores
- Other RPKI nodes for consensus validation

Author: BGP-Sentry Team
=============================================================================
"""

import logging
import time
import threading
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

class RPKIObserverService:
    """
    Main service class for RPKI node BGP observation and transaction creation.
    
    This service runs continuously to:
    1. Monitor BGP announcements from local network stack
    2. Validate announcements against RPKI/IRR
    3. Create signed transactions for blockchain
    4. Submit to transaction pool for consensus
    
    Architecture:
    BGP Router → network_stack/bgpd.json → BGPMonitor → TransactionCreator → TransactionPool
    """
    
    def __init__(self, as_number, network_stack_path="../network_stack", private_key_path="private_key.pem"):
        """
        Initialize RPKI Observer Service.
        
        Args:
            as_number: AS number of this RPKI observer (e.g., 5 for AS05)
            network_stack_path: Path to network_stack folder with bgpd.json
            private_key_path: Path to private key for transaction signing
        """
        self.as_number = as_number
        self.network_stack_path = Path(network_stack_path)
        self.private_key_path = Path(private_key_path)
        self.running = False
        
        # Configure logging
        self.logger = logging.getLogger(f"RPKIObserver-AS{as_number}")
        self.logger.setLevel(logging.INFO)
        
        # Initialize components
        self._initialize_components()
        
        self.logger.info(f"RPKI Observer Service initialized for AS{as_number}")
    
    def _initialize_components(self):
        """Initialize BGP monitor, transaction creator, and other components."""
        try:
            # Try to import real components
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, current_file_dir)
            
            utils_common_dir = os.path.join(current_file_dir, '..', '..', 'utils_common')
            utils_common_dir = os.path.abspath(utils_common_dir)
            sys.path.insert(0, utils_common_dir)
            
            from bgp_monitor import BGPMonitor
            from transaction_creator import TransactionCreator
            from transaction_pool import TransactionPool
            from trust_manager import TrustManager
            
            # Initialize BGP monitor for parsing network_stack/bgpd.json
            self.bgp_monitor = BGPMonitor(
                bgpd_path=self.network_stack_path / "bgpd.json",
                as_number=self.as_number
            )
            
            # Initialize transaction creator for signing transactions
            self.transaction_creator = TransactionCreator(
                as_number=self.as_number,
                private_key_path=self.private_key_path
            )
            
            # Initialize transaction pool for submitting transactions
            self.transaction_pool = TransactionPool()
            
            # Initialize trust manager for trust score access
            self.trust_manager = TrustManager()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            # Use fallback components for testing
            self._initialize_fallback_components()
    
    def _initialize_fallback_components(self):
        """Initialize fallback components if imports fail."""
        self.logger.warning("Using fallback components for testing")
        
        class FallbackBGPMonitor:
            def get_new_announcements(self):
                return [{
                    "sender_asn": 12,
                    "ip_prefix": "203.0.113.0/24",
                    "timestamp": datetime.now().isoformat(),
                    "announcement_type": "normal"
                }]
        
        class FallbackTransactionCreator:
            def __init__(self):
                self.as_number = None
                
            def create_transaction(self, bgp_data):
                return {
                    "transaction_id": f"tx_{int(time.time())}",
                    "observer_as": bgp_data.get('observer_as', 5),
                    "bgp_data": bgp_data,
                    "timestamp": datetime.now().isoformat(),
                    "signature": "fallback_signature"
                }
        
        class FallbackTransactionPool:
            def add_transaction(self, transaction):
                print(f"📤 Submitted transaction: {transaction['transaction_id']}")
                return True
        
        class FallbackTrustManager:
            def get_trust_score(self, as_number):
                return 80.0  # Default trust score
        
        self.bgp_monitor = FallbackBGPMonitor()
        self.transaction_creator = FallbackTransactionCreator()
        self.transaction_pool = FallbackTransactionPool()
        self.trust_manager = FallbackTrustManager()
    
    def start_service(self):
        """
        Start the RPKI Observer Service.
        
        Runs the main observation loop in a separate thread.
        """
        if self.running:
            self.logger.warning("Service already running")
            return
        
        self.running = True
        self.logger.info(f"Starting RPKI Observer Service for AS{self.as_number}")
        
        # Start main observation loop in background thread
        self.observer_thread = threading.Thread(
            target=self._observation_loop,
            name=f"RPKIObserver-AS{self.as_number}",
            daemon=True
        )
        self.observer_thread.start()
        
        self.logger.info("RPKI Observer Service started successfully")
    
    def stop_service(self):
        """Stop the RPKI Observer Service gracefully."""
        if not self.running:
            self.logger.warning("Service not running")
            return
        
        self.running = False
        self.logger.info("Stopping RPKI Observer Service...")
        
        # Wait for observer thread to finish
        if hasattr(self, 'observer_thread'):
            self.observer_thread.join(timeout=5)
        
        self.logger.info("RPKI Observer Service stopped")
    
    def _observation_loop(self):
        """
        Main observation loop - runs continuously to monitor BGP announcements.
        
        Loop process:
        1. Check for new BGP announcements in network_stack/bgpd.json
        2. Validate announcements (RPKI, IRR, behavioral checks)
        3. Create and sign transactions for observed behavior
        4. Submit transactions to shared pool for consensus
        5. Update local statistics and logs
        """
        self.logger.info("Starting BGP observation loop")
        
        while self.running:
            try:
                # 1. Monitor for new BGP announcements
                new_announcements = self.bgp_monitor.get_new_announcements()
                
                if new_announcements:
                    self.logger.info(f"Found {len(new_announcements)} new BGP announcements")
                    
                    # 2. Process each announcement
                    for announcement in new_announcements:
                        self._process_bgp_announcement(announcement)
                
                else:
                    self.logger.debug("No new BGP announcements found")
                
                # 3. Update service statistics
                self._update_statistics()
                
                # 4. Wait before next observation cycle
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in observation loop: {e}")
                time.sleep(10)  # Wait before retrying on error
    
    def _process_bgp_announcement(self, announcement):
        """
        Process a single BGP announcement through the blockchain pipeline.
        
        Args:
            announcement: Dict containing BGP announcement data
                         {sender_asn, ip_prefix, timestamp, announcement_type}
        
        Process:
        1. Validate BGP announcement (RPKI, IRR, behavioral)
        2. Determine if announcement needs blockchain recording
        3. Create and sign transaction if needed
        4. Submit to transaction pool
        """
        try:
            sender_asn = announcement.get('sender_asn')
            ip_prefix = announcement.get('ip_prefix')
            
            self.logger.info(f"Processing BGP announcement: AS{sender_asn} → {ip_prefix}")
            
            # 1. Validate BGP announcement
            validation_result = self._validate_announcement(announcement)
            
            # 2. Determine if blockchain recording is needed
            if self._needs_blockchain_record(announcement, validation_result):
                
                # 3. Create enhanced announcement data for transaction
                enhanced_data = {
                    **announcement,
                    'observer_as': self.as_number,
                    'validation_result': validation_result,
                    'trust_score': self.trust_manager.get_trust_score(sender_asn),
                    'processing_timestamp': datetime.now().isoformat()
                }
                
                # 4. Create and sign transaction
                transaction = self.transaction_creator.create_transaction(enhanced_data)
                
                if transaction:
                    # 5. Submit to transaction pool for consensus
                    success = self.transaction_pool.add_transaction(transaction)
                    
                    if success:
                        self.logger.info(f"✅ Transaction submitted: {transaction.get('transaction_id')}")
                    else:
                        self.logger.error(f"❌ Failed to submit transaction")
                
            else:
                self.logger.debug(f"Announcement does not need blockchain recording")
                
        except Exception as e:
            self.logger.error(f"Error processing BGP announcement: {e}")
    
    def _validate_announcement(self, announcement):
        """
        Validate BGP announcement against RPKI, IRR, and behavioral criteria.
        
        Args:
            announcement: BGP announcement data
            
        Returns:
            Dict with validation results {rpki_valid, irr_valid, behavioral_flags}
        """
        # Placeholder validation logic - replace with actual RPKI/IRR validation
        validation_result = {
            'rpki_valid': True,  # Would check against RPKI ROAs
            'irr_valid': True,   # Would check against IRR database
            'behavioral_flags': [],  # Would check for suspicious patterns
            'validation_timestamp': datetime.now().isoformat()
        }
        
        # Add behavioral analysis
        sender_asn = announcement.get('sender_asn')
        current_trust = self.trust_manager.get_trust_score(sender_asn)
        
        if current_trust < 30:
            validation_result['behavioral_flags'].append('low_trust_sender')
        
        return validation_result
    
    def _needs_blockchain_record(self, announcement, validation_result):
        """
        Determine if an announcement needs to be recorded on blockchain.
        
        Record on blockchain if:
        - RPKI validation failed (violation)
        - Sender has low trust score (monitoring)
        - Behavioral flags detected (suspicious activity)
        - Random sampling for good behavior tracking
        
        Args:
            announcement: BGP announcement data
            validation_result: Validation results
            
        Returns:
            Bool indicating if blockchain recording is needed
        """
        # Always record violations
        if not validation_result['rpki_valid'] or not validation_result['irr_valid']:
            return True
        
        # Record if behavioral flags detected
        if validation_result['behavioral_flags']:
            return True
        
        # Record for low trust senders (enhanced monitoring)
        sender_asn = announcement.get('sender_asn')
        trust_score = self.trust_manager.get_trust_score(sender_asn)
        if trust_score < 50:
            return True
        
        # Random sampling for good behavior (10% chance)
        import random
        if random.random() < 0.1:
            return True
        
        return False
    
    def _update_statistics(self):
        """Update service statistics and performance metrics."""
        # Placeholder for statistics tracking
        pass
    
    def get_service_status(self):
        """
        Get current service status and statistics.
        
        Returns:
            Dict with service status information
        """
        return {
            'service_name': 'RPKI Observer Service',
            'as_number': self.as_number,
            'running': self.running,
            'network_stack_path': str(self.network_stack_path),
            'private_key_path': str(self.private_key_path),
            'uptime': time.time() if self.running else 0
        }

# Example usage and testing
if __name__ == "__main__":
    # Example: Start RPKI Observer Service for AS05
    observer = RPKIObserverService(
        as_number=5,
        network_stack_path="../network_stack",
        private_key_path="private_key.pem"
    )
    
    try:
        observer.start_service()
        print("🔍 RPKI Observer Service started - monitoring BGP announcements...")
        
        # Run for testing (in production, this would run indefinitely)
        time.sleep(60)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down RPKI Observer Service...")
    finally:
        observer.stop_service()
        print("✅ RPKI Observer Service stopped")