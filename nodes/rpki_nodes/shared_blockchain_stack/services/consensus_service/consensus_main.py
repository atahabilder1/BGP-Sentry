#!/usr/bin/env python3
"""
=============================================================================
Consensus Service - Transaction Validation and Blockchain Management
=============================================================================

File: services/consensus_service/consensus_main.py
Purpose: Main service class for validating transactions from other RPKI nodes
         and managing blockchain consensus process

What this service does:
- Monitors shared transaction pool for pending transactions
- Validates signatures using shared public key registry
- Checks trust scores and staking requirements
- Participates in multi-node consensus voting
- Commits approved transactions to blockchain

Components used:
- transaction_validator.py - Validates signatures and economic requirements
- blockchain_writer.py - Writes approved transactions to blockchain
- utils_common/transaction_pool.py - Shared transaction queue
- shared_data/shared_registry/public_key_registry.json - Public keys for verification
- shared_data/state/trust_state.json - Trust scores for validation

Consensus model:
- Each RPKI node validates others' transactions (signature verification only)
- Cannot verify BGP content (information asymmetry)
- Requires majority approval (6/9 RPKI nodes) for blockchain commit
- Economic validation (trust scores + staking) before consensus

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

# Add paths for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "nodes" / "rpki_nodes"))

# Import components
try:
    from .transaction_validator import verify_transaction
    from .blockchain_writer import BlockchainWriter
    from ...blockchain_utils.transaction_pool import TransactionPool
    from ...blockchain_utils.signature_utils import SignatureUtils
    from ...blockchain_utils.trust_manager import TrustManager
except ImportError:
    # Fallback for testing
    print("⚠️  Import error - using fallback classes")

class ConsensusService:
    """
    Main service class for RPKI node consensus and blockchain management.
    
    This service runs continuously to:
    1. Monitor transaction pool for pending transactions
    2. Validate signatures from other RPKI nodes
    3. Check economic requirements (trust + staking)
    4. Participate in multi-node consensus voting
    5. Commit approved transactions to blockchain
    
    Architecture:
    TransactionPool → TransactionValidator → Consensus → BlockchainWriter → Blockchain
    """
    
    def __init__(self, as_number, consensus_threshold=0.67):
        """
        Initialize Consensus Service.
        
        Args:
            as_number: AS number of this RPKI node (e.g., 5 for AS05)
            consensus_threshold: Percentage of nodes needed for consensus (default 67%)
        """
        self.as_number = as_number
        self.consensus_threshold = consensus_threshold
        self.total_rpki_nodes = 9  # Total number of RPKI nodes in network
        self.min_consensus_votes = int(self.total_rpki_nodes * consensus_threshold)
        self.running = False
        
        # Configure logging
        self.logger = logging.getLogger(f"Consensus-AS{as_number}")
        self.logger.setLevel(logging.INFO)
        
        # Initialize components
        self._initialize_components()
        
        # Voting tracking
        self.pending_votes = {}  # transaction_id -> {votes: [], approved: bool}
        
        self.logger.info(f"Consensus Service initialized for AS{as_number}")
        self.logger.info(f"Consensus threshold: {consensus_threshold} ({self.min_consensus_votes}/{self.total_rpki_nodes} nodes)")
    
    def _initialize_components(self):
        """Initialize transaction validator, blockchain writer, and other components."""
        try:
            # Initialize transaction validator for signature and economic validation
            self.verify_transaction_func = verify_transaction(
                as_number=self.as_number
            )
            
            # Initialize blockchain writer for committing transactions
            self.commit_to_blockchain_func = BlockchainWriter()
            
            # Initialize transaction pool for monitoring pending transactions
            self.transaction_pool = TransactionPool()
            
            # Initialize signature utilities for cryptographic verification
            self.signature_utils = SignatureUtils()
            
            # Initialize trust manager for economic validation
            self.trust_manager = TrustManager()
            
            self.logger.info("All consensus components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Consensus component initialization failed: {e}")
            # Use fallback components for testing
            self._initialize_fallback_components()
    
    def _initialize_fallback_components(self):
        """Initialize fallback components if imports fail."""
        self.logger.warning("Using fallback consensus components for testing")
        
        class FallbackValidator:
            def validate_transaction(self, transaction):
                return {
                    'signature_valid': True,
                    'trust_check': True,
                    'staking_check': True,
                    'overall_valid': True
                }
        
        class FallbackBlockchainWriter:
            def commit_transaction(self, transaction):
                print(f"⛓️  Committed to blockchain: {transaction.get('transaction_id')}")
                return True
        
        class FallbackTransactionPool:
            def get_pending_transactions(self):
                return []  # No pending transactions in fallback
            
            def mark_transaction_processed(self, tx_id):
                print(f"✅ Marked transaction processed: {tx_id}")
        
        class FallbackSignatureUtils:
            def verify_signature(self, data, signature, public_key):
                return True  # Always valid in fallback
        
        class FallbackTrustManager:
            def get_trust_score(self, as_number):
                return 100.0
        
        self.transaction_validator = FallbackValidator()
        self.blockchain_writer = FallbackBlockchainWriter()
        self.transaction_pool = FallbackTransactionPool()
        self.signature_utils = FallbackSignatureUtils()
        self.trust_manager = FallbackTrustManager()
    
    def start_service(self):
        """
        Start the Consensus Service.
        
        Runs the main consensus loop in a separate thread.
        """
        if self.running:
            self.logger.warning("Consensus service already running")
            return
        
        self.running = True
        self.logger.info(f"Starting Consensus Service for AS{self.as_number}")
        
        # Start main consensus loop in background thread
        self.consensus_thread = threading.Thread(
            target=self._consensus_loop,
            name=f"Consensus-AS{self.as_number}",
            daemon=True
        )
        self.consensus_thread.start()
        
        self.logger.info("Consensus Service started successfully")
    
    def stop_service(self):
        """Stop the Consensus Service gracefully."""
        if not self.running:
            self.logger.warning("Consensus service not running")
            return
        
        self.running = False
        self.logger.info("Stopping Consensus Service...")
        
        # Wait for consensus thread to finish
        if hasattr(self, 'consensus_thread'):
            self.consensus_thread.join(timeout=5)
        
        self.logger.info("Consensus Service stopped")
    
    def _consensus_loop(self):
        """
        Main consensus loop - runs continuously to validate and approve transactions.
        
        Loop process:
        1. Get pending transactions from shared pool
        2. Validate each transaction (signature + economics)
        3. Cast vote for valid transactions
        4. Check if consensus threshold reached
        5. Commit approved transactions to blockchain
        6. Clean up processed transactions
        """
        self.logger.info("Starting consensus validation loop")
        
        while self.running:
            try:
                # 1. Get pending transactions from pool
                pending_transactions = self.transaction_pool.get_pending_transactions()
                
                if pending_transactions:
                    self.logger.info(f"Processing {len(pending_transactions)} pending transactions")
                    
                    # 2. Process each pending transaction
                    for transaction in pending_transactions:
                        self._process_transaction_for_consensus(transaction)
                
                # 3. Check for transactions ready for blockchain commit
                self._process_consensus_results()
                
                # 4. Clean up old voting records
                self._cleanup_old_votes()
                
                # 5. Wait before next consensus cycle
                time.sleep(45)  # Consensus check every 45 seconds
                
            except Exception as e:
                self.logger.error(f"Error in consensus loop: {e}")
                time.sleep(10)  # Wait before retrying on error
    
    def _process_transaction_for_consensus(self, transaction):
        """
        Process a single transaction for consensus validation.
        
        Args:
            transaction: Transaction dict from transaction pool
        
        Process:
        1. Validate transaction (signature, trust, staking)
        2. Cast vote if validation passes
        3. Update consensus tracking
        """
        try:
            tx_id = transaction.get('transaction_id')
            observer_as = transaction.get('observer_as')
            
            self.logger.debug(f"Validating transaction {tx_id} from AS{observer_as}")
            
            # Skip transactions from our own AS (can't validate our own submissions)
            if observer_as == self.as_number:
                self.logger.debug(f"Skipping own transaction: {tx_id}")
                return
            
            # 1. Validate transaction
            validation_result = self.transaction_validator.validate_transaction(transaction)
            
            if validation_result.get('overall_valid'):
                # 2. Cast approval vote
                self._cast_vote(tx_id, vote='approve', validator_as=self.as_number)
                
                self.logger.info(f"✅ Approved transaction {tx_id} from AS{observer_as}")
                
            else:
                # 3. Cast rejection vote
                self._cast_vote(tx_id, vote='reject', validator_as=self.as_number)
                
                self.logger.warning(f"❌ Rejected transaction {tx_id} from AS{observer_as}: {validation_result}")
                
        except Exception as e:
            self.logger.error(f"Error processing transaction for consensus: {e}")
    
    def _cast_vote(self, transaction_id, vote, validator_as):
        """
        Cast a vote for a transaction.
        
        Args:
            transaction_id: ID of transaction being voted on
            vote: 'approve' or 'reject'
            validator_as: AS number of validator casting vote
        """
        if transaction_id not in self.pending_votes:
            self.pending_votes[transaction_id] = {
                'votes': [],
                'approved': False,
                'rejected': False,
                'vote_timestamp': datetime.now().isoformat()
            }
        
        # Add vote to tracking
        vote_record = {
            'validator_as': validator_as,
            'vote': vote,
            'timestamp': datetime.now().isoformat()
        }
        
        self.pending_votes[transaction_id]['votes'].append(vote_record)
        
        self.logger.debug(f"Vote cast: {vote} for {transaction_id} by AS{validator_as}")
    
    def _process_consensus_results(self):
        """
        Check pending votes and commit transactions that reach consensus.
        """
        for tx_id, vote_data in list(self.pending_votes.items()):
            if vote_data.get('approved') or vote_data.get('rejected'):
                continue  # Already processed
            
            # Count votes
            approval_votes = len([v for v in vote_data['votes'] if v['vote'] == 'approve'])
            rejection_votes = len([v for v in vote_data['votes'] if v['vote'] == 'reject'])
            total_votes = approval_votes + rejection_votes
            
            # Check if consensus threshold reached
            if approval_votes >= self.min_consensus_votes:
                # Transaction approved - commit to blockchain
                self._commit_approved_transaction(tx_id)
                vote_data['approved'] = True
                
                self.logger.info(f"🎉 Transaction {tx_id} approved by consensus ({approval_votes}/{self.total_rpki_nodes} votes)")
                
            elif rejection_votes >= self.min_consensus_votes:
                # Transaction rejected
                vote_data['rejected'] = True
                
                self.logger.info(f"🚫 Transaction {tx_id} rejected by consensus ({rejection_votes}/{self.total_rpki_nodes} votes)")
                
            elif total_votes >= self.total_rpki_nodes:
                # All nodes voted but no consensus - consider failed
                vote_data['rejected'] = True
                
                self.logger.warning(f"⚠️  Transaction {tx_id} failed consensus (no majority)")
    
    def _commit_approved_transaction(self, transaction_id):
        """
        Commit an approved transaction to the blockchain.
        
        Args:
            transaction_id: ID of approved transaction
        """
        try:
            # Get full transaction data from pool
            transaction = self.transaction_pool.get_transaction_by_id(transaction_id)
            
            if transaction:
                # Commit to blockchain
                success = self.blockchain_writer.commit_transaction(transaction)
                
                if success:
                    # Mark as processed in transaction pool
                    self.transaction_pool.mark_transaction_processed(transaction_id)
                    
                    self.logger.info(f"⛓️  Transaction {transaction_id} committed to blockchain")
                    
                    # Update trust scores based on transaction
                    self._update_trust_scores_from_transaction(transaction)
                    
                else:
                    self.logger.error(f"Failed to commit transaction {transaction_id} to blockchain")
            else:
                self.logger.error(f"Transaction {transaction_id} not found in pool")
                
        except Exception as e:
            self.logger.error(f"Error committing transaction to blockchain: {e}")
    
    def _update_trust_scores_from_transaction(self, transaction):
        """
        Update trust scores based on transaction content.
        
        Args:
            transaction: Committed transaction data
        """
        try:
            # Extract BGP data from transaction
            bgp_data = transaction.get('bgp_data', {})
            sender_asn = bgp_data.get('sender_asn')
            validation_result = bgp_data.get('validation_result', {})
            
            if sender_asn:
                # This would integrate with the trust engine
                # For now, placeholder logic
                if not validation_result.get('rpki_valid'):
                    # Penalty for RPKI violation
                    current_trust = self.trust_manager.get_trust_score(sender_asn)
                    new_trust = max(0, current_trust - 15)  # 15 point penalty
                    self.trust_manager.update_trust_score(sender_asn, new_trust)
                    
                    self.logger.info(f"Applied trust penalty to AS{sender_asn}: {current_trust} → {new_trust}")
                
        except Exception as e:
            self.logger.error(f"Error updating trust scores: {e}")
    
    def _cleanup_old_votes(self):
        """Clean up old voting records to prevent memory leaks."""
        current_time = datetime.now()
        cutoff_hours = 24  # Remove votes older than 24 hours
        
        for tx_id in list(self.pending_votes.keys()):
            vote_data = self.pending_votes[tx_id]
            vote_time = datetime.fromisoformat(vote_data['vote_timestamp'])
            
            if (current_time - vote_time).total_seconds() > (cutoff_hours * 3600):
                del self.pending_votes[tx_id]
                self.logger.debug(f"Cleaned up old vote record for {tx_id}")
    
    def get_service_status(self):
        """
        Get current consensus service status and statistics.
        
        Returns:
            Dict with service status information
        """
        return {
            'service_name': 'Consensus Service',
            'as_number': self.as_number,
            'running': self.running,
            'consensus_threshold': self.consensus_threshold,
            'min_votes_needed': self.min_consensus_votes,
            'total_rpki_nodes': self.total_rpki_nodes,
            'pending_votes': len(self.pending_votes),
            'uptime': time.time() if self.running else 0
        }
    
    def get_voting_statistics(self):
        """
        Get detailed voting statistics.
        
        Returns:
            Dict with voting statistics
        """
        if not self.pending_votes:
            return {'total_transactions': 0}
        
        approved = len([v for v in self.pending_votes.values() if v.get('approved')])
        rejected = len([v for v in self.pending_votes.values() if v.get('rejected')])
        pending = len([v for v in self.pending_votes.values() if not v.get('approved') and not v.get('rejected')])
        
        return {
            'total_transactions': len(self.pending_votes),
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'approval_rate': approved / len(self.pending_votes) if self.pending_votes else 0
        }

# Example usage and testing
if __name__ == "__main__":
    # Example: Start Consensus Service for AS05
    consensus = ConsensusService(
        as_number=5,
        consensus_threshold=0.67  # 67% consensus threshold
    )
    
    try:
        consensus.start_service()
        print("⚖️  Consensus Service started - validating transactions...")
        
        # Run for testing (in production, this would run indefinitely)
        time.sleep(60)
        
        # Show statistics
        status = consensus.get_service_status()
        stats = consensus.get_voting_statistics()
        print(f"Status: {status}")
        print(f"Voting Stats: {stats}")
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Consensus Service...")
    finally:
        consensus.stop_service()
        print("✅ Consensus Service stopped")