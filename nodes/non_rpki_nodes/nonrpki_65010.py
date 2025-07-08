# --------------------------------------------------------------
# File: nonrpki_65010.py
# Purpose: Logic for a non-RPKI node (ASN 65010)
# Used By:
#   - Simulates BGP announcements and occasional withdrawals
#   - Mimics realistic BGP behavior with random intervals
# Calls:
#   - Generates BGP events to shared_data/bgp_stream.jsonl
# --------------------------------------------------------------

import json
import time
import random
import os
from datetime import datetime

# --------------------------------------------------------------
# Resolve base project directory and paths
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
PREFIXES = config.get("prefixes", ["203.0.113.0/24", "192.0.2.0/24"])
NEXT_HOPS = config.get("next_hops", ["10.0.0.1", "10.1.1.1"])
AS_PATH_POOL = config.get("as_path_pool", [MY_ASN, 65001, 65002, 65003])

# Track active announcements
active_prefixes = set()

# --------------------------------------------------------------
# Generate a realistic BGP announcement
# --------------------------------------------------------------
def generate_announcement():
    prefix = random.choice(PREFIXES)
    as_path = random.sample(AS_PATH_POOL, k=random.randint(1, 3))
    announcement = {
        "asn": MY_ASN,
        "prefix": prefix,
        "as_path": as_path,
        "next_hop": random.choice(NEXT_HOPS),
        "timestamp": int(time.time()),
        "type": "announce"
    }
    active_prefixes.add(prefix)
    return announcement

# --------------------------------------------------------------
# Generate a withdrawal for a previously announced prefix
# --------------------------------------------------------------
def generate_withdrawal():
    prefix = random.choice(list(active_prefixes))
    withdrawal = {
        "asn": MY_ASN,
        "prefix": prefix,
        "as_path": [],
        "next_hop": "",
        "timestamp": int(time.time()),
        "type": "withdraw"
    }
    active_prefixes.remove(prefix)
    return withdrawal

# --------------------------------------------------------------
# Main loop: emits announce/withdraw events periodically
# --------------------------------------------------------------
def main():
    print(f"🚀 Starting non-RPKI node for ASN {MY_ASN}")
    while True:
        try:
            # 80% chance: announcement | 20% chance: withdrawal
            if random.random() < 0.8 or not active_prefixes:
                event = generate_announcement()
            else:
                event = generate_withdrawal()

            with open(OUTPUT_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")

            print(f"[{datetime.now()}] 📡 BGP {event['type'].upper()}: {event}")
        except FileNotFoundError:
            print(f"❌ ERROR: Output file not found at {OUTPUT_FILE}. Make sure shared_data/ exists.")
            break

        # Wait 10–60 seconds before next event
        sleep_time = random.randint(10, 60)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
