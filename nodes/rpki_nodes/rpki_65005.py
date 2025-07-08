# --------------------------------------------------------------
# File: rpki_65005.py
# Purpose: Runs an RPKI-enabled node that can propose blocks
# Used By:
#   - Simulates RPKI AS 65005
#   - Participates in round-robin consensus and writes to Blockchain A
# Calls:
#   - blockchain.block
#   - blockchain.blockchain
#   - blockchain.trust_state
#   - shared_data/bgp_stream.jsonl (input)
# --------------------------------------------------------------

import sys
import os
import json
import time
from datetime import datetime
import hashlib

# Add project root to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
sys.path.append(PROJECT_ROOT)

from blockchain.block import Block, BGPAnnouncement
from blockchain.blockchain import add_block, get_chain_length, get_last_block
from blockchain.trust_state import load_trust_state, update_trust_score

CONFIG_FILE = os.path.join(CURRENT_DIR, "config_65005.json")
BGP_INPUT_FILE = os.path.join(PROJECT_ROOT, "shared_data", "bgp_stream.jsonl")

# --------------------------------------------------------------
# Load Configuration
# --------------------------------------------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

MY_ASN = config["my_asn"]
VALIDATORS = config["validators"]

# --------------------------------------------------------------
# Function: is_my_turn_to_propose
# --------------------------------------------------------------
def is_my_turn_to_propose(asn, validators, height):
    validator_ids = list(validators.keys())
    return validator_ids[height % len(validator_ids)] == str(asn)

# --------------------------------------------------------------
# Function: load_announcements_from_stream
# --------------------------------------------------------------
def load_announcements():
    announcements = []
    if os.path.exists(BGP_INPUT_FILE):
        with open(BGP_INPUT_FILE, "r") as f:
            lines = f.readlines()
        for line in lines:
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    announcement = BGPAnnouncement(
                        asn=data["asn"],
                        prefix=data["prefix"],
                        as_path=data["as_path"],
                        next_hop=data["next_hop"]
                    )
                    announcements.append(announcement)
            except Exception as e:
                print(f"Warning: Skipping malformed line. {e}")
    return announcements

# --------------------------------------------------------------
# Main: RPKI node loop
# --------------------------------------------------------------
def main():
    print(f"🔐 RPKI Node {MY_ASN} started.")
    while True:
        height = get_chain_length()
        last_block = get_last_block()
        prev_hash = last_block["hash"] if last_block else "0" * 64

        if is_my_turn_to_propose(MY_ASN, VALIDATORS, height):
            announcements = load_announcements()
            if announcements:
                block = Block(
                    index=height,
                    previous_hash=prev_hash,
                    proposer=MY_ASN,
                    announcements=announcements
                )
                add_block(block)
                print(f"[{datetime.now()}] ✅ Block proposed by ASN {MY_ASN}")
        else:
            print(f"[{datetime.now()}] ⏳ Waiting — Not my turn.")

        time.sleep(10)

if __name__ == "__main__":
    main()
