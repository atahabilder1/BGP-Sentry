# --------------------------------------------------------------
# File: bgp_simulator.py
# Purpose: Generate simulated BGP announcements and withdrawals
# Used By: Run independently to feed announcements to the buffer
# Calls:
#   - Writes to shared_data/bgp_stream.jsonl
# Consumed By:
#   - bgp_collector.py (read by node.py during block creation)
# --------------------------------------------------------------

import json
import time
import random
import os
from datetime import datetime

# Resolve the output path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "shared_data", "bgp_stream.jsonl")

# Example ASNs: mix of RPKI and non-RPKI
ASNS = list(range(65010, 65020))  # 10 non-RPKI simulated ASNs
PREFIXES = [
    "203.0.113.0/24", "192.0.2.0/24", "198.51.100.0/24",
    "10.0.0.0/8", "172.16.0.0/16"
]
NEXT_HOPS = ["192.0.2.1", "10.1.1.1", "172.16.0.1"]

# Wallets associated with ASNs (for staking on Blockchain B)
WALLETS = {
    65010: "0xabc123...", 65011: "0xdef456...", 65012: "0x789abc...",
    65013: "0xdeadbeef...", 65014: "0xfacefeed...",
    65015: "0x999888...", 65016: "0x777555...", 65017: "0xaaaaaa...",
    65018: "0xbbbbbb...", 65019: "0xcccccc..."
}

def generate_bgp_announcement():
    asn = random.choice(ASNS)
    prefix = random.choice(PREFIXES)
    bgp_type = random.choices(["announce", "withdraw"], weights=[0.8, 0.2])[0]

    return {
        "asn": asn,
        "prefix": prefix,
        "as_path": [asn, 65001],  # Pretend 65001 is the next hop (RPKI)
        "next_hop": random.choice(NEXT_HOPS),
        "timestamp": int(time.time()),
        "type": bgp_type,
        "wallet_address": WALLETS.get(asn, "")
    }

def main():
    print(f"🚀 BGP Simulator started. Writing to: {OUTPUT_FILE}")
    while True:
        announcement = generate_bgp_announcement()
        with open(OUTPUT_FILE, "a") as f:
            f.write(json.dumps(announcement) + "\n")
        print(f"[{datetime.now()}] 📡 Generated: {announcement}")
        time.sleep(3)

if __name__ == "__main__":
    main()
