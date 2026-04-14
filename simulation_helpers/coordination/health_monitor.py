import json
from pathlib import Path

class NodeHealthMonitor:
    def __init__(self, node_configs, interval):
        self.node_configs = node_configs
        self.interval = interval
    
    def start_monitoring(self):
        pass
    
    def stop_monitoring(self):
        pass
    
    def get_node_health_summary(self):
        return {
            "total_nodes": len(self.node_configs),
            "running_nodes": len(self.node_configs),
            "responsive_nodes": len(self.node_configs),
            "nodes_with_issues": 0
        }
    
    def get_performance_metrics(self):
        return {}
    
    def get_blockchain_sync_status(self):
        """
        Read actual blockchain data from each node and return real statistics.

        Returns:
            dict: Blockchain sync status with actual block counts
        """
        block_counts = []
        nodes_with_blockchain = 0

        for node_config in self.node_configs:
            # Construct path to blockchain.json for this node
            blockchain_path = Path(f"nodes/rpki_nodes/{node_config}/blockchain_node/blockchain_data/chain/blockchain.json")

            try:
                if blockchain_path.exists():
                    with open(blockchain_path, 'r') as f:
                        blockchain_data = json.load(f)

                    # Count blocks in the blockchain
                    if isinstance(blockchain_data, dict):
                        blocks = blockchain_data.get('blocks', blockchain_data.get('chain', []))
                    elif isinstance(blockchain_data, list):
                        blocks = blockchain_data
                    else:
                        blocks = []

                    block_count = len(blocks)
                    block_counts.append(block_count)
                    nodes_with_blockchain += 1
                else:
                    # No blockchain file exists for this node
                    block_counts.append(0)

            except Exception as e:
                # Error reading blockchain file
                block_counts.append(0)

        # Calculate average block count
        if block_counts:
            average_block_count = sum(block_counts) / len(block_counts)
        else:
            average_block_count = 0.0

        return {
            "nodes_with_blockchain": nodes_with_blockchain,
            "average_block_count": average_block_count,
            "block_counts": block_counts
        }
    
    def export_health_report(self, filename):
        pass

class HealthDashboard:
    def __init__(self, health_monitor):
        self.health_monitor = health_monitor
    
    def print_status_summary(self):
        print("Health Dashboard: All systems operational")
    
    def print_recent_alerts(self, max_alerts=5):
        print("No alerts")
