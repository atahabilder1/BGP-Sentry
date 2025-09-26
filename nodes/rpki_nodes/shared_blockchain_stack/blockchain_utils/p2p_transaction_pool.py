#!/usr/bin/env python3
import json
import logging
import socket
import threading
from pathlib import Path
from datetime import datetime

class P2PTransactionPool:
    """
    Peer-to-peer transaction pool with direct node-to-node communication.
    Each node maintains its own pool and communicates directly with peers.
    """
    
    def __init__(self, as_number, base_port=8000):
        self.as_number = as_number
        self.my_port = base_port + as_number
        
        # All RPKI nodes in the network (hardcoded peer discovery)
        self.peer_nodes = {
            1: ("localhost", 8001),
            3: ("localhost", 8003), 
            5: ("localhost", 8005),
            7: ("localhost", 8007),
            9: ("localhost", 8009),
            11: ("localhost", 8011),
            13: ("localhost", 8013),
            15: ("localhost", 8015),
            17: ("localhost", 8017)
        }
        
        # Remove self from peer list
        if self.as_number in self.peer_nodes:
            del self.peer_nodes[self.as_number]
        
        # Local transaction storage
        self.local_dir = Path("blockchain_data/transaction_pool")
        self.local_dir.mkdir(exist_ok=True)
        self.pending_file = self.local_dir / "pending.json"
        
        # P2P communication
        self.server_socket = None
        self.running = False
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"P2P-AS{self.as_number}")
        
        # Transaction voting tracking
        self.pending_votes = {}  # transaction_id -> {votes: [], needed: 3}
    
    def start_p2p_server(self):
        """Start P2P server to listen for incoming messages"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("localhost", self.my_port))
            self.server_socket.listen(5)
            self.running = True
            
            self.logger.info(f"P2P server started on port {self.my_port}")
            
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
        """Handle incoming vote response"""
        tx_id = message["transaction_id"]
        vote = message["vote"]
        from_as = message["from_as"]
        
        if tx_id not in self.pending_votes:
            self.pending_votes[tx_id] = {"votes": [], "needed": 3}
        
        # Record vote
        self.pending_votes[tx_id]["votes"].append({
            "from_as": from_as,
            "vote": vote
        })
        
        self.logger.info(f"Received {vote} vote for {tx_id} from AS{from_as}")
        
        # Check if consensus reached
        approve_votes = len([v for v in self.pending_votes[tx_id]["votes"] if v["vote"] == "approve"])
        
        if approve_votes >= 3:
            self.logger.info(f"Consensus reached for {tx_id} - writing to blockchain")
            self._commit_to_blockchain(tx_id)
    
    def broadcast_transaction(self, transaction):
        """Broadcast transaction to all peer nodes for voting"""
        tx_id = transaction["transaction_id"]
        self.pending_votes[tx_id] = {"votes": [], "needed": 3}
        
        # Send to all peers
        for peer_as, (host, port) in self.peer_nodes.items():
            self._send_vote_request_to_node(peer_as, host, port, transaction)
        
        self.logger.info(f"Broadcast transaction {tx_id} to {len(self.peer_nodes)} peers")
    
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
    
    def _validate_transaction(self, transaction):
        """Validate incoming transaction (simplified)"""
        # In real implementation: check signatures, validate BGP data, etc.
        return "approve"  # For now, approve all transactions
    
    def _commit_to_blockchain(self, transaction_id):
        """Commit approved transaction to local blockchain"""
        # This would integrate with your blockchain_interface.py
        self.logger.info(f"Committed transaction {transaction_id} to blockchain")
    
    def stop(self):
        """Stop P2P communication"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
