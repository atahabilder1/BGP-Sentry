#!/usr/bin/env python3
"""
=============================================================================
Blockchain Interface Utility - File-Based Blockchain Operations
=============================================================================

File: utils_common/blockchain_interface.py
Purpose: Provides interface for reading and writing to the BGP-Sentry blockchain
         using file-based storage instead of smart contracts

What this utility does:
- Reads/writes blockchain data from shared_data/chain/blockchain.json
- Manages blockchain structure and integrity
- Provides thread-safe access to blockchain operations
- Handles block creation and transaction commits

Used by:
- ConsensusService: Commits approved transactions to blockchain
- RPKIObserverService: Reads blockchain for historical analysis
- Trust Engine: Updates trust scores based on blockchain events

Storage Files:
- blockchain.json: Main blockchain with blocks and transactions
- bgp_stream.jsonl: Stream of BGP events for analysis
- trust_log.jsonl: Trust score change log

Blockchain Structure:
- File-based JSON storage (no smart contracts)
- Simple block structure with transaction lists
- Immutable append-only design
- Cryptographic block linking

Author: BGP-Sentry Team
=============================================================================
"""

import json
import threading
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class BlockchainInterface:
    """
    Interface for BGP-Sentry file-based blockchain operations.
    
    Provides thread-safe access to blockchain data stored in JSON files,
    enabling multiple services to read and write blockchain data concurrently.
    """
    
    def __init__(self, blockchain_path="shared_data/chain", in_memory=False,
                 genesis_block=None):
        """
        Initialize blockchain interface.

        Args:
            blockchain_path: Path to blockchain data directory (ignored when in_memory=True)
            in_memory: If True, keep chain in RAM only (no disk I/O). Used for
                       per-node replicas in the simulation.
            genesis_block: Optional genesis block dict to copy from a primary chain.
                           Ensures all replicas share the same genesis hash.
        """
        self.in_memory = in_memory

        # Thread safety - use RLock for reentrant locking (nested lock acquisition)
        self.lock = threading.RLock()

        # Initialize blockchain structure
        self.blockchain_data = {
            "version": "1.0",
            "network": "BGP-Sentry",
            "genesis_timestamp": datetime.now().isoformat(),
            "blocks": [],
            "metadata": {
                "total_transactions": 0,
                "total_blocks": 0,
                "last_updated": datetime.now().isoformat()
            }
        }

        if not in_memory:
            self.blockchain_dir = Path(blockchain_path)
            self.blockchain_file = self.blockchain_dir / "blockchain.json"
            self.bgp_stream_file = self.blockchain_dir / "bgp_stream.jsonl"
            self.trust_log_file = self.blockchain_dir / "trust_log.jsonl"
            self.lock_file = self.blockchain_dir / "blockchain_lock.json"

            # State folder for fast queries (IP prefix -> ASN mappings)
            self.state_dir = self.blockchain_dir.parent / "state"
            self.ip_asn_mapping_file = self.state_dir / "ip_asn_mapping.json"

            # Create directories if they don't exist
            self.blockchain_dir.mkdir(parents=True, exist_ok=True)
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Initialize IP-ASN mapping if it doesn't exist
            if not self.ip_asn_mapping_file.exists():
                with open(self.ip_asn_mapping_file, 'w') as f:
                    json.dump({}, f, indent=2)

            # Load existing blockchain
            self._load_blockchain()
        else:
            # In-memory mode: no disk paths needed
            self.blockchain_dir = None
            self.blockchain_file = None
            self.bgp_stream_file = None
            self.trust_log_file = None
            self.lock_file = None
            self.state_dir = None
            self.ip_asn_mapping_file = None

        # Transaction dedup index: O(1) lookup for recently committed tx IDs
        self._recent_tx_ids: set = set()
        self._RECENT_TX_WINDOW = 500  # Number of recent blocks to index

        # Ensure genesis block exists
        if not self.blockchain_data["blocks"]:
            if genesis_block is not None:
                # Use the same genesis block as the primary chain
                self.blockchain_data["blocks"].append(genesis_block)
            else:
                self._create_genesis_block()

        # Build initial dedup index from existing blocks
        self._rebuild_tx_index()
    
    def _rebuild_tx_index(self):
        """Build dedup index from the last N blocks."""
        self._recent_tx_ids.clear()
        blocks = self.blockchain_data["blocks"][-self._RECENT_TX_WINDOW:]
        for block in blocks:
            for tx in block.get("transactions", []):
                tx_id = tx.get("transaction_id")
                if tx_id:
                    self._recent_tx_ids.add(tx_id)

    def _load_blockchain(self):
        """Load blockchain data from file."""
        if self.in_memory:
            return  # Nothing to load
        try:
            if self.blockchain_file.exists():
                with open(self.blockchain_file, 'r') as f:
                    loaded_data = json.load(f)

                # Validate loaded data structure
                if self._validate_blockchain_structure(loaded_data):
                    self.blockchain_data = loaded_data
                    print(f"Loaded blockchain with {len(self.blockchain_data['blocks'])} blocks")
                else:
                    print("Warning: Invalid blockchain structure, initializing new blockchain")
            else:
                print("No existing blockchain found, initializing new blockchain")

        except Exception as e:
            print(f"Error loading blockchain: {e}")
    
    def _validate_blockchain_structure(self, data: Dict) -> bool:
        """Validate blockchain data structure."""
        try:
            required_keys = ["version", "network", "blocks", "metadata"]
            for key in required_keys:
                if key not in data:
                    return False
            
            # Validate blocks structure
            if not isinstance(data["blocks"], list):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _save_blockchain(self):
        """Save blockchain data to file with atomic write."""
        # Update in-memory metadata regardless of mode
        self.blockchain_data["metadata"].update({
            "total_blocks": len(self.blockchain_data["blocks"]),
            "total_transactions": sum(
                len(block.get("transactions", []))
                for block in self.blockchain_data["blocks"]
            ),
            "last_updated": datetime.now().isoformat(),
        })

        if self.in_memory:
            return  # Skip disk I/O

        try:
            with self.lock:
                # Atomic write: write to temp file then rename
                temp_file = self.blockchain_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(self.blockchain_data, f, indent=2)

                # Atomic rename
                temp_file.replace(self.blockchain_file)

        except Exception as e:
            print(f"Error saving blockchain: {e}")
    
    def _create_genesis_block(self):
        """Create the genesis block."""
        genesis_block = {
            "block_number": 0,
            "timestamp": datetime.now().isoformat(),
            "previous_hash": "0" * 64,  # Genesis has no previous block
            "transactions": [],
            "block_hash": "",
            "merkle_root": "",
            "metadata": {
                "block_type": "genesis",
                "created_by": "BGP-Sentry Network"
            }
        }
        
        # Calculate merkle root and block hash
        genesis_block["merkle_root"] = self._calculate_merkle_root(genesis_block["transactions"])
        genesis_block["block_hash"] = self._calculate_block_hash(genesis_block)
        
        # Add to blockchain
        self.blockchain_data["blocks"].append(genesis_block)
        self._save_blockchain()
        
        print("Genesis block created")
    
    def _calculate_block_hash(self, block: Dict) -> str:
        """Calculate SHA-256 hash of block data."""
        try:
            # Create deterministic string representation (excluding hash field)
            block_copy = block.copy()
            block_copy.pop("block_hash", None)  # Remove hash field for calculation
            
            block_string = json.dumps(block_copy, sort_keys=True, separators=(',', ':'))
            
            # Calculate SHA-256 hash
            hash_obj = hashlib.sha256()
            hash_obj.update(block_string.encode('utf-8'))
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            print(f"Error calculating block hash: {e}")
            return "error_hash"
    
    def _calculate_merkle_root(self, transactions: List[Dict]) -> str:
        """Calculate Merkle root of transactions."""
        if not transactions:
            return "0" * 64
        
        try:
            # Hash each transaction
            tx_hashes = []
            for tx in transactions:
                tx_string = json.dumps(tx, sort_keys=True, separators=(',', ':'))
                tx_hash = hashlib.sha256(tx_string.encode('utf-8')).hexdigest()
                tx_hashes.append(tx_hash)
            
            # Simple Merkle root calculation (concatenate all hashes)
            combined_hashes = ''.join(tx_hashes)
            merkle_root = hashlib.sha256(combined_hashes.encode('utf-8')).hexdigest()
            
            return merkle_root
            
        except Exception as e:
            print(f"Error calculating Merkle root: {e}")
            return "error_merkle"
    
    def add_transaction_to_blockchain(self, transaction: Dict) -> bool:
        """
        Add a transaction to the blockchain by creating a new block.
        
        Args:
            transaction: Transaction data to add
            
        Returns:
            bool: True if transaction added successfully
        """
        try:
            with self.lock:
                # Blockchain-level dedup: reject if tx already on chain
                tx_id = transaction.get("transaction_id")
                if tx_id and tx_id in self._recent_tx_ids:
                    print(f"⚠️ Duplicate transaction {tx_id} rejected (already on chain)")
                    return False

                # Get previous block
                previous_block = self.blockchain_data["blocks"][-1] if self.blockchain_data["blocks"] else None
                previous_hash = previous_block["block_hash"] if previous_block else "0" * 64

                # Create new block
                new_block = {
                    "block_number": len(self.blockchain_data["blocks"]),
                    "timestamp": datetime.now().isoformat(),
                    "previous_hash": previous_hash,
                    "transactions": [transaction],
                    "block_hash": "",
                    "merkle_root": "",
                    "metadata": {
                        "block_type": "transaction",
                        "transaction_count": 1
                    }
                }
                
                # Calculate Merkle root and block hash
                new_block["merkle_root"] = self._calculate_merkle_root(new_block["transactions"])
                new_block["block_hash"] = self._calculate_block_hash(new_block)
                
                # Add block to blockchain
                self.blockchain_data["blocks"].append(new_block)

                # Update dedup index
                if tx_id:
                    self._recent_tx_ids.add(tx_id)
                # Trim index if it grows beyond 2x window (lazy cleanup)
                if len(self._recent_tx_ids) > self._RECENT_TX_WINDOW * 2:
                    self._rebuild_tx_index()

                # Save blockchain
                self._save_blockchain()

                # Log to BGP stream
                self._log_to_bgp_stream(transaction)

                # Update state folder with IP prefix → ASN mapping
                self._update_state_mapping(transaction)

                print(f"✅ Transaction added to blockchain: Block {new_block['block_number']}")
                return True
                
        except Exception as e:
            print(f"Error adding transaction to blockchain: {e}")
            return False
    
    def add_multiple_transactions(self, transactions: List[Dict]) -> bool:
        """
        Add multiple transactions to a single block.
        
        Args:
            transactions: List of transactions to add
            
        Returns:
            bool: True if all transactions added successfully
        """
        try:
            if not transactions:
                return True
            
            with self.lock:
                # Get previous block
                previous_block = self.blockchain_data["blocks"][-1] if self.blockchain_data["blocks"] else None
                previous_hash = previous_block["block_hash"] if previous_block else "0" * 64
                
                # Create new block with multiple transactions
                new_block = {
                    "block_number": len(self.blockchain_data["blocks"]),
                    "timestamp": datetime.now().isoformat(),
                    "previous_hash": previous_hash,
                    "transactions": transactions,
                    "block_hash": "",
                    "merkle_root": "",
                    "metadata": {
                        "block_type": "batch",
                        "transaction_count": len(transactions)
                    }
                }
                
                # Calculate Merkle root and block hash
                new_block["merkle_root"] = self._calculate_merkle_root(new_block["transactions"])
                new_block["block_hash"] = self._calculate_block_hash(new_block)
                
                # Add block to blockchain
                self.blockchain_data["blocks"].append(new_block)
                
                # Save blockchain
                self._save_blockchain()
                
                # Log all transactions to BGP stream
                for transaction in transactions:
                    self._log_to_bgp_stream(transaction)
                
                print(f"✅ {len(transactions)} transactions added to blockchain: Block {new_block['block_number']}")
                return True
                
        except Exception as e:
            print(f"Error adding multiple transactions to blockchain: {e}")
            return False
    
    def _log_to_bgp_stream(self, transaction: Dict):
        """Log transaction to BGP stream file for analysis."""
        if self.in_memory:
            return
        try:
            # Extract BGP data from transaction
            bgp_data = transaction.get('bgp_data', {})

            stream_entry = {
                "timestamp": datetime.now().isoformat(),
                "transaction_id": transaction.get('transaction_id'),
                "observer_as": transaction.get('observer_as'),
                "sender_asn": bgp_data.get('sender_asn'),
                "ip_prefix": bgp_data.get('ip_prefix'),
                "announcement_type": bgp_data.get('announcement_type', 'unknown'),
                "validation_result": bgp_data.get('validation_result', {})
            }

            # Append to BGP stream file (JSONL format)
            with open(self.bgp_stream_file, 'a') as f:
                f.write(json.dumps(stream_entry) + '\n')

        except Exception as e:
            print(f"Error logging to BGP stream: {e}")

    def _update_state_mapping(self, transaction: Dict):
        """
        Update state folder with IP prefix -> ASN mapping for fast queries.

        Args:
            transaction: Transaction containing BGP announcement data
        """
        if self.in_memory:
            return
        try:
            # Extract IP prefix and sender ASN from transaction
            ip_prefix = transaction.get('ip_prefix')
            sender_asn = transaction.get('sender_asn')

            # Also check bgp_data for backward compatibility
            if not ip_prefix or not sender_asn:
                bgp_data = transaction.get('bgp_data', {})
                ip_prefix = bgp_data.get('ip_prefix')
                sender_asn = bgp_data.get('sender_asn')

            if not ip_prefix or not sender_asn:
                # No IP prefix or ASN data in this transaction
                return

            # Load current IP-ASN mapping
            mapping = {}
            if self.ip_asn_mapping_file.exists():
                try:
                    with open(self.ip_asn_mapping_file, 'r') as f:
                        mapping = json.load(f)
                except json.JSONDecodeError:
                    # File is corrupted, start fresh
                    mapping = {}

            # Update mapping with new IP prefix → ASN
            mapping[str(ip_prefix)] = int(sender_asn)

            # Atomic write to state file
            temp_file = self.ip_asn_mapping_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(mapping, f, indent=2, sort_keys=True)

            # Atomic rename
            temp_file.replace(self.ip_asn_mapping_file)

            print(f"📍 Updated state: {ip_prefix} → AS{sender_asn}")

        except Exception as e:
            print(f"Error updating state mapping: {e}")

    def query_ip_prefix(self, ip_prefix: str) -> Optional[int]:
        """
        Fast query for IP prefix → ASN mapping from state folder.

        Args:
            ip_prefix: IP prefix to query (e.g., "203.0.113.0/24")

        Returns:
            ASN number if found, None otherwise
        """
        try:
            if not self.ip_asn_mapping_file.exists():
                return None

            with open(self.ip_asn_mapping_file, 'r') as f:
                mapping = json.load(f)

            return mapping.get(str(ip_prefix))

        except Exception as e:
            print(f"Error querying IP prefix: {e}")
            return None

    def get_all_ip_mappings(self) -> Dict[str, int]:
        """
        Get all IP prefix → ASN mappings from state folder.

        Returns:
            Dict of IP prefix → ASN mappings
        """
        try:
            if not self.ip_asn_mapping_file.exists():
                return {}

            with open(self.ip_asn_mapping_file, 'r') as f:
                return json.load(f)

        except Exception as e:
            print(f"Error getting IP mappings: {e}")
            return {}

    def get_last_block(self) -> Optional[Dict]:
        """
        Get the last block in the chain.

        Returns:
            Last block dict, or None if chain is empty.
        """
        with self.lock:
            if self.blockchain_data["blocks"]:
                return self.blockchain_data["blocks"][-1]
            return None

    def append_replicated_block(self, block: Dict) -> bool:
        """
        Append a replicated block received from a peer node.

        Verifies the block hash and hash-chain linkage before appending.
        Used by per-node blockchain replicas to stay in sync with the
        primary (canonical) chain.

        Args:
            block: Complete block dict (as committed by the originating node)

        Returns:
            True if block was appended successfully
        """
        try:
            with self.lock:
                # Verify block hash
                calculated_hash = self._calculate_block_hash(block)
                if calculated_hash != block.get("block_hash"):
                    print(f"WARNING: Replicated block #{block.get('block_number')} hash mismatch")
                    return False

                # Verify hash-chain linkage
                if self.blockchain_data["blocks"]:
                    last_block = self.blockchain_data["blocks"][-1]
                    if block.get("previous_hash") != last_block.get("block_hash"):
                        print(
                            f"WARNING: Replicated block #{block.get('block_number')} "
                            f"previous_hash mismatch"
                        )
                        return False

                # Append the block
                self.blockchain_data["blocks"].append(block)

                if not self.in_memory:
                    self._save_blockchain()

                return True

        except Exception as e:
            print(f"Error appending replicated block: {e}")
            return False

    def get_blockchain_info(self) -> Dict:
        """
        Get blockchain information and statistics.
        
        Returns:
            Dict with blockchain information
        """
        try:
            with self.lock:
                blocks = self.blockchain_data["blocks"]
                
                if not blocks:
                    return {"error": "No blocks in blockchain"}
                
                # Calculate statistics
                total_transactions = sum(len(block.get("transactions", [])) for block in blocks)
                latest_block = blocks[-1]
                
                return {
                    "version": self.blockchain_data["version"],
                    "network": self.blockchain_data["network"],
                    "total_blocks": len(blocks),
                    "total_transactions": total_transactions,
                    "genesis_timestamp": self.blockchain_data.get("genesis_timestamp"),
                    "latest_block": {
                        "block_number": latest_block["block_number"],
                        "timestamp": latest_block["timestamp"],
                        "hash": latest_block["block_hash"],
                        "transaction_count": len(latest_block.get("transactions", []))
                    },
                    "file_path": str(self.blockchain_file)
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_transactions_by_as(self, as_number: int) -> List[Dict]:
        """
        Get all transactions involving a specific AS.
        
        Args:
            as_number: AS number to search for
            
        Returns:
            List of transactions involving the AS
        """
        try:
            with self.lock:
                matching_transactions = []
                
                for block in self.blockchain_data["blocks"]:
                    for transaction in block.get("transactions", []):
                        # Check if AS is involved as observer or subject
                        if (transaction.get("observer_as") == as_number or
                            transaction.get("bgp_data", {}).get("sender_asn") == as_number):
                            
                            # Add block context to transaction
                            tx_with_context = transaction.copy()
                            tx_with_context["block_number"] = block["block_number"]
                            tx_with_context["block_timestamp"] = block["timestamp"]
                            matching_transactions.append(tx_with_context)
                
                return matching_transactions
                
        except Exception as e:
            print(f"Error getting transactions by AS: {e}")
            return []
    
    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """
        Get the most recent transactions.
        
        Args:
            limit: Maximum number of transactions to return
            
        Returns:
            List of recent transactions
        """
        try:
            with self.lock:
                recent_transactions = []
                
                # Start from the latest block and work backwards
                for block in reversed(self.blockchain_data["blocks"]):
                    for transaction in reversed(block.get("transactions", [])):
                        if len(recent_transactions) >= limit:
                            break
                        
                        # Add block context to transaction
                        tx_with_context = transaction.copy()
                        tx_with_context["block_number"] = block["block_number"]
                        tx_with_context["block_timestamp"] = block["timestamp"]
                        recent_transactions.append(tx_with_context)
                    
                    if len(recent_transactions) >= limit:
                        break
                
                return recent_transactions
                
        except Exception as e:
            print(f"Error getting recent transactions: {e}")
            return []
    
    def verify_blockchain_integrity(self) -> Dict:
        """
        Verify the integrity of the blockchain.
        
        Returns:
            Dict with verification results
        """
        try:
            with self.lock:
                blocks = self.blockchain_data["blocks"]
                
                if not blocks:
                    return {"valid": True, "message": "Empty blockchain"}
                
                errors = []
                
                # Verify each block
                for i, block in enumerate(blocks):
                    # Verify block hash
                    calculated_hash = self._calculate_block_hash(block)
                    if calculated_hash != block.get("block_hash"):
                        errors.append(f"Block {i}: Hash mismatch")
                    
                    # Verify previous hash linkage (except genesis)
                    if i > 0:
                        expected_prev_hash = blocks[i-1]["block_hash"]
                        if block.get("previous_hash") != expected_prev_hash:
                            errors.append(f"Block {i}: Previous hash mismatch")
                    
                    # Verify Merkle root
                    calculated_merkle = self._calculate_merkle_root(block.get("transactions", []))
                    if calculated_merkle != block.get("merkle_root"):
                        errors.append(f"Block {i}: Merkle root mismatch")
                
                return {
                    "valid": len(errors) == 0,
                    "total_blocks": len(blocks),
                    "errors": errors,
                    "message": "Blockchain valid" if not errors else f"{len(errors)} integrity errors found"
                }
                
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def log_trust_change(self, as_number: int, old_score: float, new_score: float, reason: str):
        """
        Log trust score changes to trust log file.
        
        Args:
            as_number: AS number whose trust changed
            old_score: Previous trust score
            new_score: New trust score
            reason: Reason for the change
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "as_number": as_number,
                "old_score": old_score,
                "new_score": new_score,
                "delta": new_score - old_score,
                "reason": reason
            }
            
            # Append to trust log file (JSONL format)
            with open(self.trust_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            print(f"Error logging trust change: {e}")
    
    def get_bgp_stream_analysis(self, hours: int = 24) -> Dict:
        """
        Analyze BGP stream data for the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dict with BGP stream analysis
        """
        try:
            if not self.bgp_stream_file.exists():
                return {"error": "BGP stream file not found"}
            
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            stats = {
                "total_events": 0,
                "announcement_types": {},
                "observer_counts": {},
                "sender_counts": {},
                "violations": 0
            }
            
            with open(self.bgp_stream_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry["timestamp"])
                        
                        if entry_time > cutoff_time:
                            stats["total_events"] += 1
                            
                            # Count announcement types
                            ann_type = entry.get("announcement_type", "unknown")
                            stats["announcement_types"][ann_type] = stats["announcement_types"].get(ann_type, 0) + 1
                            
                            # Count observers
                            observer = entry.get("observer_as")
                            if observer:
                                stats["observer_counts"][str(observer)] = stats["observer_counts"].get(str(observer), 0) + 1
                            
                            # Count senders
                            sender = entry.get("sender_asn")
                            if sender:
                                stats["sender_counts"][str(sender)] = stats["sender_counts"].get(str(sender), 0) + 1
                            
                            # Count violations
                            validation = entry.get("validation_result", {})
                            if not validation.get("rpki_valid") or not validation.get("irr_valid"):
                                stats["violations"] += 1
                                
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}
    
    def export_blockchain_data(self, output_path: str, format: str = "json") -> bool:
        """
        Export blockchain data to a file.
        
        Args:
            output_path: Path to output file
            format: Export format ("json" or "csv")
            
        Returns:
            bool: True if export successful
        """
        try:
            output_file = Path(output_path)
            
            if format.lower() == "json":
                with open(output_file, 'w') as f:
                    json.dump(self.blockchain_data, f, indent=2)
                    
            elif format.lower() == "csv":
                import csv
                
                # Extract transactions for CSV export
                transactions = []
                for block in self.blockchain_data["blocks"]:
                    for tx in block.get("transactions", []):
                        tx_row = {
                            "block_number": block["block_number"],
                            "block_timestamp": block["timestamp"],
                            "transaction_id": tx.get("transaction_id"),
                            "observer_as": tx.get("observer_as"),
                            "sender_asn": tx.get("bgp_data", {}).get("sender_asn"),
                            "ip_prefix": tx.get("bgp_data", {}).get("ip_prefix"),
                            "announcement_type": tx.get("bgp_data", {}).get("announcement_type")
                        }
                        transactions.append(tx_row)
                
                with open(output_file, 'w', newline='') as f:
                    if transactions:
                        writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
                        writer.writeheader()
                        writer.writerows(transactions)
            else:
                print(f"Unsupported export format: {format}")
                return False
            
            print(f"Blockchain data exported to {output_file}")
            return True
            
        except Exception as e:
            print(f"Error exporting blockchain data: {e}")
            return False

# Convenience functions for backward compatibility
def add_transaction(transaction: Dict) -> bool:
    """Add transaction to blockchain."""
    interface = BlockchainInterface()
    return interface.add_transaction_to_blockchain(transaction)

def get_blockchain_info() -> Dict:
    """Get blockchain information."""
    interface = BlockchainInterface()
    return interface.get_blockchain_info()

# Example usage and testing
if __name__ == "__main__":
    # Test the blockchain interface
    interface = BlockchainInterface()
    
    print("🧪 Testing Blockchain Interface")
    
    # Test blockchain info
    info = interface.get_blockchain_info()
    print(f"Blockchain info: {info}")
    
    # Test adding a transaction
    test_transaction = {
        'transaction_id': f'test_tx_{int(time.time())}',
        'observer_as': 5,
        'timestamp': datetime.now().isoformat(),
        'bgp_data': {
            'sender_asn': 12,
            'ip_prefix': '203.0.113.0/24',
            'announcement_type': 'normal',
            'validation_result': {'rpki_valid': True, 'irr_valid': True}
        },
        'signature': 'test_signature_data'
    }
    
    success = interface.add_transaction_to_blockchain(test_transaction)
    print(f"Add transaction: {'✅' if success else '❌'}")
    
    # Test recent transactions
    recent = interface.get_recent_transactions(5)
    print(f"Recent transactions: {len(recent)}")
    
    # Test blockchain integrity
    integrity = interface.verify_blockchain_integrity()
    print(f"Blockchain integrity: {'✅' if integrity['valid'] else '❌'} - {integrity['message']}")
    
    # Test BGP stream analysis
    analysis = interface.get_bgp_stream_analysis(24)
    print(f"BGP analysis: {analysis}")
    
    print("Blockchain interface test completed")