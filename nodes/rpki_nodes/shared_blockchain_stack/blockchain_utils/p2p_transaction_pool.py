#!/usr/bin/env python3
import json
import logging
import socket
import threading
import sys
from pathlib import Path
from datetime import datetime

# Import BlockchainInterface for writing to blockchain
from blockchain_interface import BlockchainInterface

# Import BGPCOIN ledger for token rewards
from bgpcoin_ledger import BGPCoinLedger

# Import RPKI Node Registry for AS type checking
from rpki_node_registry import RPKINodeRegistry

# Import Relevant Neighbor Cache for optimized voting
sys.path.insert(0, str(Path(__file__).parent.parent / "network_stack"))
from relevant_neighbor_cache import RelevantNeighborCache

class P2PTransactionPool:
    """
    Peer-to-peer transaction pool with direct node-to-node communication.
    Each node maintains its own pool and communicates directly with peers.
    """
    
    def __init__(self, as_number, base_port=8000):
        self.as_number = as_number
        self.my_port = base_port + as_number

        # Get peer RPKI nodes from registry (excludes self automatically)
        self.peer_nodes = RPKINodeRegistry.get_peer_nodes(self.as_number)

        # Initialize blockchain interface for writing to chain/ folder
        # Each node writes to its own blockchain file:
        # Path: nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/
        as_formatted = f"as{self.as_number:02d}"  # Format as as01, as03, etc.
        blockchain_path = f"nodes/rpki_nodes/{as_formatted}/blockchain_node/blockchain_data/chain"
        self.blockchain = BlockchainInterface(blockchain_path)

        # P2P communication
        self.server_socket = None
        self.running = False
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"P2P-AS{self.as_number}")

        # Transaction voting tracking (need 3/9 for consensus)
        self.pending_votes = {}  # transaction_id -> {transaction: {}, votes: [], needed: 3}
        self.committed_transactions = set()  # Track already committed transactions
        self.total_nodes = RPKINodeRegistry.get_node_count()
        self.consensus_threshold = 3  # 3/9 = 33% consensus (minimum 3 votes)

        # Knowledge base for time-windowed BGP observations
        # Each node maintains observations to validate incoming transactions
        self.knowledge_base = []  # List of observed BGP announcements
        self.knowledge_window_seconds = 480  # Keep observations ±8 minutes (480 seconds)
        self.cleanup_interval = 60  # Clean old observations every 60 seconds

        # Transaction timeout configuration
        self.REGULAR_TIMEOUT = 60       # 1 minute for regular announcements
        self.ATTACK_TIMEOUT = 180       # 3 minutes for attack transactions

        # Sampling configuration for regular announcements
        self.SAMPLING_WINDOW_SECONDS = 3600  # 1 hour - ignore duplicates within this window

        # Persistent storage for knowledge base
        self.knowledge_base_file = self.blockchain.state_dir / "knowledge_base.json"

        # Sampling cache: Track last seen time for each (ip_prefix, as_number)
        # Format: {(ip_prefix, as_number): last_seen_timestamp}
        # This allows O(1) lookup instead of scanning blockchain
        self.last_seen_cache = {}
        self.last_seen_cache_file = self.blockchain.state_dir / "last_seen_announcements.json"

        # Load existing knowledge base from disk
        self._load_knowledge_base()

        # Load last_seen cache from disk
        self._load_last_seen_cache()

        # Initialize BGPCOIN ledger for token rewards
        self.bgpcoin_ledger = BGPCoinLedger(ledger_path=self.blockchain.state_dir)
        self.logger.info(f"💰 BGPCOIN ledger initialized")

        # Track first commit for bonus rewards
        self.first_commit_tracker = {}  # transaction_id -> first_committer_as

        # Initialize governance system (will be initialized after P2P server starts)
        self.governance = None

        # Initialize attack consensus (will be initialized after P2P server starts)
        self.attack_consensus = None

        # Initialize relevant neighbor cache for optimized voting
        network_stack_path = Path(__file__).parent.parent / "network_stack"
        self.neighbor_cache = RelevantNeighborCache(
            cache_path=str(network_stack_path),
            my_as_number=self.as_number
        )
        self.logger.info(f"📡 Neighbor cache initialized")

        # Start background threads
        cleanup_thread = threading.Thread(target=self._cleanup_old_observations, daemon=True)
        cleanup_thread.start()

        save_thread = threading.Thread(target=self._periodic_save_knowledge_base, daemon=True)
        save_thread.start()

        # Cleanup thread for last_seen cache
        cache_cleanup_thread = threading.Thread(target=self._periodic_cleanup_last_seen_cache, daemon=True)
        cache_cleanup_thread.start()

        # Timeout cleanup thread for pending transactions
        timeout_thread = threading.Thread(target=self._cleanup_timed_out_transactions, daemon=True)
        timeout_thread.start()
    
    def start_p2p_server(self):
        """Start P2P server to listen for incoming messages"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("localhost", self.my_port))
            self.server_socket.listen(5)
            self.running = True

            self.logger.info(f"P2P server started on port {self.my_port}")

            # Initialize governance system now that P2P is ready
            from governance_system import GovernanceSystem
            self.governance = GovernanceSystem(
                as_number=self.as_number,
                bgpcoin_ledger=self.bgpcoin_ledger,
                p2p_pool=self,
                governance_path=self.blockchain.state_dir
            )
            self.logger.info(f"📜 Governance system initialized")

            # Initialize attack consensus system
            from attack_detector import AttackDetector
            from nonrpki_rating import NonRPKIRatingSystem
            from attack_consensus import AttackConsensus

            attack_detector = AttackDetector(
                roa_database_path=str(self.blockchain.state_dir / "roa_database.json"),
                as_relationships_path=str(self.blockchain.state_dir / "as_relationships.json")
            )

            rating_system = NonRPKIRatingSystem(
                rating_path=str(self.blockchain.state_dir)
            )

            self.attack_consensus = AttackConsensus(
                as_number=self.as_number,
                attack_detector=attack_detector,
                rating_system=rating_system,
                bgpcoin_ledger=self.bgpcoin_ledger,
                p2p_pool=self,
                blockchain_dir=self.blockchain.blockchain_dir
            )
            self.logger.info(f"🛡️  Attack consensus system initialized")

            # Start server thread
            server_thread = threading.Thread(target=self._server_loop, daemon=True)
            server_thread.start()

        except Exception as e:
            self.logger.error(f"Failed to start P2P server: {e}")
    
    def _server_loop(self):
        """Listen for incoming P2P messages"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket,), 
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"Server loop error: {e}")
    
    def _handle_client(self, client_socket):
        """Handle incoming P2P message"""
        try:
            data = client_socket.recv(4096).decode('utf-8')
            message = json.loads(data)

            if message["type"] == "vote_request":
                self._handle_vote_request(message)
            elif message["type"] == "vote_response":
                self._handle_vote_response(message)
            elif message["type"] == "governance_proposal":
                # Handle governance proposal (monthly analysis, etc.)
                if self.governance:
                    self.governance.handle_proposal_message(message)
            elif message["type"] == "governance_vote":
                # Handle governance vote
                if self.governance:
                    self.governance.handle_vote_message(message)
            elif message["type"] == "attack_proposal":
                # Handle attack detection proposal
                if self.attack_consensus:
                    self.attack_consensus.handle_attack_proposal(message)
            elif message["type"] == "attack_vote":
                # Handle attack vote
                if self.attack_consensus:
                    self.attack_consensus.handle_attack_vote(message)

        except Exception as e:
            self.logger.error(f"Error handling client message: {e}")
        finally:
            client_socket.close()
    
    def _handle_vote_request(self, message):
        """Handle incoming vote request from another node"""
        transaction = message["transaction"]
        from_as = message["from_as"]
        
        self.logger.info(f"Received vote request for {transaction['transaction_id']} from AS{from_as}")
        
        # Validate transaction (simplified)
        vote = self._validate_transaction(transaction)
        
        # Send vote back
        self._send_vote_to_node(from_as, transaction["transaction_id"], vote)
    
    def _handle_vote_response(self, message):
        """
        Handle incoming signature (vote) response from peer.

        SECURITY: Vote deduplication prevents replay attacks:
        - Each AS can only vote once per transaction
        - Total votes cannot exceed total nodes (9)
        - Duplicate votes are rejected with warning
        """
        tx_id = message["transaction_id"]
        vote = message["vote"]
        from_as = message["from_as"]

        if tx_id not in self.pending_votes:
            self.logger.warning(f"Received vote for unknown transaction {tx_id}")
            return

        # Variable to store commit decision (determined inside lock)
        should_commit = False

        # CRITICAL SECTION: Hold lock ONLY for data structure access
        # DO NOT hold lock during I/O operations!
        with self.lock:
            # Check if already committed (prevent duplicates)
            if tx_id in self.committed_transactions:
                self.logger.debug(f"Transaction {tx_id} already committed, skipping")
                return

            # VOTE DEDUPLICATION: Check if this AS already voted
            existing_voters = [v["from_as"] for v in self.pending_votes[tx_id]["votes"]]

            if from_as in existing_voters:
                self.logger.warning(
                    f"🚨 REPLAY ATTACK DETECTED: AS{from_as} already voted on {tx_id}, rejecting duplicate vote"
                )
                return  # Reject duplicate vote

            # SANITY CHECK: Ensure vote count doesn't exceed total nodes
            if len(existing_voters) >= self.total_nodes:
                self.logger.error(
                    f"🚨 VOTE OVERFLOW: Transaction {tx_id} already has {len(existing_voters)} votes "
                    f"(max={self.total_nodes}), rejecting vote from AS{from_as}"
                )
                return  # Reject overflow

            # Record signature/vote (now guaranteed to be unique)
            self.pending_votes[tx_id]["votes"].append({
                "from_as": from_as,
                "vote": vote,
                "timestamp": message.get("timestamp")
            })

            self.logger.info(f"✅ Received signature from AS{from_as} for {tx_id}")

            # Check if consensus reached (3/9 signatures minimum)
            approve_votes = len([v for v in self.pending_votes[tx_id]["votes"] if v["vote"] == "approve"])

            self.logger.info(f"Signatures collected: {approve_votes}/{self.consensus_threshold} for {tx_id}")

            if approve_votes >= self.consensus_threshold:
                # Mark as committed BEFORE writing to prevent race condition
                self.committed_transactions.add(tx_id)

                # Set flag to commit (will happen OUTSIDE lock)
                should_commit = True

                self.logger.info(f"🎉 CONSENSUS REACHED ({approve_votes}/{self.total_nodes}) - Will write to blockchain!")

        # LOCK RELEASED HERE - Other threads can now process votes concurrently!

        # NON-CRITICAL SECTION: I/O operations (blockchain write, BGPCOIN, attack detection)
        # This can take several seconds, but lock is FREE for other threads
        if should_commit:
            self._commit_to_blockchain(tx_id)
    
    def broadcast_transaction(self, transaction):
        """
        Broadcast transaction to RELEVANT peer nodes for signature collection.

        OPTIMIZATION: Uses neighbor cache to only query RPKI nodes that are
        likely to have observed this announcement (based on AS topology).

        TIMEOUT: Tracks creation time for timeout handling (60s regular, 180s attack)
        """
        tx_id = transaction["transaction_id"]
        sender_asn = transaction.get("sender_asn")

        self.pending_votes[tx_id] = {
            "transaction": transaction,
            "votes": [],
            "needed": self.consensus_threshold,
            "created_at": datetime.now(),  # Track creation time for timeout
            "is_attack": transaction.get("is_attack", False)  # Track type for timeout duration
        }

        # Get relevant neighbors from cache (optimized voting)
        relevant_neighbors = self.neighbor_cache.get_relevant_neighbors(sender_asn)

        # Filter to only neighbors in our peer list
        target_peers = {
            peer_as: (host, port)
            for peer_as, (host, port) in self.peer_nodes.items()
            if peer_as in relevant_neighbors
        }

        # Fallback: if no relevant neighbors, use all peers
        if not target_peers:
            target_peers = self.peer_nodes
            self.logger.warning(f"⚠️  No relevant neighbors cached for AS{sender_asn}, using all peers")

        # Send vote requests to relevant peers only
        for peer_as, (host, port) in target_peers.items():
            self._send_vote_request_to_node(peer_as, host, port, transaction)

        self.logger.info(f"📡 Broadcast transaction {tx_id} to {len(target_peers)}/{len(self.peer_nodes)} "
                        f"relevant peers (AS{sender_asn})")
    
    def _send_vote_request_to_node(self, peer_as, host, port, transaction):
        """Send vote request to specific peer node"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            sock.connect((host, port))
            
            message = {
                "type": "vote_request",
                "from_as": self.as_number,
                "transaction": transaction,
                "timestamp": datetime.now().isoformat()
            }
            
            sock.send(json.dumps(message).encode('utf-8'))
            sock.close()
            
        except Exception as e:
            self.logger.warning(f"Failed to send vote request to AS{peer_as}: {e}")
    
    def _send_vote_to_node(self, target_as, transaction_id, vote):
        """Send vote response to specific node"""
        if target_as not in self.peer_nodes:
            return
            
        host, port = self.peer_nodes[target_as]
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            
            message = {
                "type": "vote_response", 
                "from_as": self.as_number,
                "transaction_id": transaction_id,
                "vote": vote,
                "timestamp": datetime.now().isoformat()
            }
            
            sock.send(json.dumps(message).encode('utf-8'))
            sock.close()
            
            self.logger.info(f"Sent {vote} vote for {transaction_id} to AS{target_as}")
            
        except Exception as e:
            self.logger.warning(f"Failed to send vote to AS{target_as}: {e}")
    
    def _check_recent_announcement_in_cache(self, ip_prefix, sender_asn):
        """
        Check if same announcement (prefix, AS) was recorded within last 1 hour.
        Uses in-memory cache for O(1) lookup instead of scanning blockchain.

        Args:
            ip_prefix: IP prefix to check
            sender_asn: AS number to check

        Returns:
            True if found in last hour (should skip), False otherwise (should record)
        """
        try:
            cache_key = (ip_prefix, sender_asn)
            current_time = datetime.now().timestamp()
            cutoff_time = current_time - self.SAMPLING_WINDOW_SECONDS

            # Check cache
            if cache_key in self.last_seen_cache:
                last_seen = self.last_seen_cache[cache_key]

                if last_seen > cutoff_time:
                    # Found within 1 hour window
                    time_since = int(current_time - last_seen)
                    self.logger.info(f"📊 Sampling: {ip_prefix} from AS{sender_asn} seen {time_since}s ago, skipping")
                    return True  # Skip

            return False  # Not found or too old, should record

        except Exception as e:
            self.logger.error(f"Error checking last seen cache: {e}")
            return False  # On error, allow recording

    def _update_last_seen_cache(self, ip_prefix, sender_asn):
        """
        Update last seen timestamp for this (prefix, AS) pair.
        Called when transaction is successfully committed to blockchain.

        Args:
            ip_prefix: IP prefix
            sender_asn: AS number
        """
        cache_key = (ip_prefix, sender_asn)
        self.last_seen_cache[cache_key] = datetime.now().timestamp()

        # Periodically save cache to disk (every 100 updates)
        if len(self.last_seen_cache) % 100 == 0:
            self._save_last_seen_cache()

    def _save_last_seen_cache(self):
        """
        Save last_seen_cache to disk for persistence across restarts.
        """
        try:
            # Convert tuple keys to strings for JSON serialization
            serializable_cache = {
                f"{ip_prefix}|{asn}": timestamp
                for (ip_prefix, asn), timestamp in self.last_seen_cache.items()
            }

            data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "cache": serializable_cache
            }

            temp_file = self.last_seen_cache_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.last_seen_cache_file)
            self.logger.debug(f"💾 Saved last_seen cache ({len(serializable_cache)} entries)")

        except Exception as e:
            self.logger.error(f"Error saving last_seen cache: {e}")

    def _load_last_seen_cache(self):
        """
        Load last_seen_cache from disk on startup.
        """
        try:
            if self.last_seen_cache_file.exists():
                with open(self.last_seen_cache_file, 'r') as f:
                    data = json.load(f)

                # Convert string keys back to tuples
                serializable_cache = data.get('cache', {})
                current_time = datetime.now().timestamp()
                cutoff_time = current_time - self.SAMPLING_WINDOW_SECONDS

                valid_entries = 0
                for key_str, timestamp in serializable_cache.items():
                    # Only load entries within sampling window (not expired)
                    if timestamp > cutoff_time:
                        ip_prefix, asn = key_str.split('|', 1)
                        self.last_seen_cache[(ip_prefix, int(asn))] = timestamp
                        valid_entries += 1

                self.logger.info(f"📂 Loaded last_seen cache ({valid_entries} valid entries)")
            else:
                self.logger.info("📂 No last_seen cache found, starting fresh")

        except Exception as e:
            self.logger.error(f"Error loading last_seen cache: {e}")
            self.last_seen_cache = {}

    def _cleanup_last_seen_cache(self):
        """
        Remove expired entries from last_seen_cache (older than 1 hour).
        Called periodically to prevent unbounded growth.
        """
        try:
            current_time = datetime.now().timestamp()
            cutoff_time = current_time - self.SAMPLING_WINDOW_SECONDS

            initial_size = len(self.last_seen_cache)

            # Remove expired entries
            self.last_seen_cache = {
                key: timestamp
                for key, timestamp in self.last_seen_cache.items()
                if timestamp > cutoff_time
            }

            removed = initial_size - len(self.last_seen_cache)
            if removed > 0:
                self.logger.debug(f"🧹 Cleaned {removed} expired entries from last_seen cache")

        except Exception as e:
            self.logger.error(f"Error cleaning last_seen cache: {e}")

    def _periodic_cleanup_last_seen_cache(self):
        """
        Background thread that periodically cleans last_seen_cache.
        Runs every hour to remove expired entries and save to disk.
        """
        import time

        # Wait for server to start
        time.sleep(10)

        while self.running:
            try:
                time.sleep(3600)  # Clean every hour

                # Cleanup expired entries
                self._cleanup_last_seen_cache()

                # Save to disk
                self._save_last_seen_cache()

            except Exception as e:
                self.logger.error(f"Error in periodic last_seen cache cleanup: {e}")

    def _cleanup_timed_out_transactions(self):
        """
        Background thread that checks for timed-out pending transactions.

        TIMEOUT RULES:
        - Regular announcements: 60 seconds timeout
        - Attack transactions: 180 seconds timeout

        CONSENSUS STATUS on timeout:
        - 3+ approve votes: CONFIRMED (write normally)
        - 1-2 approve votes: INSUFFICIENT_CONSENSUS
        - 0 approve votes: SINGLE_WITNESS
        """
        import time

        # Wait for server to start
        time.sleep(10)

        while self.running:
            try:
                time.sleep(30)  # Check every 30 seconds

                current_time = datetime.now()
                timed_out_transactions = []

                # CRITICAL SECTION: Check for timeouts with lock
                with self.lock:
                    for tx_id, vote_data in list(self.pending_votes.items()):
                        # Skip if already committed
                        if tx_id in self.committed_transactions:
                            continue

                        created_at = vote_data.get("created_at")
                        is_attack = vote_data.get("is_attack", False)

                        if not created_at:
                            continue

                        # Determine timeout based on type
                        timeout_duration = self.ATTACK_TIMEOUT if is_attack else self.REGULAR_TIMEOUT
                        elapsed = (current_time - created_at).total_seconds()

                        # Check if timed out
                        if elapsed >= timeout_duration:
                            timed_out_transactions.append(tx_id)
                            self.logger.warning(
                                f"⏱️  Transaction {tx_id} timed out after {elapsed:.0f}s "
                                f"({'ATTACK' if is_attack else 'REGULAR'}, timeout={timeout_duration}s)"
                            )

                # NON-CRITICAL SECTION: Process timeouts (lock released)
                for tx_id in timed_out_transactions:
                    self._handle_timed_out_transaction(tx_id)

            except Exception as e:
                self.logger.error(f"Error in timeout cleanup: {e}")

    def _handle_timed_out_transaction(self, transaction_id):
        """
        Handle transaction that has timed out waiting for consensus.

        Decision tree:
        - 3+ approve: Write as CONFIRMED (reached consensus)
        - 1-2 approve: Write as INSUFFICIENT_CONSENSUS
        - 0 approve: Write as SINGLE_WITNESS

        Args:
            transaction_id: ID of timed-out transaction
        """
        try:
            # Get vote data with lock
            with self.lock:
                if transaction_id not in self.pending_votes:
                    return  # Already processed

                if transaction_id in self.committed_transactions:
                    return  # Already committed

                vote_data = self.pending_votes.get(transaction_id)
                if not vote_data:
                    return

                # Count approve votes
                approve_votes = [v for v in vote_data["votes"] if v["vote"] == "approve"]
                approve_count = len(approve_votes)

                # Determine consensus status
                if approve_count >= self.consensus_threshold:
                    consensus_status = "CONFIRMED"
                elif approve_count >= 1:
                    consensus_status = "INSUFFICIENT_CONSENSUS"
                else:
                    consensus_status = "SINGLE_WITNESS"

                # Mark as committed to prevent re-processing
                self.committed_transactions.add(transaction_id)

            # Commit with appropriate status
            self._commit_unconfirmed_transaction(transaction_id, consensus_status, approve_count)

        except Exception as e:
            self.logger.error(f"Error handling timed-out transaction {transaction_id}: {e}")

    def _commit_unconfirmed_transaction(self, transaction_id, consensus_status, approve_count):
        """
        Commit transaction with unconfirmed/partial consensus status.

        Args:
            transaction_id: Transaction ID
            consensus_status: CONFIRMED, INSUFFICIENT_CONSENSUS, or SINGLE_WITNESS
            approve_count: Number of approve votes received
        """
        try:
            if transaction_id not in self.pending_votes:
                return

            vote_data = self.pending_votes[transaction_id]
            transaction = vote_data["transaction"]

            # Add consensus metadata
            transaction["signatures"] = vote_data["votes"]
            transaction["consensus_status"] = consensus_status
            transaction["consensus_reached"] = (consensus_status == "CONFIRMED")
            transaction["signature_count"] = len(vote_data["votes"])
            transaction["approve_count"] = approve_count
            transaction["timeout_commit"] = True

            # Write to blockchain
            success = self.blockchain.add_transaction_to_blockchain(transaction)

            if success:
                self.logger.info(
                    f"⛓️  Transaction {transaction_id} committed with status={consensus_status} "
                    f"({approve_count} approve votes, timeout)"
                )

                # Update last_seen cache for sampling (if regular announcement and has some approval)
                if not transaction.get('is_attack', False) and approve_count > 0:
                    self._update_last_seen_cache(
                        transaction.get('ip_prefix'),
                        transaction.get('sender_asn')
                    )

                # Award reduced BGPCOIN rewards for partial consensus
                if approve_count > 0 and consensus_status in ["CONFIRMED", "INSUFFICIENT_CONSENSUS"]:
                    self._award_bgpcoin_rewards(transaction_id, vote_data)

                # Remove from pending votes
                del self.pending_votes[transaction_id]
            else:
                self.logger.error(f"Failed to write timed-out transaction {transaction_id} to blockchain")

        except Exception as e:
            self.logger.error(f"Error committing unconfirmed transaction {transaction_id}: {e}")

    def add_bgp_observation(self, ip_prefix, sender_asn, timestamp, trust_score, is_attack=False):
        """
        Add BGP observation to knowledge base.
        Called when this node observes a BGP announcement.

        SAMPLING LOGIC:
        - Attacks: Always record (bypass sampling)
        - Regular: Only if not seen in last 1 hour (1-hour sampling window)

        Args:
            ip_prefix: IP prefix announced (e.g., "203.0.113.0/24")
            sender_asn: AS number that made the announcement
            timestamp: Timestamp of the announcement
            trust_score: Trust score for this announcement
            is_attack: Whether this is an attack (bypasses sampling)

        Returns:
            bool: True if observation added, False if skipped (sampling)
        """
        # SAMPLING: For regular announcements, check if recorded in last 1 hour
        if not is_attack:
            if self._check_recent_announcement_in_cache(ip_prefix, sender_asn):
                # Already recorded within 1 hour, skip
                return False

        with self.lock:
            observation = {
                "ip_prefix": ip_prefix,
                "sender_asn": sender_asn,
                "timestamp": timestamp,
                "trust_score": trust_score,
                "observed_at": datetime.now().isoformat(),
                "is_attack": is_attack
            }
            self.knowledge_base.append(observation)
            self.logger.info(f"📚 Added to knowledge base: {ip_prefix} from AS{sender_asn} "
                           f"({'ATTACK' if is_attack else 'REGULAR'})")

            # Record in neighbor cache: "I (RPKI node) observed this non-RPKI AS"
            # This builds the mapping for optimized voting
            self.neighbor_cache.record_observation(
                non_rpki_as=sender_asn,
                observed_by_rpki_as=self.as_number
            )

            return True  # Observation added

    def _cleanup_old_observations(self):
        """
        Background thread that removes old observations outside time window.
        Keeps knowledge base size manageable.

        Window: 8 minutes (480 seconds) - allows time for:
        - BGP propagation delays (2-3 minutes)
        - Fork resolution and transaction rescue (2-3 minutes)
        - Vote collection and consensus (1-2 minutes)
        """
        import time
        from dateutil import parser

        while self.running:
            try:
                time.sleep(self.cleanup_interval)

                with self.lock:
                    current_time = datetime.now()
                    initial_count = len(self.knowledge_base)

                    # Remove observations older than 8-minute window
                    self.knowledge_base = [
                        obs for obs in self.knowledge_base
                        if (current_time - parser.parse(obs["observed_at"])).total_seconds()
                           <= self.knowledge_window_seconds
                    ]

                    removed = initial_count - len(self.knowledge_base)
                    if removed > 0:
                        self.logger.debug(f"🧹 Cleaned {removed} old observations from knowledge base "
                                        f"(window: {self.knowledge_window_seconds}s)")

            except Exception as e:
                self.logger.error(f"Error cleaning knowledge base: {e}")

    def _check_knowledge_base(self, transaction):
        """
        Check if transaction matches any observation in knowledge base.

        Args:
            transaction: Transaction to validate

        Returns:
            True if matching observation found, False otherwise
        """
        try:
            from dateutil import parser

            ip_prefix = transaction.get("ip_prefix")
            sender_asn = transaction.get("sender_asn")
            tx_timestamp = transaction.get("timestamp")

            if not all([ip_prefix, sender_asn, tx_timestamp]):
                self.logger.warning("Transaction missing required fields for validation")
                return False

            # Parse transaction timestamp (outside lock - no shared data access)
            tx_time = parser.parse(tx_timestamp)

            # CRITICAL SECTION: Copy knowledge base snapshot with lock
            with self.lock:
                knowledge_snapshot = list(self.knowledge_base)  # Shallow copy

            # NON-CRITICAL SECTION: Search snapshot (lock released)
            # This allows other threads to modify knowledge_base concurrently
            for obs in knowledge_snapshot:
                # Check if IP prefix and sender ASN match
                if obs["ip_prefix"] == ip_prefix and obs["sender_asn"] == sender_asn:
                    # Check if timestamp is within window
                    obs_time = parser.parse(obs["timestamp"])
                    time_diff = abs((tx_time - obs_time).total_seconds())

                    if time_diff <= self.knowledge_window_seconds:
                        self.logger.info(f"✅ Knowledge match: {ip_prefix} from AS{sender_asn} "
                                       f"(time diff: {time_diff:.0f}s)")
                        return True

            self.logger.warning(f"❌ No knowledge match: {ip_prefix} from AS{sender_asn} at {tx_timestamp}")
            return False

        except Exception as e:
            self.logger.error(f"Error checking knowledge base: {e}")
            return False

    def _validate_transaction(self, transaction):
        """
        Validate incoming transaction based on knowledge base.
        Node votes 'approve' if it also observed this BGP announcement.
        Node votes 'reject' if it has no record of seeing this announcement.
        """
        try:
            # Check if transaction matches our knowledge base
            if self._check_knowledge_base(transaction):
                self.logger.info(f"✅ APPROVE: Transaction matches my observations")
                return "approve"
            else:
                self.logger.warning(f"❌ REJECT: Transaction not in my knowledge base")
                return "reject"

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return "reject"  # Reject on errors for safety
    
    def _commit_to_blockchain(self, transaction_id):
        """Commit approved transaction with signatures to blockchain"""
        try:
            self.logger.info(f"🔍 DEBUG: _commit_to_blockchain called for {transaction_id}")

            if transaction_id not in self.pending_votes:
                self.logger.error(f"Transaction {transaction_id} not found in pending votes")
                return

            vote_data = self.pending_votes[transaction_id]
            transaction = vote_data["transaction"]

            # Add collected signatures to transaction
            transaction["signatures"] = vote_data["votes"]
            transaction["consensus_reached"] = True
            transaction["signature_count"] = len(vote_data["votes"])

            self.logger.info(f"🔍 DEBUG: About to call add_transaction_to_blockchain for {transaction_id}")

            # Write to blockchain using BlockchainInterface
            # This writes to: blockchain_data/chain/blockchain.json
            success = self.blockchain.add_transaction_to_blockchain(transaction)

            self.logger.info(f"🔍 DEBUG: add_transaction_to_blockchain returned: {success}")

            if success:
                self.logger.info(f"⛓️  Transaction {transaction_id} committed to blockchain with {len(vote_data['votes'])} signatures")

                # Update last_seen cache for sampling (if regular announcement)
                if not transaction.get('is_attack', False):
                    self._update_last_seen_cache(
                        transaction.get('ip_prefix'),
                        transaction.get('sender_asn')
                    )

                # Award BGPCOIN rewards for block commit
                self._award_bgpcoin_rewards(transaction_id, vote_data)

                # Trigger attack detection for this transaction
                self._trigger_attack_detection(transaction, transaction_id)

                # Remove from pending votes
                del self.pending_votes[transaction_id]
            else:
                self.logger.error(f"Failed to write transaction {transaction_id} to blockchain")

        except Exception as e:
            self.logger.error(f"Error committing transaction to blockchain: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _award_bgpcoin_rewards(self, transaction_id: str, vote_data: dict):
        """
        Award BGPCOIN tokens for successful block commit.

        IMMEDIATE REWARDS (instant):
        - Block committer gets base reward
        - First-to-commit bonus
        - Voters get smaller rewards

        Args:
            transaction_id: ID of the committed transaction
            vote_data: Vote data containing voters
        """
        try:
            # Check if this node was first to commit (bonus reward)
            is_first = transaction_id not in self.first_commit_tracker
            if is_first:
                self.first_commit_tracker[transaction_id] = self.as_number

            # Get list of voters who approved
            voter_as_list = [
                vote["from_as"]
                for vote in vote_data["votes"]
                if vote["vote"] == "approve"
            ]

            # Award rewards using BGPCOIN ledger
            result = self.bgpcoin_ledger.award_block_commit_reward(
                committer_as=self.as_number,
                voter_as_list=voter_as_list,
                is_first=is_first
            )

            if result.get("success"):
                self.logger.info(f"💰 BGPCOIN rewards distributed:")
                self.logger.info(f"   Committer (AS{self.as_number}): {result['committer_reward']} BGPCOIN")
                for voter_as, reward in result.get("voter_rewards", {}).items():
                    self.logger.info(f"   Voter (AS{voter_as}): {reward} BGPCOIN")

                # Show updated balance
                my_balance = self.bgpcoin_ledger.get_balance(self.as_number)
                self.logger.info(f"   💼 My balance: {my_balance} BGPCOIN")
            else:
                self.logger.warning(f"⚠️ BGPCOIN reward failed: {result.get('reason', 'unknown')}")

        except Exception as e:
            self.logger.error(f"Error awarding BGPCOIN rewards: {e}")

    def _trigger_attack_detection(self, transaction: dict, transaction_id: str):
        """
        Trigger attack detection analysis for committed transaction.

        This runs AFTER the transaction is written to blockchain.
        If attack detected, nodes vote on whether it's truly an attack.

        Args:
            transaction: Committed transaction
            transaction_id: Transaction ID
        """
        try:
            if not self.attack_consensus:
                return  # Attack consensus not initialized

            # Extract BGP announcement details
            announcement = {
                "sender_asn": transaction.get("sender_asn"),
                "ip_prefix": transaction.get("ip_prefix"),
                "as_path": transaction.get("as_path", [transaction.get("sender_asn")]),
                "timestamp": transaction.get("timestamp")
            }

            # Check if all required fields present
            if not announcement["sender_asn"] or not announcement["ip_prefix"]:
                self.logger.warning("Transaction missing required fields for attack detection")
                return

            self.logger.info(f"🔍 Analyzing transaction {transaction_id} for potential attacks...")

            # Trigger attack detection and consensus voting
            self.attack_consensus.analyze_and_propose_attack(announcement, transaction_id)

        except Exception as e:
            self.logger.error(f"Error triggering attack detection: {e}")

    def _load_knowledge_base(self):
        """
        Load knowledge base from disk on startup.
        Provides crash recovery and persistence across restarts.
        """
        try:
            if self.knowledge_base_file.exists():
                with open(self.knowledge_base_file, 'r') as f:
                    data = json.load(f)

                # Load observations and filter out expired ones
                from dateutil import parser
                current_time = datetime.now()

                loaded = data.get('observations', [])
                valid_observations = []

                for obs in loaded:
                    try:
                        observed_at = parser.parse(obs['observed_at'])
                        age_seconds = (current_time - observed_at).total_seconds()

                        if age_seconds <= self.knowledge_window_seconds:
                            valid_observations.append(obs)
                    except Exception as e:
                        self.logger.warning(f"Skipping invalid observation: {e}")

                self.knowledge_base = valid_observations
                self.logger.info(f"📂 Loaded {len(valid_observations)} observations from knowledge base "
                               f"({len(loaded) - len(valid_observations)} expired)")
            else:
                self.logger.info("📂 No existing knowledge base found, starting fresh")

        except json.JSONDecodeError as e:
            # Handle corrupted file
            self.logger.error(f"Knowledge base file corrupted: {e}")
            if self.knowledge_base_file.exists():
                # Rename corrupted file for forensics
                corrupted_path = self.knowledge_base_file.with_suffix('.json.corrupted')
                self.knowledge_base_file.rename(corrupted_path)
                self.logger.warning(f"Corrupted file moved to: {corrupted_path}")
            self.knowledge_base = []

        except Exception as e:
            self.logger.error(f"Error loading knowledge base: {e}")
            self.knowledge_base = []

    def _save_knowledge_base(self):
        """
        Save knowledge base to disk atomically.
        Uses temp file + rename to prevent corruption.
        """
        try:
            # CRITICAL SECTION: Copy knowledge base with lock (fast)
            with self.lock:
                knowledge_snapshot = list(self.knowledge_base)  # Shallow copy

            # NON-CRITICAL SECTION: File I/O (lock released, can take 100ms+)
            data = {
                "version": "1.0",
                "as_number": self.as_number,
                "last_updated": datetime.now().isoformat(),
                "window_seconds": self.knowledge_window_seconds,
                "observation_count": len(knowledge_snapshot),
                "observations": knowledge_snapshot
            }

            # Atomic write: write to temp file then rename
            temp_file = self.knowledge_base_file.with_suffix('.tmp')

            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)

            # Atomic rename (fast operation, no lock needed)
            temp_file.replace(self.knowledge_base_file)

            self.logger.debug(f"💾 Saved {len(knowledge_snapshot)} observations to knowledge base")

        except Exception as e:
            self.logger.error(f"Error saving knowledge base: {e}")

    def _periodic_save_knowledge_base(self):
        """
        Background thread that periodically saves knowledge base to disk.
        Provides crash recovery with minimal data loss (≤60 seconds).
        """
        import time

        # Wait for server to start before saving
        time.sleep(5)

        while self.running:
            try:
                time.sleep(60)  # Save every 60 seconds
                self._save_knowledge_base()

            except Exception as e:
                self.logger.error(f"Error in periodic save: {e}")

    def get_pending_transactions(self):
        """
        Get list of pending transactions (for compatibility with consensus monitoring).

        Returns:
            List of transactions waiting for consensus
        """
        # CRITICAL SECTION: Copy data with lock (fast)
        with self.lock:
            pending_snapshot = dict(self.pending_votes)  # Shallow copy
            committed_snapshot = set(self.committed_transactions)  # Copy set

        # NON-CRITICAL SECTION: Process snapshot (lock released)
        pending = []
        for tx_id, vote_data in pending_snapshot.items():
            if tx_id not in committed_snapshot:
                transaction = vote_data.get("transaction", {})
                if transaction:
                    pending.append(transaction)
        return pending

    def get_transaction_by_id(self, transaction_id):
        """
        Get transaction by ID (for compatibility with consensus monitoring).

        Args:
            transaction_id: Transaction ID to retrieve

        Returns:
            Transaction dict if found, None otherwise
        """
        with self.lock:
            vote_data = self.pending_votes.get(transaction_id)
            if vote_data:
                return vote_data.get("transaction")
            return None

    def mark_transaction_processed(self, transaction_id):
        """
        Mark transaction as processed (for compatibility with consensus monitoring).

        Args:
            transaction_id: Transaction ID to mark as processed
        """
        with self.lock:
            if transaction_id in self.pending_votes:
                # Add to committed set
                self.committed_transactions.add(transaction_id)
                self.logger.debug(f"Marked transaction {transaction_id} as processed")

    def stop(self):
        """Stop P2P communication and save knowledge base"""
        self.running = False

        # Save knowledge base before shutdown
        self.logger.info("💾 Saving knowledge base before shutdown...")
        self._save_knowledge_base()

        if self.server_socket:
            self.server_socket.close()
