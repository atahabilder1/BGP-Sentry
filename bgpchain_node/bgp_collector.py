# --------------------------------------------------------------
# bgp_collector.py
# --------------------------------------------------------------
# Reads BGP announcements from the shared JSONL file.
# Converts each line into a BGPAnnouncement object.
# Used by node.py during block proposal.
# --------------------------------------------------------------

import os
import json
from block import BGPAnnouncement

# Set the path to the shared BGP stream
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAM_FILE = os.path.join(BASE_DIR, "shared_data", "bgp_stream.jsonl")

def collect_bgp_announcements(max_announcements=5):
    announcements = []
    lines_to_keep = []

    try:
        # Read all lines from the JSONL file
        with open(STREAM_FILE, "r") as f:
            lines = f.readlines()

        # Take only the first N announcements
        for line in lines:
            if len(announcements) >= max_announcements:
                lines_to_keep.append(line)  # retain for next time
                continue

            try:
                data = json.loads(line.strip())
                announcement = BGPAnnouncement(
                    asn=data["asn"],
                    prefix=data["prefix"],
                    as_path=data["as_path"],
                    next_hop=data["next_hop"],
                    timestamp=data["timestamp"]
                )
                announcements.append(announcement)
            except (json.JSONDecodeError, KeyError):
                print(f"⚠️ Skipping invalid line: {line.strip()}")

        # Rewrite file with leftover lines
        with open(STREAM_FILE, "w") as f:
            f.writelines(lines_to_keep)

    except FileNotFoundError:
        print(f"❌ {STREAM_FILE} not found. Run the BGP generator first.")

    return announcements
