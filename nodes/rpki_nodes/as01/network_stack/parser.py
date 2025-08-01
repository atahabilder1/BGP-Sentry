import re
import json
from typing import List, Dict
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def parse_bgpd_log(log_file: str) -> List[Dict]:
    """
    Parse bgpd.log file to extract BGP announcements with path length of 1.
    Returns a list of dictionaries containing sender ASN, announced prefixes, and timestamp.
    """
    announcements = []
    current_update = None
    update_pattern = re.compile(
        r'^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[.*\] (\d+\.\d+\.\d+\.\d+)\((bgpd-R\d+)\) rcvd UPDATE w/ attr: nexthop \d+\.\d+\.\d+\.\d+, origin \w+(?:, metric \d+)?, path (\S+)$'
    )
    prefix_pattern = re.compile(
        r'^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[.*\] (\d+\.\d+\.\d+\.\d+)\((bgpd-R\d+)\) rcvd (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast$'
    )

    with open(log_file, 'r') as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()
            # Match UPDATE line with path
            update_match = update_pattern.match(line)
            if update_match:
                try:
                    timestamp, sender_ip, router_id, path = update_match.groups()
                    path_list = path.split()
                    if len(path_list) == 1:  # Strictly check for path length of 1
                        current_update = {
                            'timestamp': timestamp,
                            'sender_asn': int(path_list[0]),
                            'sender_ip': sender_ip,
                            'router_id': router_id,
                            'announced_prefixes': []
                        }
                        logging.debug(f"Valid UPDATE line {line_number}: {line}")
                    else:
                        logging.debug(f"Skipping UPDATE line {line_number} with path length {len(path_list)}: {line}")
                        current_update = None
                except Exception as e:
                    logging.warning(f"Skipping malformed UPDATE line {line_number}: {line} - Error: {e}")
                    current_update = None
                continue

            # Match prefix line
            prefix_match = prefix_pattern.match(line)
            if prefix_match:
                try:
                    prefix_timestamp, prefix_sender_ip, prefix_router_id, prefix = prefix_match.groups()
                    if current_update:
                        # Require sender IP, router ID match, and timestamp difference up to 0.1ms
                        time_diff = abs(float(prefix_timestamp.split('.')[-1]) - float(current_update['timestamp'].split('.')[-1])) / 1000  # Convert to ms
                        if (prefix_sender_ip == current_update['sender_ip'] and 
                            prefix_router_id == current_update['router_id'] and 
                            (prefix_timestamp == current_update['timestamp'] or time_diff < 0.1)):
                            announcements.append({
                                'sender_asn': current_update['sender_asn'],
                                'announced_prefixes': [prefix],
                                'timestamp': prefix_timestamp
                            })
                            logging.debug(f"Added prefix {prefix} at line {line_number} to UPDATE at {current_update['timestamp']} (sender_ip={prefix_sender_ip}, router_id={prefix_router_id}, diff={time_diff:.3f}ms)")
                        else:
                            logging.debug(f"Skipping prefix line {line_number} due to sender IP mismatch ({prefix_sender_ip} vs {current_update['sender_ip']}), router ID mismatch ({prefix_router_id} vs {current_update['router_id']}), or timestamp mismatch (diff={time_diff:.3f}ms): {line}")
                            current_update = None  # Reset after mismatch
                    else:
                        logging.debug(f"Skipping prefix line {line_number} with no valid current UPDATE: {line}")
                except Exception as e:
                    logging.warning(f"Skipping malformed prefix line {line_number}: {line} - Error: {e}")
                    current_update = None
                continue

            # Reset current_update on non-UPDATE, non-prefix lines
            if current_update:
                logging.debug(f"Resetting current_update at line {line_number} due to non-UPDATE/prefix line: {line}")
                current_update = None

    return announcements

def write_to_json(data: List[Dict], output_file: str) -> None:
    """
    Write parsed BGP announcements to a JSON file.
    """
    with open(output_file, 'w') as f:
        json.dump({'bgp_announcements': data}, f, indent=2)

def main():
    input_file = 'bgpd.log'
    output_file = 'bgp_announcements.json'
    try:
        announcements = parse_bgpd_log(input_file)
        write_to_json(announcements, output_file)
        logging.info(f"Parsed {len(announcements)} announcements and saved to {output_file}")
    except FileNotFoundError:
        logging.error(f"Input file {input_file} not found")
    except Exception as e:
        logging.error(f"Error processing file: {e}")

if __name__ == '__main__':
    main()