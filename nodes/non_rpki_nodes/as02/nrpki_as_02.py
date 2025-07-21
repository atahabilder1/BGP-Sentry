# --------------------------------------------------------------
# File: nonrpki_65010.py
# Purpose: Non-RPKI node simulator (ASN 65010) using config file only
# --------------------------------------------------------------

import json
import time
import random
import os
from datetime import datetime

# --------------------------------------------------------------
# Resolve Paths
# --------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
CONFIG_FILE = os.path.join(CURRENT_DIR, "config_65010.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "shared_data", "bgp_stream.jsonl")

# --------------------------------------------------------------
# Load Configuration
# --------------------------------------------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

MY_ASN = config["my_asn"]
WALLET = config["wallet_address"]
PREFIXES = config.get("prefixes", [])
NEXT_HOPS = config.get("next_hops", [])
AS_PATH_POOL = config.get("as_path_pool", [MY_ASN])

active_prefixes = set()

# --------------------------------------------------------------
# Generate Announcement
# --------------------------------------------------------------
def generate_announcement():
    prefix = random.choice(PREFIXES)
    as_path = random.sample(AS_PATH_POOL, k=random.randint(1, len(AS_PATH_POOL)))
    return {
        "asn": MY_ASN,
        "prefix": prefix,
        "as_path": as_path,
        "next_hop": random.choice(NEXT_HOPS),
        "timestamp": int(time.time()),
        "type": "announce",
        "wallet_address": WALLET
    }

# --------------------------------------------------------------
# Generate Withdrawal
# --------------------------------------------------------------
def generate_withdrawal():
    prefix = random.choice(list(active_prefixes))
    active_prefixes.remove(prefix)
    return {
        "asn": MY_ASN,
        "prefix": prefix,
        "as_path": [],
        "next_hop": "",
        "timestamp": int(time.time()),
        "type": "withdraw",
        "wallet_address": WALLET
    }

# --------------------------------------------------------------
# Main Event Loop
# --------------------------------------------------------------
def main():
    print(f"🚀 Starting non-RPKI node for ASN {MY_ASN}")
    while True:
        try:
            if random.random() < 0.8 or not active_prefixes:
                event = generate_announcement()
                active_prefixes.add(event["prefix"])
            else:
                event = generate_withdrawal()

            with open(OUTPUT_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")

            print(f"[{datetime.now()}] 📡 BGP {event['type'].upper()}: {event}")
        except FileNotFoundError:
            print(f"❌ ERROR: Output file not found at {OUTPUT_FILE}")
            break

        time.sleep(random.randint(10, 60))

if __name__ == "__main__":
    main()
