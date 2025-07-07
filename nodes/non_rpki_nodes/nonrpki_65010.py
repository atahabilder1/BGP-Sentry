# --------------------------------------------------------------
# File: nonrpki_65010.py
# Purpose: Logic for a non-RPKI node (ASN 65010)
# Used By:
#   - Simulates BGP announcements from a non-trusted AS
#   - Optionally interacts with Blockchain B to stake USDC
# Calls:
#   - Generates announcements to bgp_stream.jsonl
#   - Can invoke web3 API for staking (optional)
# --------------------------------------------------------------

import json
import time
import random
import os
from datetime import datetime

# ---------------------------
# Load Configuration
# ---------------------------
with open("nodes/non_rpki_nodes/config_65010.json", "r") as f:
    config = json.load(f)

MY_ASN = config["my_asn"]
PREFIXES = config.get("prefixes", ["203.0.113.0/24", "192.0.2.0/24"])
NEXT_HOPS = config.get("next_hops", ["10.0.0.1", "10.1.1.1"])
AS_PATH_POOL = config.get("as_path_pool", [MY_ASN, 65001, 65002, 65003])

# ---------------------------
# Output File
# ---------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "shared_data", "bgp_stream.jsonl")

# ---------------------------
# Function: generate_announcement
# ---------------------------
def generate_announcement():
    return {
        "asn": MY_ASN,
        "prefix": random.choice(PREFIXES),
        "as_path": random.sample(AS_PATH_POOL, k=random.randint(1, 3)),
        "next_hop": random.choice(NEXT_HOPS),
        "timestamp": int(time.time()),
        "type": "announce"  # Or "withdraw" for testing
    }

# ---------------------------
# Main loop: Feed announcements
# ---------------------------
def main():
    print(f"🚀 Starting non-RPKI node for ASN {MY_ASN}")
    while True:
        announcement = generate_announcement()
        with open(OUTPUT_FILE, "a") as f:
            f.write(json.dumps(announcement) + "\n")
        print(f"[{datetime.now()}] ✉️  BGP Announcement: {announcement}")
        time.sleep(5)

if __name__ == "__main__":
    main()
