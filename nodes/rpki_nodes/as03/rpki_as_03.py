# --------------------------------------------------------------
# File: rpki_65003.py
# Purpose: RPKI-enabled node for ASN 65003
# Used to read announcements from shared buffer and log verified ones to blockchain
# Uses keys/private/private_key_65003.pem for signing
# --------------------------------------------------------------

import json
import os
import time
from datetime import datetime
print("trying to import blockchain")
from blockchain.block import Block
print("trying to import blockchain")
from blockchain.blockchain import add_block, get_chain_length
from blockchain.trust_state import get_trust, set_trust
import hashlib

# --------------------------------------------------------------
# Setup Paths
# --------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "nodes/rpki_nodes/config_65003.json")
PRIVATE_KEY_FILE = os.path.join(BASE_DIR, "nodes/rpki_nodes/keys/private/private_key_65003.pem")
INPUT_STREAM = os.path.join(BASE_DIR, "shared_data/bgp_stream.jsonl")

# --------------------------------------------------------------
# Load Configuration
# --------------------------------------------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

MY_ASN = config["my_asn"]
TRUST_THRESHOLD = config["trust_threshold"]

# --------------------------------------------------------------
# Function: sign_announcement
# Simulates a digital signature using a hash of message + private key
# --------------------------------------------------------------
def sign_announcement(data_dict):
    with open(PRIVATE_KEY_FILE, "r") as f:
        private_key = f.read().strip()
    message = json.dumps(data_dict, sort_keys=True)
    return hashlib.sha256((message + private_key).encode()).hexdigest()

# --------------------------------------------------------------
# Function: process_announcement
# Validate trust score and log to blockchain if trustworthy
# --------------------------------------------------------------
def process_announcement(announcement):
    asn = announcement["asn"]
    prefix = announcement["prefix"]
    score = get_trust(asn, prefix)

    if score >= TRUST_THRESHOLD:
        signed_data = {
            "data": announcement,
            "signed_by": MY_ASN,
            "signature": sign_announcement(announcement)
        }
        block = Block(
            index=get_chain_length(),
            data=signed_data,
            timestamp=int(time.time())
        )
        add_block(block)
        print(f"[{datetime.now()}] ✅ Logged: {signed_data}")
    else:
        print(f"[{datetime.now()}] ❌ Skipped: Trust score {score} below threshold for {asn}-{prefix}")

# --------------------------------------------------------------
# Main Loop: Continuously watch stream and process announcements
# --------------------------------------------------------------
def main():
    print(f"🔐 RPKI Node {MY_ASN} started.")
    seen_lines = 0
    while True:
        if os.path.exists(INPUT_STREAM):
            with open(INPUT_STREAM, "r") as f:
                lines = f.readlines()
                new_lines = lines[seen_lines:]
                for line in new_lines:
                    try:
                        announcement = json.loads(line.strip())
                        process_announcement(announcement)
                    except Exception as e:
                        print(f"[!] Error: {e}")
                seen_lines = len(lines)
        time.sleep(5)

if __name__ == "__main__":
    main()
