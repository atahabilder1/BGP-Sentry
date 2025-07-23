#!/usr/bin/env python3
# Shebang line to ensure the script runs with Python 3

import re  # For regular expression matching of log lines
from collections import defaultdict  # For storing peer-to-prefix mappings
import json  # For reading/writing JSON config and output
import logging  # For logging operations and errors
import sys  # For command-line arguments and exit handling
import os  # For file and directory operations
from datetime import datetime  # For parsing timestamps
import pytz  # For handling UTC timezone
import itertools  # For grouping lines by timestamp

# Configure logging to write to a file for tracking script execution and errors
logging.basicConfig(
    filename='/opt/rpki_nodes/output/bgp_parser.log',  # Output log file path
    level=logging.INFO,  # Log INFO and above (INFO, WARNING, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log format with timestamp, level, and message
)

def parse_timestamp(timestamp_str):
    """
    Convert a timestamp string from the log to a UTC datetime object for ordering.

    Args:
        timestamp_str (str): Timestamp in format 'YYYY/MM/DD HH:MM:SS.ssssss' (e.g., '2025/07/18 19:50:15.215093')

    Returns:
        datetime: Parsed UTC datetime object, or None if the format is invalid
    """
    try:
        # Parse the timestamp string and assign UTC timezone (consistent with Mininet/FRR simulation)
        dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=pytz.UTC)
        return dt
    except ValueError as e:
        # Log an error if the timestamp format is invalid (e.g., malformed log line)
        logging.error(f"Invalid timestamp format: {timestamp_str}, error: {str(e)}")
        return None

def load_peer_as_map(config_file):
    """
    Load the peer-to-AS mapping from a JSON config file.

    Args:
        config_file (str): Path to the JSON file (e.g., '/opt/rpki_nodes/config/peer_as_map.json')

    Returns:
        dict: Mapping of peer IPs to AS numbers (e.g., {'9.0.5.2': 4}), or empty dict if loading fails
    """
    try:
        # Open and read the JSON config file
        with open(config_file, 'r') as f:
            peer_as_map = json.load(f)
            # Validate that all AS numbers are integers
            for ip, as_num in peer_as_map.items():
                if not isinstance(as_num, int):
                    logging.error(f"Invalid AS number for peer {ip}: {as_num}")
                    return {}
            return peer_as_map
    except FileNotFoundError:
        # Log if the config file is missing
        logging.error(f"Config file {config_file} not found")
        return {}
    except Exception as e:
        # Log any other errors during loading
        logging.error(f"Error loading peer-as map: {str(e)}")
        return {}

def parse_bgp_logs(log_files, peer_as_map, start_time=None, end_time=None):
    """
    Parse multiple BGP log files synchronously using a global clock approach.

    This function collects all timestamps from all RPKI nodes' logs, sorts them, and processes
    entries for each unique timestamp across all nodes, ensuring each node processes its own
    log independently but in global timestamp order. The output includes a 'node' field to
    link each announcement to its source RPKI node's log file.

    Args:
        log_files (list): List of paths to BGP log files (e.g., ['/opt/rpki_nodes/logs/rpki1_log.txt', ...])
        peer_as_map (dict): Mapping of peer IPs to AS numbers (e.g., {'9.0.5.2': 4})
        start_time (datetime, optional): Only process entries with UTC timestamps >= start_time
        end_time (datetime, optional): Only process entries with UTC timestamps <= end_time

    Returns:
        dict: Mapping of peer IPs to lists of announcement dictionaries
              (e.g., {'9.0.5.2': [{'as_number': 4, 'type': 'announcement', 'prefix': '10.3.0.0/24', 'node': 'rpki1_log.txt'}, ...]})
    """
    # Initialize a defaultdict to store peer-to-announcement mappings
    peer_prefixes = defaultdict(list)
    
    # Define regular expressions to match FRR BGP log lines from Mininet simulation
    update_re = re.compile(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd UPDATE w/ attr:.*path (\S+)$')  # Matches UPDATE messages with AS path
    prefix_re = re.compile(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast$')  # Matches prefix announcements
    withdraw_re = re.compile(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd UPDATE about (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast -- withdrawn$')  # Matches withdrawals
    duplicate_re = re.compile(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast\.\.\.duplicate ignored$')  # Matches duplicates
    denied_re = re.compile(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d+) BGP: \[\w+-\w+\] (\S+)\(bgpd-R\d+\) rcvd UPDATE about (\d+\.\d+\.\d+\.\d+/\d+) IPv4 unicast -- DENIED')  # Matches denied updates
    
    # Track current UPDATE message's peer and AS path for each node (keyed by log_file)
    current_peers = {}  # Maps log_file to current peer IP
    current_as_paths = {}  # Maps log_file to current AS path
    processed_prefixes = set()  # Track processed (peer_ip, prefix) pairs to avoid duplicates across all nodes
    
    # Collect all lines with their timestamps from all log files
    all_lines = []
    try:
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    # Read all lines from the node's log file
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line:
                            # Parse the timestamp from the line
                            timestamp = parse_timestamp(line[:26])
                            if timestamp and (start_time is None or timestamp >= start_time) and (end_time is None or timestamp <= end_time):
                                all_lines.append((timestamp, line, log_file))
                    logging.info(f"Collected lines from log file: {log_file}")
            except FileNotFoundError:
                # Log if a node's log file is missing and continue
                logging.error(f"Log file {log_file} not found")
                continue
        
        if not all_lines:
            logging.error("No valid log entries found")
            return {}
        
        # Sort all lines by timestamp to create a global clock
        all_lines.sort(key=lambda x: x[0])
        
        # Group lines by timestamp to process synchronously
        for timestamp, group in itertools.groupby(all_lines, key=lambda x: x[0]):
            # Process all lines for this timestamp across all nodes
            for _, line, log_file in group:
                # Check for UPDATE message with AS path
                update_match = update_re.match(line)
                if update_match:
                    # Extract peer IP and AS path from UPDATE message for this node
                    peer_ip = update_match.group(2)
                    current_peers[log_file] = peer_ip
                    current_as_paths[log_file] = update_match.group(3).split()
                    logging.info(f"[{log_file}] Found UPDATE from peer {peer_ip} with AS path {current_as_paths[log_file]} at {timestamp}")
                    continue
                
                # Check for prefix announcement
                prefix_match = prefix_re.match(line)
                if prefix_match and log_file in current_peers:
                    peer_ip = prefix_match.group(2)
                    prefix = prefix_match.group(3)
                    # Verify peer IP matches the current UPDATE and AS path has exactly one hop
                    if peer_ip == current_peers.get(log_file) and len(current_as_paths.get(log_file, [])) == 1:
                        # Check if the AS in the path matches the peer's AS in peer_as_map
                        if peer_as_map.get(peer_ip) == int(current_as_paths[log_file][0]):
                            prefix_key = (peer_ip, prefix)
                            # Add prefix only if not already processed (avoid duplicates across all nodes)
                            if prefix_key not in processed_prefixes:
                                peer_prefixes[peer_ip].append({
                                    "as_number": peer_as_map[peer_ip],
                                    "type": "announcement",
                                    "prefix": prefix,
                                    "node": os.path.basename(log_file)  # Link announcement to source RPKI node
                                })
                                processed_prefixes.add(prefix_key)
                                logging.info(f"[{log_file}] Added prefix {prefix} for peer {peer_ip} (AS {peer_as_map[peer_ip]}) at {timestamp}")
                
                # Check for withdrawal
                withdraw_match = withdraw_re.match(line)
                if withdraw_match:
                    peer_ip = withdraw_match.group(2)
                    prefix = withdraw_match.group(3)
                    prefix_key = (peer_ip, prefix)
                    # Remove prefix if it was previously announced by any node
                    if prefix_key in processed_prefixes:
                        peer_prefixes[peer_ip] = [
                            entry for entry in peer_prefixes[peer_ip]
                            if entry["prefix"] != prefix
                        ]
                        processed_prefixes.remove(prefix_key)
                        logging.info(f"[{log_file}] Removed withdrawn prefix {prefix} for peer {peer_ip} at {timestamp}")
                
                # Skip duplicate announcements
                duplicate_match = duplicate_re.match(line)
                if duplicate_match:
                    logging.debug(f"[{log_file}] Ignored duplicate prefix {duplicate_match.group(3)} from peer {duplicate_match.group(2)} at {timestamp}")
                    continue
                
                # Skip denied updates
                denied_match = denied_re.match(line)
                if denied_match:
                    logging.debug(f"[{log_file}] Ignored denied prefix {denied_match.group(3)} from peer {denied_match.group(2)} at {timestamp}")
                    continue
    
    except Exception as e:
        # Log any unexpected errors during parsing
        logging.error(f"Error parsing log files: {str(e)}")
        return {}
    
    # Convert defaultdict to regular dict for output
    result = dict(peer_prefixes)
    
    # Print the result to console as JSON
    print(json.dumps(result, indent=4))
    
    # Log the final result
    logging.info(f"Parsed prefixes: {json.dumps(result)}")
    
    return result

def main(log_dir, config_file=None, start_time_str=None, end_time_str=None):
    """
    Main function to process BGP logs from a directory and write results to a file.

    Args:
        log_dir (str): Directory containing BGP log files (e.g., '/opt/rpki_nodes/logs')
        config_file (str, optional): Path to JSON file with peer-to-AS mapping
        start_time_str (str, optional): Start timestamp (YYYY/MM/DD HH:MM:SS.ssssss) in UTC
        end_time_str (str, optional): End timestamp (YYYY/MM/DD HH:MM:SS.ssssss) in UTC
    """
    # Log the start of the parsing process
    logging.info(f"Starting BGP log parsing for directory: {log_dir}")
    
    # Load peer-to-AS mapping (default or from config file)
    peer_as_map = {
        '9.0.5.2': 4,
        '9.0.6.2': 10,
        '9.0.7.2': 12
    }
    if config_file:
        peer_as_map = load_peer_as_map(config_file)
        if not peer_as_map:
            logging.error("Failed to load peer-as map, using default")
    
    # Parse start time if provided
    start_time = None
    if start_time_str:
        start_time = parse_timestamp(start_time_str)
        if not start_time:
            logging.error(f"Invalid start time format: {start_time_str}")
            sys.exit(1)
        logging.info(f"Filtering entries after {start_time_str} UTC")
    
    # Parse end time if provided
    end_time = None
    if end_time_str:
        end_time = parse_timestamp(end_time_str)
        if not end_time:
            logging.error(f"Invalid end time format: {end_time_str}")
            sys.exit(1)
        logging.info(f"Filtering entries before {end_time_str} UTC")
    
    # Validate that start_time is not after end_time
    if start_time and end_time and start_time > end_time:
        logging.error(f"Start time {start_time_str} is after end time {end_time_str}")
        sys.exit(1)
    
    # Collect all .txt files from the log directory
    log_files = [
        os.path.join(log_dir, f) for f in os.listdir(log_dir)
        if f.endswith('.txt') and os.path.isfile(os.path.join(log_dir, f))
    ]
    
    # Check if any log files were found
    if not log_files:
        logging.error(f"No .txt log files found in directory {log_dir}")
        sys.exit(1)
    
    # Parse logs and get the result
    result = parse_bgp_logs(log_files, peer_as_map, start_time, end_time)
    
    # Write results to JSON file
    output_file = '/opt/rpki_nodes/output/bgp_prefixes.json'
    try:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
        logging.info(f"Results written to {output_file}")
    except Exception as e:
        logging.error(f"Error writing to output file: {str(e)}")

if __name__ == "__main__":
    # Check command-line arguments: log_dir [config_file] [start_time] [end_time]
    log_dir = "/opt/rpki_nodes/logs"  # Default log directory
    config_file = None
    start_time_str = None
    end_time_str = None
    
    # Parse command-line arguments
    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
    if len(sys.argv) > 2:
        config_file = sys.argv[2]
    if len(sys.argv) > 3:
        start_time_str = sys.argv[3]
    if len(sys.argv) > 4:
        end_time_str = sys.argv[4]
    
    # Verify log directory exists
    if not os.path.isdir(log_dir):
        logging.error(f"Log directory {log_dir} does not exist")
        sys.exit(1)
    
    # Run the main function
    main(log_dir, config_file, start_time_str, end_time_str)