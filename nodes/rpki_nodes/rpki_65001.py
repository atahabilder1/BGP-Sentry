# --------------------------------------------------------------
# File: rpki_65001.py
# Purpose: RPKI-enabled node for ASN 65001
# - Reads shared BGP stream from shared_data/bgp_stream.jsonl
# - Verifies trust score and stake for each announcement
# - Signs and logs trusted announcements into Blockchain A
# - Uses keys/private/private_key_65001.pem for signing
# - Records results in shared_data/consolidated_log.jsonl
# - Does NOT delete any processed announcements from the stream
# - Placeholder for additional BGP validation (e.g., path validation)
# --------------------------------------------------------------

import json
import os
import time
import hashlib
import logging
import fcntl
from datetime import datetime
import sys

# Add project root (two steps up) to sys.path to locate blockchain folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from blockchain.block import Block
    from blockchain.blockchain import add_block, get_chain_length
    from blockchain.trust_state import get_trust
    from blockchain.staking_interface import check_stake_amount
except ImportError as e:
    print(f"[!] Failed to import blockchain modules: {e}")
    sys.exit(1)

# --------------------------------------------------------------
# Setup Logging
# --------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("rpki_65001.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
# Setup Paths
# --------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '../..'))
CONFIG_FILE = os.path.join(BASE_DIR, "config_65001.json")
PRIVATE_KEY_FILE = os.path.join(BASE_DIR, "keys/private/private_key_65001.pem")
INPUT_STREAM = os.path.join(PROJECT_ROOT, "shared_data/bgp_stream.jsonl")
CONSOLIDATED_LOG = os.path.join(PROJECT_ROOT, "shared_data/consolidated_log.jsonl")

# --------------------------------------------------------------
# Load Configuration
# --------------------------------------------------------------
try:
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    MY_ASN = config.get("my_asn", "65001")
    TRUST_THRESHOLD = float(config.get("trust_threshold", 0.8))
except FileNotFoundError:
    logger.error(f"Configuration file not found: {CONFIG_FILE}")
    sys.exit(1)
except json.JSONDecodeError:
    logger.error(f"Invalid JSON in configuration file: {CONFIG_FILE}")
    sys.exit(1)
except KeyError as e:
    logger.error(f"Missing key in configuration: {e}")
    sys.exit(1)

# --------------------------------------------------------------
# Function: sign_announcement
# Simulates digital signature using SHA256 over message + private key
# --------------------------------------------------------------
def sign_announcement(data_dict):
    try:
        with open(PRIVATE_KEY_FILE, "r") as f:
            private_key = f.read().strip()
        message = json.dumps(data_dict, sort_keys=True)
        return hashlib.sha256((message + private_key).encode()).hexdigest()
    except FileNotFoundError:
        logger.error(f"Private key file not found: {PRIVATE_KEY_FILE}")
        raise
    except Exception as e:
        logger.error(f"Error signing announcement: {e}")
        raise

# --------------------------------------------------------------
# Function: placeholder_additional_checks
# Future: Path validation, prefix legitimacy, etc.
# --------------------------------------------------------------
def placeholder_additional_checks(announcement):
    # Placeholder for extended validation logic
    return True  # Accept all for now

# --------------------------------------------------------------
# Function: process_announcement
# Logs trusted BGP announcements to Blockchain A and consolidated log
# --------------------------------------------------------------
def process_announcement(announcement):
    try:
        asn = announcement["asn"]
        prefix = announcement["prefix"]
        wallet = announcement.get("wallet_address", "N/A")
        logger.debug(f"Processing announcement: {announcement}")
        trust_score = get_trust(asn, prefix)
        stake_amount = check_stake_amount(wallet) if wallet != "N/A" else 0

        status = "SKIPPED"
        reason = ""

        if trust_score >= TRUST_THRESHOLD and placeholder_additional_checks(announcement):
            signed_data = {
                "data": announcement,
                "signed_by": MY_ASN,
                "signature": sign_announcement(announcement)
            }
            block = Block(
                index=get_chain_length(),
                data=signed_data,
                timestamp=int(time.time())
            )
            add_block(block)
            status = "ACCEPTED"
        else:
            reason = f"Trust score {trust_score} < threshold {TRUST_THRESHOLD} or failed additional checks"

        log_entry = {
            "timestamp": str(datetime.now()),
            "asn": asn,
            "prefix": prefix,
            "wallet": wallet,
            "trust_score": trust_score,
            "stake_amount": stake_amount,
            "status": status,
            "reason": reason,
            "as_path": announcement.get("as_path", []),
            "next_hop": announcement.get("next_hop", "N/A"),
            "type": announcement.get("type", "N/A")
        }
        with open(CONSOLIDATED_LOG, "a") as log_file:
            log_file.write(json.dumps(log_entry) + "\n")

        logger.info(f"{status}: {asn} {prefix} (Trust={trust_score}, Stake={stake_amount})")
    except KeyError as e:
        logger.error(f"Missing key in announcement: {e}")
        raise
    except Exception as e:
        logger.error(f"Error processing announcement: {e}")
        raise

# --------------------------------------------------------------
# Main loop
# --------------------------------------------------------------
def main():
    logger.info(f"🔐 RPKI Node {MY_ASN} started.")
    while True:
        if os.path.exists(INPUT_STREAM):
            try:
                with open(INPUT_STREAM, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        announcement = json.loads(line)
                        process_announcement(announcement)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in line: {line}")
                    except Exception as e:
                        logger.error(f"Error processing announcement: {e}")
            except Exception as e:
                logger.error(f"Error reading input stream {INPUT_STREAM}: {e}")
        else:
            logger.warning(f"Input stream file not found: {INPUT_STREAM}")
        time.sleep(5)

if __name__ == "__main__":
    main()
