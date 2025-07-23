# rpki_as_03.py
#
# Purpose:
#   This script implements an RPKI-enabled node for Autonomous System Number (ASN) 65003.
#   It reads BGP announcements from R3-bgpd.log, validates their trust scores using RPKI data,
#   signs them with a private key, and creates blockchain proposals for trustworthy announcements.
#   The script is part of the BGP_Announcement_Recorder project and integrates with blockchain
#   modules for decentralized trust management.
#
# Key Functionality:
#   - Loads configuration from config_as_03.json in the as03 directory and a private key for signing.
#   - Reads and parses BGP announcements from R3-bgpd.log in the as03 directory.
#   - Validates announcements based on a trust score threshold.
#   - Signs valid announcements and creates blockchain proposals (blocks).
#   - Processes the log file once and exits, without continuous monitoring.
#   - Outputs step completion messages and logs debug information only in debug mode.
#
# Dependencies:
#   - Blockchain modules: block.py, blockchain.py, trust_state.py (in blockchain directory).
#   - External libraries: os, sys, json, time, hashlib, datetime, re (for log parsing), logging (for debug output).
#   - Files: as03/config_as_03.json, as_03_private_key.pem, as03/R3-bgpd.log.
#
# Functions:
#   - parse_bgpd_log(log_file): Parses R3-bgpd.log to extract BGP announcements.
#   - sign_announcement(data_dict): Generates a SHA-256 hash signature for an announcement.
#   - process_announcement(announcement): Validates and creates a blockchain proposal for an announcement.
#   - main(): Reads the log file, processes announcements, and logs proposals to the blockchain.
#
# Notes:
#   - Debug mode is controlled by the DEBUG constant or config_as_03.json's 'debug' field.
#   - Step completion messages are logged with logging.info for visibility in all modes.
#   - Debug messages (e.g., proposal details, errors) use logging.debug and appear only in debug mode.

import os
import sys
import json
import time
import hashlib
import re
import logging
from datetime import datetime

# === Step 1: Configure logging ===
# Purpose: Sets up logging for step completion (info) and debug messages (debug).
# Info messages (e.g., step completion) always output; debug messages require DEBUG=True.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpki_as_03.log"))
    ]
)
logger = logging.getLogger(__name__)

# Debug mode control (can be overridden by config_as_03.json).
DEBUG = True

# === Step 2: Add parent folder (rpki_nodes) to sys.path ===
# Purpose: Allows importing blockchain modules from the blockchain directory.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
logger.info("Step 2 completed: Added parent folder to sys.path.")

# === Step 3: Import blockchain modules ===
from blockchain.block import Block
from blockchain.blockchain import add_block, get_chain_length
from blockchain.trust_state import get_trust, set_trust
logger.info("Step 3 completed: Imported blockchain modules.")

# === Step 4: Set up file paths based on folder name (e.g., 'as03') ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))         # e.g., .../rpki_nodes/as03
AS_FOLDER = os.path.basename(SCRIPT_DIR)                        # → 'as03'
AS_NUM = AS_FOLDER.replace("as", "")                            # → '03'
ASN = f"650{AS_NUM}"                                           # → '65003'
BASE_DIR = os.path.dirname(SCRIPT_DIR)                          # → .../rpki_nodes

# Construct paths for configuration, private key, and BGP log file.
CONFIG_FILE = os.path.join(SCRIPT_DIR, f"config_as_{AS_NUM}.json")  # Inside as03 directory
PRIVATE_KEY_FILE = os.path.join(BASE_DIR, f"as_{AS_NUM}_private_key.pem")  # Matches as_03_private_key.pem
BGP_LOG_FILE = os.path.join(SCRIPT_DIR, "R3-bgpd.log")         # Path to R3-bgpd.log
logger.info(f"Step 4 completed: Set up file paths (config: {CONFIG_FILE}, key: {PRIVATE_KEY_FILE}, log: {BGP_LOG_FILE}).")

# === Step 5: Load configuration ===
# Purpose: Reads config_as_03.json to get ASN, trust threshold, and optional debug flag.
try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    MY_ASN = config["my_asn"]
    TRUST_THRESHOLD = config["trust_threshold"]
    # Check for debug flag in config, if present.
    DEBUG = config.get("debug", DEBUG)
    if not DEBUG:
        logger.setLevel(logging.INFO)  # Disable debug logs if DEBUG=False
    logger.info(f"Step 5 completed: Loaded configuration (ASN: {MY_ASN}, Trust Threshold: {TRUST_THRESHOLD}, Debug: {DEBUG}).")
except FileNotFoundError:
    logger.error(f"Step 5 failed: {CONFIG_FILE} not found.")
    sys.exit(1)
except KeyError as e:
    logger.error(f"Step 5 failed: Missing key {e} in {CONFIG_FILE}.")
    sys.exit(1)

# === Step 6: Define function to parse BGP log ===
# Function: parse_bgpd_log
# Purpose: Parses R3-bgpd.log to extract BGP announcements (ASN, prefix, timestamp).
# Inputs:
#   - log_file: Path to R3-bgpd.log.
# Outputs:
#   - List of dictionaries, each containing announcement details (e.g., {"asn": "65001", "prefix": "192.0.2.0/24", "timestamp": 1629876543}).
def parse_bgpd_log(log_file):
    announcements = []
    # Regex to match BGP UPDATE messages with ASN and prefix.
    pattern = re.compile(r'announce\s+(\S+)\s+from\s+AS(\d+)', re.IGNORECASE)
    
    try:
        with open(log_file, "r") as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    prefix = match.group(1)  # e.g., 192.0.2.0/24
                    asn = match.group(2)    # e.g., 65001
                    # Extract timestamp or use current time.
                    timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line)
                    timestamp = int(time.time()) if not timestamp_match else int(datetime.strptime(timestamp_match.group(0), "%Y-%m-%d %H:%M:%S").timestamp())
                    announcements.append({
                        "asn": asn,
                        "prefix": prefix,
                        "timestamp": timestamp
                    })
                    logger.debug(f"Parsed announcement: ASN={asn}, Prefix={prefix}, Timestamp={timestamp}")
        logger.info(f"Step 6 completed: Parsed {len(announcements)} announcements from {log_file}.")
    except FileNotFoundError:
        logger.error(f"Step 6 failed: {log_file} not found.")
    except Exception as e:
        logger.error(f"Step 6 failed: Error parsing log: {e}")
    
    return announcements

# === Step 7: Define function to sign announcements ===
# Function: sign_announcement
# Purpose: Generates a SHA-256 hash signature for a BGP announcement using the private key.
# Inputs:
#   - data_dict: Dictionary containing announcement data (e.g., {"asn": "65001", "prefix": "192.0.2.0/24"}).
# Outputs:
#   - String: Hexadecimal SHA-256 hash of the announcement data combined with the private key.
def sign_announcement(data_dict):
    try:
        with open(PRIVATE_KEY_FILE, "r") as f:
            private_key = f.read().strip()
        message = json.dumps(data_dict, sort_keys=True)
        signature = hashlib.sha256((message + private_key).encode()).hexdigest()
        logger.debug(f"Generated signature for announcement: {signature}")
        logger.info("Step 7 completed: Signed announcement.")
        return signature
    except FileNotFoundError:
        logger.error(f"Step 7 failed: {PRIVATE_KEY_FILE} not found.")
        return None
    except Exception as e:
        logger.error(f"Step 7 failed: Error signing announcement: {e}")
        return None

# === Step 8: Define function to process announcements and create proposals ===
# Function: process_announcement
# Purpose: Validates a BGP announcement's trust score and creates a signed blockchain proposal if trustworthy.
# Inputs:
#   - announcement: Dictionary with announcement details (e.g., {"asn": "65001", "prefix": "192.0.2.0/24"}).
# Outputs:
#   - None: Logs the proposal to the blockchain if valid; logs status.
def process_announcement(announcement):
    asn = announcement["asn"]
    prefix = announcement["prefix"]
    score = get_trust(asn, prefix)
    logger.debug(f"Evaluated trust score for {asn}-{prefix}: {score}")

    if score >= TRUST_THRESHOLD:
        # Create a signed proposal for the blockchain.
        proposal = {
            "data": announcement,
            "signed_by": MY_ASN,
            "signature": sign_announcement(announcement)
        }
        if proposal["signature"] is None:
            logger.error("Step 8 failed: Skipping proposal due to signing error.")
            return
        block = Block(
            index=get_chain_length(),
            data=proposal,
            timestamp=int(time.time())
        )
        add_block(block)
        logger.debug(f"Created proposal: {proposal}")
        logger.info(f"Step 8 completed: Proposal created and logged for {asn}-{prefix}.")
    else:
        logger.debug(f"Skipped proposal: Trust score {score} below threshold {TRUST_THRESHOLD} for {asn}-{prefix}")
        logger.info(f"Step 8 completed: Skipped proposal for {asn}-{prefix} due to low trust score.")

# === Step 9: Define main function ===
# Function: main
# Purpose: Reads R3-bgpd.log, extracts announcements, and processes them to create blockchain proposals.
# Inputs:
#   - None
# Outputs:
#   - None: Processes all announcements and exits.
def main():
    logger.info(f"🔐 RPKI Node {MY_ASN} started.")
    
    # Read and parse R3-bgpd.log.
    if os.path.exists(BGP_LOG_FILE):
        announcements = parse_bgpd_log(BGP_LOG_FILE)
        logger.info(f"Step 9 completed: Found {len(announcements)} announcements to process.")
        
        # Process each announcement.
        for announcement in announcements:
            try:
                process_announcement(announcement)
            except Exception as e:
                logger.error(f"Step 9 failed: Error processing announcement: {e}")
    else:
        logger.error(f"Step 9 failed: {BGP_LOG_FILE} not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()