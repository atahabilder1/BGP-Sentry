"""
Purpose:
    Parses bgpd.json and trust_state.json from the shared_data directory to extract
    BGP announcement fields (sender_asn, ip_prefix, timestamp, trust_score, prefix_length).
    Prompts the user for an announcement index and returns the extracted fields as a dictionary.

Calls:
    - None (standalone module, called by main.py or other scripts).

Location:
    - File: Located in blockchain_node directory (e.g., blockchain_node/parse_bgp.py).
    - shared_data: Located three levels up from this script (../../../shared_data),
      containing bgpd.json and trust_state.json.

Notes:
    - Logs all operations to parse_bgp.log and console for debugging.
    - Validates JSON structure and user input.
    - Returns None on error, otherwise a dictionary with parsed fields.
"""

from pathlib import Path
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("parse_bgp.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_bgp_announcement():
    """
    Reads and parses bgpd.json from the 'shared_data' subdirectory three levels up,
    prompts the user for an announcement index, extracts sender_asn, ip_prefix,
    timestamp, and trust_score for the selected announcement, and returns them.
    Returns: dict with sender_asn, ip_prefix, timestamp, trust_score, prefix_length.
    """
    logger.info("Starting parse_bgp_announcement")
    
    # Get the directory of the current script
    current_dir = Path(__file__).parent
    logger.debug("Current script directory: %s", current_dir)

    # Construct paths, going three levels up to shared_data
    shared_data_dir = current_dir / ".." / ".." / ".." / "shared_data"
    bgpd_path = shared_data_dir / "bgpd.json"
    trust_state_path = shared_data_dir / "trust_state.json"

    # Resolve to absolute paths for verification
    bgpd_path = bgpd_path.resolve()
    trust_state_path = trust_state_path.resolve()
    logger.debug("Resolved shared_data directory: %s", shared_data_dir.resolve())
    logger.debug("Full path to bgpd.json: %s", bgpd_path)
    logger.debug("Full path to trust_state.json: %s", trust_state_path)

    try:
        # Check if input files exist
        logger.info("Checking for input files")
        logger.debug("Checking if bgpd.json exists: %s", bgpd_path.exists())
        logger.debug("Checking if trust_state.json exists: %s", trust_state_path.exists())
        if not bgpd_path.exists():
            logger.error("bgpd.json not found at %s", bgpd_path)
            print(f"Error: bgpd.json not found at {bgpd_path}")
            return None
        if not trust_state_path.exists():
            logger.error("trust_state.json not found at %s", trust_state_path)
            print(f"Error: trust_state.json not found at {trust_state_path}")
            return None
        logger.info("Input files found")

        # Read and parse bgpd.json
        logger.info("Reading bgpd.json")
        with open(bgpd_path, 'r') as file:
            bgpd_data = json.load(file)
        logger.debug("bgpd.json content: %s", json.dumps(bgpd_data, indent=2))

        # Read and parse trust_state.json
        logger.info("Reading trust_state.json")
        with open(trust_state_path, 'r') as file:
            trust_scores = json.load(file)
        logger.debug("trust_state.json content: %s", json.dumps(trust_scores, indent=2))

        # Check if bgp_announcements exists and is a list
        logger.info("Validating bgpd.json structure")
        if 'bgp_announcements' not in bgpd_data or not isinstance(bgpd_data['bgp_announcements'], list):
            logger.error("'bgp_announcements' key missing or not a list in bgpd.json: %s", 
                         json.dumps(bgpd_data, indent=2))
            print("Error: 'bgp_announcements' key missing or not a list in bgpd.json")
            return None

        # Get the total number of announcements
        announcements = bgpd_data['bgp_announcements']
        logger.debug("Number of announcements: %d", len(announcements))
        if not announcements:
            logger.error("No announcements found in bgpd.json")
            print("Error: No announcements found in bgpd.json")
            return None

        # Prompt user for announcement index (1-based)
        logger.info("Prompting user for announcement index")
        while True:
            try:
                index = int(input(f"Enter the announcement number to process (1-{len(announcements)}): "))
                logger.debug("User input index: %d", index)
                if 1 <= index <= len(announcements):
                    break
                logger.warning("Invalid index %d, must be between 1 and %d", index, len(announcements))
                print(f"Please enter a number between 1 and {len(announcements)}")
            except ValueError as e:
                logger.warning("Invalid input for index: %s", str(e))
                print("Please enter a valid number")

        # Adjust to 0-based index for list access
        selected_announcement = announcements[index - 1]
        logger.debug("Selected announcement: %s", json.dumps(selected_announcement, indent=2))

        # Extract fields
        sender_asn = selected_announcement.get('sender_asn')
        prefixes = selected_announcement.get('announced_prefixes', [])
        timestamp = selected_announcement.get('timestamp')
        logger.debug("Extracted fields: sender_asn=%s, prefixes=%s, timestamp=%s", 
                     sender_asn, prefixes, timestamp)

        # Validate required fields
        if sender_asn is None or timestamp is None:
            logger.error("Missing sender_asn or timestamp in announcement %d: %s", 
                         index, json.dumps(selected_announcement, indent=2))
            print(f"Error: Missing sender_asn or timestamp in announcement {index}")
            return None
        if not prefixes:
            logger.error("No prefixes in announcement %d: %s", 
                         index, json.dumps(selected_announcement, indent=2))
            print(f"Error: No prefixes in announcement {index}")
            return None

        # Extract the first prefix
        ip_prefix = prefixes[0]
        logger.debug("Selected IP prefix: %s", ip_prefix)
        try:
            prefix_length = int(ip_prefix.split('/')[-1])
            logger.debug("Extracted prefix length: %d", prefix_length)
        except (IndexError, ValueError) as e:
            logger.error("Invalid prefix format in announcement %d: %s, error: %s", 
                         index, ip_prefix, str(e))
            print(f"Error: Invalid prefix format in announcement {index}: {ip_prefix}")
            return None

        # Get trust score for sender_asn (convert to string for JSON key)
        trust_score = trust_scores.get(str(sender_asn), "N/A")
        logger.debug("Trust score for sender_asn %s: %s", sender_asn, trust_score)
        if trust_score == "N/A":
            logger.warning("No trust score found for sender_asn %s in announcement %d", 
                           sender_asn, index)
            print(f"Warning: No trust score found for sender_asn {sender_asn} in announcement {index}")

        # Log and print extracted values
        logger.info("Parsed announcement %d successfully", index)
        print(f"Announcement {index}:")
        print(f"  Number Prefix (sender_asn): {sender_asn}")
        print(f"  IP Prefix: {ip_prefix}")
        print(f"  Length (from prefix): {prefix_length}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Trust Score: {trust_score}")

        result = {
            "sender_asn": sender_asn,
            "ip_prefix": ip_prefix,
            "timestamp": timestamp,
            "trust_score": trust_score,
            "prefix_length": prefix_length
        }
        logger.debug("Returning parsed result: %s", json.dumps(result, indent=2))
        return result

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON format: %s, document: %s", str(e), e.doc)
        print(f"Error: Invalid JSON format in {e.doc}")
        return None
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        print(f"Error: An unexpected error occurred: {str(e)}")
        return None

if __name__ == "__main__":
    logger.info("Starting parse_bgp.py")
    result = parse_bgp_announcement()
    logger.info("Finished parse_bgp.py")
    if result:
        logger.debug("Parsed data: %s", json.dumps(result, indent=2))
    else:
        logger.error("Parsing failed, no data returned")