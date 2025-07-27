import logging
import threading
import time
import signal
import sys
from pathlib import Path
import colorama

# Initialize colorama for cross-platform colorful output
colorama.init()

# Find BGP_Announcement_Recorder root for sys.path
def find_project_root(start_path):
    """
    Find the BGP_Announcement_Recorder directory by walking up from start_path.
    Returns: Path object or raises FileNotFoundError if not found.
    """
    current = Path(start_path).resolve()
    while current != current.parent:
        if current.name == "BGP_Announcement_Recorder":
            return current
        current = current.parent
    raise FileNotFoundError(
        "Could not find 'BGP_Announcement_Recorder' directory. "
        "Ensure script is run from within the project."
    )

# Add project root to sys.path for relative imports
try:
    project_root = find_project_root(__file__)
    sys.path.insert(0, str(project_root))
except FileNotFoundError as e:
    print(f"\033[31m❌ Error: {str(e)}\033[0m")
    sys.exit(1)

# Specific imports from shared_blockchain_stack
from nodes.rpki_nodes.shared_blockchain_stack.bgp_parser.parse_bgp import parse_bgp_data
from nodes.rpki_nodes.shared_blockchain_stack.concensus_engine.verify_transaction import verify_transaction
from nodes.rpki_nodes.shared_blockchain_stack.block_proposer.create_transaction import create_transaction
from nodes.rpki_nodes.shared_blockchain_stack.block_proposer.commit_to_blockchain import commit_to_blockchain
from nodes.rpki_nodes.shared_blockchain_stack.transaction_pool import add_transaction
from nodes.rpki_nodes.shared_blockchain_stack.utils.stake_engine.staking_interface import stake
from nodes.rpki_nodes.shared_blockchain_stack.utils.trust_engine.trust_engine_instant import calculate_trust_instant
from nodes.rpki_nodes.shared_blockchain_stack.utils.trust_engine.trust_engine_periodic import calculate_trust_periodic
from nodes.rpki_nodes.shared_blockchain_stack.utils.trust_engine.trust_state import update_trust_state


print("import is succcessful")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("node.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Validate function existence
for func in [parse_bgp_data, proposer_main, verify_transaction]:
    if not callable(func):
        logger.error(f"Function {func.__name__} is not callable")
        print(f"\033[31m❌ Error: Function {func.__name__} is not callable. Verify module imports.\033[0m")
        sys.exit(1)

# Background thread configuration
THREAD_CONFIG = {
    "bgp_parser": {
        "func": parse_bgp_data,
        "args": (),  # Add arguments if needed, e.g., ("bgp_config.json",)
        "sleep_interval": 1
    },
    "block_proposer": {
        "func": proposer_main,
        "args": (),  # Add arguments if needed
        "sleep_interval": 1
    },
    "concensus_engine": {
        "func": verify_transaction,
        "args": (),  # Add arguments if needed
        "sleep_interval": 1
    }
}

def run_in_background(name, config):
    """
    Run a function in a background thread with error handling and restart.
    Args:
        name: Thread name (e.g., 'bgp_parser').
        config: Dict with func, args, and sleep_interval.
    """
    def wrapper():
        while True:
            logger.info(f"Starting background thread for {name}")
            try:
                while True:
                    config["func"](*config["args"])
                    time.sleep(config["sleep_interval"])
            except Exception as e:
                logger.error(f"Error in {name} thread: {str(e)}")
                print(f"\033[31m❌ Error in {name}: {str(e)}\033[0m")
                time.sleep(10)  # Wait before restarting
    thread = threading.Thread(target=wrapper, name=name, daemon=True)
    thread.start()
    logger.debug(f"Started {name} thread")
    print(f"\033[32m✅ Started {name} in background\033[0m")
    return thread

# Start background threads automatically
threads = {}
try:
    for name, config in THREAD_CONFIG.items():
        threads[name] = run_in_background(name, config)
except NameError as e:
    logger.error(f"Failed to start background threads: {str(e)}")
    print(f"\033[31m❌ Error: Failed to start background threads: {str(e)}\033[0m")
    sys.exit(1)

# Graceful shutdown handler
def shutdown_handler(signum, frame):
    logger.info("Received shutdown signal")
    print(f"\033[32m✅ Shutting down node\033[0m")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

def main():
    """
    Main function for node-specific logic.
    """
    logger.info("Starting node.py in as05/blockchain_node")
    while True:
        try:
            # Example node logic
            parsed_data = {
                "sender_asn": 5,
                "ip_prefix": "203.0.113.0/24",
                "timestamp": "2025-07-26T18:00:00Z",
                "trust_score": "N/A",
                "prefix_length": 24
            }
            transaction_id = create_transaction(parsed_data)
            add_transaction({"transaction_id": transaction_id})
            commit_to_blockchain()
            stake(amount=1000)
            calculate_trust_instant()
            update_trust_state()
            logger.info("Node logic executed successfully")
            print(f"\033[32m✅ Node logic executed\033[0m")

            # Monitor thread health
            for name, thread in threads.items():
                if not thread.is_alive():
                    logger.error(f"{name} thread stopped unexpectedly")
                    print(f"\033[31m❌ {name} thread stopped\033[0m")
                    # Restart thread
                    threads[name] = run_in_background(name, THREAD_CONFIG[name])

            time.sleep(60)  # Run logic every 60 seconds
            logger.debug("Node.py still running")
        except KeyboardInterrupt:
            shutdown_handler(None, None)
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            print(f"\033[31m❌ Error in main loop: {str(e)}\033[0m")
            time.sleep(10)  # Prevent rapid error looping

if __name__ == "__main__":
    main()