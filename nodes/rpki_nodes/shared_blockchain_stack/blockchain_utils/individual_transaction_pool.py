#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from datetime import datetime
import threading

class IndividualTransactionPool:
    """
    Individual transaction pool for each blockchain node.
    Manages local pending transactions and P2P communication.
    """
    
    def __init__(self, as_number, pool_dir="blockchain_data/transaction_pool"):
        self.as_number = as_number
        self.pool_dir = Path(pool_dir)
        self.pool_dir.mkdir(exist_ok=True)
        
        # Local files
        self.pending_file = self.pool_dir / "pending_transactions.json"
        self.votes_file = self.pool_dir / "incoming_votes.json" 
        self.requests_file = self.pool_dir / "outgoing_requests.json"
        
        # P2P communication directory (shared across all nodes)
        self.p2p_dir = Path("../../shared_communication")
        self.p2p_dir.mkdir(exist_ok=True)
        
        # Other AS numbers for P2P communication
        self.other_nodes = [1, 3, 5, 7, 9, 11, 13, 15, 17]
        self.other_nodes.remove(self.as_number)
        
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"TxPool-AS{self.as_number}")
        
    def add_local_transaction(self, transaction):
        """Add a transaction to this node's pending pool"""
        with self.lock:
            # Load existing transactions
            if self.pending_file.exists():
                with open(self.pending_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"transactions": []}
            
            # Add transaction with metadata
            transaction_entry = {
                "transaction": transaction,
                "created_at": datetime.now().isoformat(),
                "votes_needed": 3,
                "votes_received": [],
                "status": "pending"
            }
            
            data["transactions"].append(transaction_entry)
            
            # Save back
            with open(self.pending_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Added local transaction: {transaction.get('transaction_id')}")
            
            # Broadcast to other nodes
            self._broadcast_transaction(transaction)
    
    def _broadcast_transaction(self, transaction):
        """Broadcast transaction to other nodes for voting"""
        for target_as in self.other_nodes:
            # Create communication file
            comm_file = self.p2p_dir / f"as{self.as_number:02d}_to_as{target_as:02d}.json"
            
            # Load existing communications
            if comm_file.exists():
                with open(comm_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {"messages": []}
            
            # Add vote request
            vote_request = {
                "type": "vote_request",
                "from_as": self.as_number,
                "to_as": target_as,
                "transaction": transaction,
                "timestamp": datetime.now().isoformat()
            }
            
            data["messages"].append(vote_request)
            
            with open(comm_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        self.logger.info(f"Broadcast transaction {transaction.get('transaction_id')} to {len(self.other_nodes)} nodes")
    
    def check_incoming_vote_requests(self):
        """Check for incoming vote requests from other nodes"""
        vote_requests = []
        
        for sender_as in self.other_nodes:
            comm_file = self.p2p_dir / f"as{sender_as:02d}_to_as{self.as_number:02d}.json"
            
            if comm_file.exists():
                with open(comm_file, 'r') as f:
                    data = json.load(f)
                
                for message in data["messages"]:
                    if message["type"] == "vote_request":
                        vote_requests.append(message)
                
                # Clear processed messages
                data["messages"] = []
                with open(comm_file, 'w') as f:
                    json.dump(data, f, indent=2)
        
        return vote_requests
    
    def send_vote(self, target_as, transaction_id, vote, signature=None):
        """Send a vote to another node"""
        comm_file = self.p2p_dir / f"as{self.as_number:02d}_to_as{target_as:02d}.json"
        
        # Load existing communications
        if comm_file.exists():
            with open(comm_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"messages": []}
        
        # Add vote response
        vote_response = {
            "type": "vote_response",
            "from_as": self.as_number,
            "to_as": target_as,
            "transaction_id": transaction_id,
            "vote": vote,  # "approve" or "reject"
            "signature": signature,
            "timestamp": datetime.now().isoformat()
        }
        
        data["messages"].append(vote_response)
        
        with open(comm_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Sent {vote} vote for {transaction_id} to AS{target_as}")
    
    def collect_votes(self, transaction_id):
        """Collect votes for a specific transaction"""
        votes = []
        
        for sender_as in self.other_nodes:
            comm_file = self.p2p_dir / f"as{sender_as:02d}_to_as{self.as_number:02d}.json"
            
            if comm_file.exists():
                with open(comm_file, 'r') as f:
                    data = json.load(f)
                
                # Find votes for this transaction
                remaining_messages = []
                for message in data["messages"]:
                    if (message["type"] == "vote_response" and 
                        message["transaction_id"] == transaction_id):
                        votes.append({
                            "from_as": message["from_as"],
                            "vote": message["vote"],
                            "signature": message.get("signature")
                        })
                    else:
                        remaining_messages.append(message)
                
                # Keep unprocessed messages
                data["messages"] = remaining_messages
                with open(comm_file, 'w') as f:
                    json.dump(data, f, indent=2)
        
        return votes
    
    def get_pending_transactions(self):
        """Get transactions pending consensus from this node"""
        if not self.pending_file.exists():
            return []
        
        with open(self.pending_file, 'r') as f:
            data = json.load(f)
        
        return [entry["transaction"] for entry in data["transactions"] 
                if entry["status"] == "pending"]
    
    def mark_transaction_approved(self, transaction_id):
        """Mark a transaction as approved (ready for blockchain)"""
        self._update_transaction_status(transaction_id, "approved")
    
    def mark_transaction_rejected(self, transaction_id):
        """Mark a transaction as rejected"""
        self._update_transaction_status(transaction_id, "rejected")
    
    def _update_transaction_status(self, transaction_id, status):
        """Update transaction status"""
        if not self.pending_file.exists():
            return
        
        with self.lock:
            with open(self.pending_file, 'r') as f:
                data = json.load(f)
            
            for entry in data["transactions"]:
                if entry["transaction"].get("transaction_id") == transaction_id:
                    entry["status"] = status
                    entry["updated_at"] = datetime.now().isoformat()
            
            with open(self.pending_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Transaction {transaction_id} marked as {status}")
