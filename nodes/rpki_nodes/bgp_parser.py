#!/usr/bin/env python3
# Shebang line to ensure the script runs with Python 3

import re
from collections import defaultdict
import json
import logging
import sys
import os

# Configure logging to track script execution and errors
logging.basicConfig(
    filename='/opt/rpki_nodes/output/bgp_parser.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def parse_bgp_log(log_file, peer_as_map):
    """
    Parse BGP log file to extract announcements with single-hop AS path.
    
    Args:
        log_file (str): Path to the BGP log file.
        peer_as_map (dict): Mapping of peer IPs to their AS numbers (e.g., {'9.0.5.2': 4}).
    
    Returns:
        dict: Mapping of peer IPs to lists of announcement dictionaries with AS number, type, and prefix.
    """
    # Initialize dictionary to store peer-to-announcement mappings
    peer_prefixes = defaultdict(list)
    
    # Regular expressions for parsing log lines
    update_re = re.compile(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+ BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd UPDATE w/ attr:.*path (\S+)$')
    prefix_re = re.compile(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+ BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast$')
    withdraw_re = re.compile(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+ BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd UPDATE about (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast -- withdrawn$')
    duplicate_re = re.compile(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+ BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast\.\.\.duplicate ignored$')
    denied_re = re.compile(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+ BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd UPDATE about (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast -- DENIED')
    
    # Temporary storage for current UPDATE message's AS path
    current_peer = None
    current_as_path = None
    processed_prefixes = set()  # Track processed prefixes to handle duplicates
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Match UPDATE message with AS path
                update_match = update_re.match(line)
                if update_match:
                    current_peer = update_match.group(1)
                    current_as_path = update_match.group(2).split()
                    logging.info(f"Found UPDATE from peer {current_peer} with AS path {current_as_path}")
                    continue
                
                # Match prefix announcement
                prefix_match = prefix_re.match(line)
                if prefix_match and current_peer and current_as_path:
                    peer_ip = prefix_match.group(1)
                    prefix = prefix_match.group(2)
                    # Ensure the peer IP matches and AS path has one hop
                    if peer_ip == current_peer and len(current_as_path) == 1:
                        # Verify the AS matches the peer's AS
                        if peer_as_map.get(peer_ip) == int(current_as_path[0]):
                            prefix_key = (peer_ip, prefix)
                            if prefix_key not in processed_prefixes:
                                # Add announcement dictionary
                                peer_prefixes[peer_ip].append({
                                    "as_number": peer_as_map[peer_ip],
                                    "type": "announcement",
                                    "prefix": prefix
                                })
                                processed_prefixes.add(prefix_key)
                                logging.info(f"Added prefix {prefix} for peer {peer_ip} (AS {peer_as_map[peer_ip]})")
                    continue
                
                # Handle withdrawals
                withdraw_match = withdraw_re.match(line)
                if withdraw_match:
                    peer_ip = withdraw_match.group(1)
                    prefix = withdraw_match.group(2)
                    prefix_key = (peer_ip, prefix)
                    if prefix_key in processed_prefixes:
                        # Remove the matching prefix dictionary
                        peer_prefixes[peer_ip] = [
                            entry for entry in peer_prefixes[peer_ip]
                            if entry["prefix"] != prefix
                        ]
                        processed_prefixes.remove(prefix_key)
                        logging.info(f"Removed withdrawn prefix {prefix} for peer {peer_ip}")
                    continue
                
                # Skip duplicates
                duplicate_match = duplicate_re.match(line)
                if duplicate_match:
                    logging.debug(f"Ignored duplicate prefix {duplicate_match.group(2)} from peer {duplicate_match.group(1)}")
                    continue
                
                # Skip denied updates
                denied_match = denied_re.match(line)
                if denied_match:
                    logging.debug(f"Ignored denied prefix {denied_match.group(2)} from peer {denied_match.group(1)}")
                    continue
    
    except FileNotFoundError:
        logging.error(f"Log file {log_file} not found")
        return {}
    except Exception as e:
        logging.error(f"Error parsing log file: {str(e)}")
        return {}
    
    # Convert defaultdict to regular dict
    result = dict(peer_prefixes)
    
    # Print the result to console as JSON
    print(json.dumps(result, indent=4))
    
    # Log the result
    logging.info(f"Parsed prefixes: {json.dumps(result)}")
    
    return result

def main(log_file, peer_as_map):
    """
    Main function to process the BGP log and write results to a file.
    
    Args:
        log_file (str): Path to the BGP log file.
        peer_as_map (dict): Mapping of peer IPs to their AS numbers.
    """
    logging.info(f"Starting BGP log parsing for file: {log_file}")
    result = parse_bgp_log(log_file, peer_as_map)
    
    # Write results to JSON file
    output_file = '/opt/rpki_nodes/output/bgp_prefixes.json'
    try:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
        logging.info(f"Results written to {output_file}")
    except Exception as e:
        logging.error(f"Error writing to output file: {str(e)}")

if __name__ == "__main__":
    # Default peer-to-AS mapping
    peer_as_map = {
        '9.0.5.2': 4,
        '9.0.6.2': 10,
        '9.0.7.2': 12
    }
    
    # Check for command-line argument for log file path
    log_file = "/opt/rpki_nodes/logs/bgp_log.txt"
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    
    # Verify log file exists
    if not os.path.exists(log_file):
        logging.error(f"Log file {log_file} does not exist")
        sys.exit(1)
    
    main(log_file, peer_as_map)