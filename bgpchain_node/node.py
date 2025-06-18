# --------------------------------------------------------------
# node.py
# --------------------------------------------------------------
# This is the main script that runs a single BGP blockchain node.
# Responsibilities:
#   - Load configuration (ASN and validator list)
#   - Determine if it's this node's turn to propose (round-robin)
#   - Collect BGP announcements
#   - Propose and add new blocks to the blockchain
#
# Uses:
#   - config.json
#   - block.py (Block class)
#   - bgp_collector.py (to collect BGP announcements)
#   - blockchain.py (to get/add blocks)
# --------------------------------------------------------------

import json
import time
from block import Block
from blockchain import add_block, get_last_block, get_chain_length
from bgp_collector import collect_bgp_announcements

# --------------------------------------------------------------
# Function: load_config
# Loads the local ASN and validator list from config.json
# --------------------------------------------------------------
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

# --------------------------------------------------------------
# Function: is_my_turn_to_propose
# Determines if this node is the proposer based on round-robin
# logic using block height and validator order.
# --------------------------------------------------------------
def is_my_turn_to_propose(my_asn, validators, block_height):
    validator_ids = list(validators.keys())
    proposer_index = block_height % len(validator_ids)
    return validator_ids[proposer_index] == str(my_asn)

# --------------------------------------------------------------
# Main Function: Starts the node loop
# Every 10 seconds:
#   - Check if it's this ASN's turn to propose
#   - If yes, collect BGP announcements and create a block
#   - Add block to the local blockchain
# --------------------------------------------------------------
def main():
    config = load_config()
    my_asn = config["my_asn"]
    validators = config["validators"]

    while True:
        block_height = get_chain_length()                   # Current chain length
        last_block = get_last_block()                       # Last block on chain
        previous_hash = last_block["hash"] if last_block else "0" * 64

        if is_my_turn_to_propose(my_asn, validators, block_height):
            print(f"✅ ASN {my_asn} is proposer for block {block_height}")
            bgp_announcements = collect_bgp_announcements()  # Get announcements
            block = Block(
                index=block_height,
                previous_hash=previous_hash,
                proposer=my_asn,
                announcements=bgp_announcements
            )
            add_block(block)
            print(f"📦 Block {block_height} added by ASN {my_asn}")
        else:
            print(f"⏳ ASN {my_asn} is waiting — block {block_height} proposer not me.")

        time.sleep(10)  # Wait 10 seconds before checking again

# --------------------------------------------------------------
# Entry point
# --------------------------------------------------------------
if __name__ == "__main__":
    main()
