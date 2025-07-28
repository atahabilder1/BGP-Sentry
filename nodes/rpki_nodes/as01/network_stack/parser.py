import re
import json
from datetime import datetime
import os

def parse_bgp_log():
    announcements = []
    current_announcement = None
    log_file = 'bgpd.log'
    sender_asn_default = 2
    last_peer_ip = None
    prefix_window_active = False

    # Check if log file exists
    if not os.path.exists(log_file):
        print(f"Error: {log_file} not found in the current directory.")
        return

    with open(log_file, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # Match lines with rcvd UPDATE w/ attr containing a single ASN path
        path_match = re.match(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{6}) BGP: \[\w+-\w+\] (\d+\.\d+\.\d+\.\d+)\(bgpd-R\d+\) rcvd UPDATE w/ attr: nexthop \d+\.\d+\.\d+\.\d+, origin i,.* path (\d+)$', line)
        if path_match:
            timestamp, peer_ip, as_path = path_match.groups()
            # Close any previous announcement
            prefix_window_active = False
            # Start a new announcement
            try:
                dt = datetime.strptime(timestamp, '%Y/%m/%d %H:%M:%S.%f')
                iso_timestamp = dt.isoformat() + 'Z'
            except ValueError:
                print(f"Warning: Invalid timestamp format at line {i+1}: {timestamp}")
                continue
            current_announcement = {
                "sender_asn": sender_asn_default,
                "announced_prefixes": [],
                "timestamp": iso_timestamp
            }
            announcements.append(current_announcement)
            last_peer_ip = peer_ip
            prefix_window_active = True
            continue

        # Match lines with rcvd prefixes
        prefix_match = re.match(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{6} BGP: \[\w+-\w+\] (\d+\.\d+\.\d+\.\d+)\(bgpd-R\d+\) rcvd (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast$', line)
        if prefix_match and current_announcement and prefix_window_active and last_peer_ip:
            peer_ip, prefix = prefix_match.groups()
            # Ensure the prefix belongs to the current announcement's peer
            if peer_ip == last_peer_ip:
                # Check next few lines for DENIED or duplicate
                skip = False
                for j in range(i, min(i + 3, len(lines))):
                    if 'DENIED due to: as-path contains our own AS' in lines[j] or 'duplicate ignored' in lines[j]:
                        skip = True
                        break
                if not skip:
                    current_announcement["announced_prefixes"].append(prefix)
            continue

        # Close prefix window if we encounter a non-prefix line
        if current_announcement and prefix_window_active and not prefix_match:
            prefix_window_active = False

    # Filter out announcements with no prefixes
    announcements = [ann for ann in announcements if ann["announced_prefixes"]]

    # Write to bgpd.json
    output = {"bgp_announcements": announcements}
    try:
        with open('bgpd.json', 'w') as f:
            json.dump(output, f, indent=2)
        print("Successfully wrote parsed announcements to bgpd.json")
    except Exception as e:
        print(f"Error writing to bgpd.json: {e}")

if __name__ == "__main__":
    parse_bgp_log()