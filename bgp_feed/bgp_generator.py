# --------------------------------------------------------------
# bgp_generator.py
# --------------------------------------------------------------
# This standalone script simulates BGP announcements
# and appends them to a shared buffer file.
#
# Place this in bgp_feed/
# Run this separately to feed the blockchain node.
# --------------------------------------------------------------

import json
import time
import random
import os
from datetime import datetime

# Resolve shared_data directory path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "shared_data", "bgp_stream.jsonl")

ASNS = [64512, 64513, 64514, 64515, 64516]
PREFIXES = [
    "203.0.113.0/24", "192.0.2.0/24", "198.51.100.0/24", "10.0.0.0/8", "172.16.0.0/16"
]
NEXT_HOPS = ["192.0.2.1", "10.1.1.1", "172.16.0.1"]

def generate_bgp_announcement():
    return {
        "asn": random.choice(ASNS),
        "prefix": random.choice(PREFIXES),
        "as_path": random.sample(ASNS, random.randint(1, 3)),
        "next_hop": random.choice(NEXT_HOPS),
        "timestamp": int(time.time())
    }

def main():
    print(f"🚀 Starting BGP Generator. Output: {OUTPUT_FILE}")
    while True:
        announcement = generate_bgp_announcement()
        with open(OUTPUT_FILE, "a") as f:
            f.write(json.dumps(announcement) + "\n")
        print(f"[{datetime.now()}] 📡 Generated: {announcement}")
        time.sleep(2)

if __name__ == "__main__":
    main()
