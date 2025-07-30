import json

TRUST_SCORE_FILE = "/home/anik/code/BGP_Announcement_Recorder/nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/trust_state.json"

def get_trust_score(as_number: int) -> int:
    """
    Returns the trust score for a given AS number.
    Returns -1 if not found.
    """
    try:
        with open(TRUST_SCORE_FILE, "r") as f:
            trust_data = json.load(f)
        return trust_data.get(str(as_number), -1)
    except Exception as e:
        print(f"❌ Error reading trust score file: {e}")
        return -1

# Optional CLI usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python trust_score_checker.py <AS_NUMBER>")
        print("Example: python trust_score_checker.py 2")
    else:
        as_number = int(sys.argv[1])
        score = get_trust_score(as_number)
        if score >= 0:
            print(f"✅ Trust score for AS{as_number}: {score}")
        else:
            print(f"❌ No trust score found for AS{as_number}")
