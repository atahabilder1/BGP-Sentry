import os
import re
import json
from datetime import datetime

# Define paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))  # Move up two levels to BGP_Announcement_Recorder
MININET_LOGS_DIR = os.path.join(ROOT_DIR, 'bgp_feed', 'mininet_logs')
SHARED_DATA_DIR = os.path.join(ROOT_DIR, 'shared_data')
OUTPUT_FILE = os.path.join(SHARED_DATA_DIR, 'bgp_announcements.json')

# Ensure shared_data directory exists
os.makedirs(SHARED_DATA_DIR, exist_ok=True)

# Regular expressions for parsing BGP log lines
SEND_UPDATE_RE = re.compile(
    r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[.*?\] u\d+:s\d+ send UPDATE (?:w/ attr: nexthop (\S+)(?:, origin (\S+))?(?:, path (.*?))?(?:, metric (\d+))?.*?)?(?:(\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast)?'
)
RCVD_UPDATE_RE = re.compile(
    r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[.*?\] (\d+\.\d+\.\d+\.\d+)(?:\(bgpd-R(\d+)\))? rcvd UPDATE (?:w/ attr: nexthop (\S+)(?:, origin (\S+))?(?:, path (.*?))?(?:, metric (\d+))?.*?)?(?:about (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast)?(?: -- DENIED due to: (.*?);)?'
)

def parse_log_file(filepath):
    announcements = []
    with open(filepath, 'r') as f:
        for line in f:
            # Parse sent updates
            send_match = SEND_UPDATE_RE.match(line)
            if send_match:
                timestamp, nexthop, origin, as_path, metric, prefix = send_match.groups()
                if prefix:  # Ensure prefix is present
                    announcement = {
                        'type': 'sent',
                        'timestamp': timestamp,
                        'prefix': prefix,
                        'nexthop': nexthop or 'N/A',
                        'origin': origin or 'N/A',
                        'as_path': as_path.strip() if as_path else 'N/A',
                        'metric': metric or 'N/A',
                        'router': os.path.basename(filepath).split('-')[0]  # e.g., R1 from R1-bgpd.log
                    }
                    announcements.append(announcement)

            # Parse received updates
            rcvd_match = RCVD_UPDATE_RE.match(line)
            if rcvd_match:
                timestamp, peer, router_id, nexthop, origin, as_path, metric, prefix, denied_reason = rcvd_match.groups()
                if prefix:  # Ensure prefix is present
                    announcement = {
                        'type': 'received',
                        'timestamp': timestamp,
                        'prefix': prefix,
                        'peer': peer,
                        'router_id': f'R{router_id}' if router_id else 'N/A',
                        'nexthop': nexthop or 'N/A',
                        'origin': origin or 'N/A',
                        'as_path': as_path.strip() if as_path else 'N/A',
                        'metric': metric or 'N/A',
                        'denied': bool(denied_reason),
                        'denied_reason': denied_reason or 'N/A',
                        'router': os.path.basename(filepath).split('-')[0]
                    }
                    announcements.append(announcement)
    
    return announcements

def main():
    all_announcements = []
    
    # Process all bgpd log files in mininet_logs directory
    for filename in os.listdir(MININET_LOGS_DIR):
        if filename.endswith('-bgpd.log'):
            filepath = os.path.join(MININET_LOGS_DIR, filename)
            announcements = parse_log_file(filepath)
            all_announcements.extend(announcements)
    
    # Sort announcements by timestamp
    all_announcements.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y/%m/%d %H:%M:%S.%f'))
    
    # Save to JSON file in shared_data
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_announcements, f, indent=2)
    
    print(f"Extracted {len(all_announcements)} BGP announcements and saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()