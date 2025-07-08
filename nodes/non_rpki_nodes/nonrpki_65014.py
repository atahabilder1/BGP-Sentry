# --------------------------------------------------------------
# File: nonrpki_65014.py
# Purpose: Logic for non-RPKI node ASN 65014
# Used By:
#   - Simulates BGP announcements from ASN 65014
#   - Sends announcements to shared_data/bgp_stream.jsonl
# --------------------------------------------------------------

import json
import time
import random
import os
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
CONFIG_FILE = os.path.join(CURRENT_DIR, "config_65014.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "shared_data", "bgp_stream.jsonl")

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

MY_ASN = config["my_asn"]
PREFIXES = config.get("prefixes", [])
NEXT_HOPS = config.get("next_hops", [])
AS_PATH_POOL = config.get("as_path_pool", [MY_ASN, 65001, 65002, 65003])

def generate_announcement():
    return {
        "asn": MY_ASN,
        "prefix": random.choice(PREFIXES),
        "as_path": random.sample(AS_PATH_POOL, k=random.randint(1, 3)),
        "next_hop": random.choice(NEXT_HOPS),
        "timestamp": int(time.time()),
        "type": random.choices(["announce", "withdraw"], weights=[0.85, 0.15])[0]
    }

def main():
    print(f"🚀 Starting non-RPKI node for ASN {MY_ASN}")
    while True:
        announcement = generate_announcement()
        try:
            with open(OUTPUT_FILE, "a") as f:
                f.write(json.dumps(announcement) + "\n")
            print(f"[{datetime.now()}] ✉️  BGP Announcement: {announcement}")
        except FileNotFoundError:
            print(f"❌ ERROR: File not found at {OUTPUT_FILE}.")
            break
        time.sleep(random.randint(10, 60))

if __name__ == "__main__":
    main()
