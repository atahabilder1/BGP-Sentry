"""
blockchain_module.py

Purpose:
This module reads a 'bgpd.json' file from a 'shared_data' subdirectory located
three levels up from the script's directory (e.g., at the root of BGP_Announcement_Recorder),
parses its contents, and allows the user to select a single BGP announcement to process.
For the chosen announcement, it extracts four fields: sender_asn (number prefix),
announced_prefixes (list of prefixes), length (extracted from the first prefix's CIDR
notation, e.g., 24 from 192.168.0.0/24), and timestamp. It also retrieves a trust score
for the sender_asn from 'trust_state.json' in the 'shared_data' subdirectory and prints
all values.

Input:
- Expects a 'bgpd.json' file in the 'shared_data' subdirectory three levels up.
- The JSON file is expected to contain a 'bgp_announcements' list, where each
  announcement has 'sender_asn', 'announced_prefixes' (a list), and 'timestamp'.
- Expects a 'trust_state.json' file in the 'shared_data' subdirectory three levels up,
  mapping sender_asn (as strings) to trust scores (e.g., {"2": 85.5}).
- User input: The index of the announcement to process (1-based).

Functions:
- parse_bgpd_json(): Locates and parses the bgpd.json file, prompts for an announcement
  index, retrieves the trust score from trust_state.json, and prints the details
  of the selected announcement.
"""

from pathlib import Path
import json

def parse_bgpd_json():
    """
    Reads and parses bgpd.json from the 'shared_data' subdirectory three levels up,
    prompts the user for an announcement index, extracts sender_asn, announced_prefixes,
    length (from the first prefix's CIDR notation), and timestamp for the selected
    announcement. Retrieves the trust score for the sender_asn from trust_state.json
    and prints all values.
    """
    # Get the directory of the current script
    current_dir = Path(__file__).parent

    # Construct paths, going three levels up to shared_data
    shared_data_dir = current_dir / ".." / ".." / ".." / "shared_data"
    bgpd_path = current_dir / "bgpd.json"
    trust_state_path = shared_data_dir / "trust_state.json"

    # Resolve to absolute paths for verification
    bgpd_path = bgpd_path.resolve()
    trust_state_path = trust_state_path.resolve()

    # Debug prints to show resolved paths
    print(f"Script directory: {current_dir}")
    print(f"Resolved shared_data directory: {shared_data_dir.resolve()}")
    print(f"Full path to bgpd.json: {bgpd_path}")
    print(f"Full path to trust_state.json: {trust_state_path}")

    try:
        # Check if files exist
        if not bgpd_path.exists():
            print(f"Error: bgpd.json not found at {bgpd_path}")
            return
        if not trust_state_path.exists():
            print(f"Error: trust_state.json not found at {trust_state_path}")
            return

        # Read and parse bgpd.json
        with open(bgpd_path, 'r') as file:
            bgpd_data = json.load(file)

        # Read and parse trust_state.json
        with open(trust_state_path, 'r') as file:
            trust_scores = json.load(file)

        # Check if bgp_announcements exists and is a list
        if 'bgp_announcements' not in bgpd_data or not isinstance(bgpd_data['bgp_announcements'], list):
            print("Error: 'bgp_announcements' key missing or not a list in bgpd.json")
            return

        # Get the total number of announcements
        announcements = bgpd_data['bgp_announcements']
        if not announcements:
            print("Error: No announcements found in bgpd.json")
            return

        # Prompt user for announcement index (1-based)
        while True:
            try:
                index = int(input(f"Enter the announcement number to process (1-{len(announcements)}): "))
                if 1 <= index <= len(announcements):
                    break
                print(f"Please enter a number between 1 and {len(announcements)}")
            except ValueError:
                print("Please enter a valid number")

        # Adjust to 0-based index for list access
        selected_announcement = announcements[index - 1]

        # Extract fields
        sender_asn = selected_announcement.get('sender_asn')
        prefixes = selected_announcement.get('announced_prefixes', [])
        timestamp = selected_announcement.get('timestamp')

        # Validate required fields
        if sender_asn is None or timestamp is None:
            print(f"Error: Missing sender_asn or timestamp in announcement {index}")
            return
        if not prefixes:
            print(f"Error: No prefixes in announcement {index}")
            return

        # Extract length from the first prefix (e.g., 24 from 192.168.0.0/24)
        first_prefix = prefixes[0]
        try:
            prefix_length = int(first_prefix.split('/')[-1])
        except (IndexError, ValueError):
            print(f"Error: Invalid prefix format in announcement {index}: {first_prefix}")
            return

        # Get trust score for sender_asn (convert to string for JSON key)
        trust_score = trust_scores.get(str(sender_asn), "N/A")
        if trust_score == "N/A":
            print(f"Warning: No trust score found for sender_asn {sender_asn} in announcement {index}")

        # Print extracted values for the selected announcement
        print(f"Announcement {index}:")
        print(f"  Number Prefix (sender_asn): {sender_asn}")
        print(f"  Announced Prefixes: {prefixes}")
        print(f"  Length (from first prefix): {prefix_length}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Trust Score: {trust_score}")

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {e.doc}")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    parse_bgpd_json()