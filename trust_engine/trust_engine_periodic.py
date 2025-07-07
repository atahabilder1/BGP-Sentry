# --------------------------------------------------------------
# File: trust_engine_periodic.py
# Purpose: Adjust trust scores monthly based on observed behavior
# Used By: Admin or Cron job (e.g., once per month)
# Calls:
#   - blockchain.py to read full chain history
#   - trust_state.py to read and write trust scores
# --------------------------------------------------------------

from blockchain import blockchain
from blockchain import trust_state
from collections import defaultdict
from datetime import datetime

# Configurable parameters
REWARD_GOOD_BEHAVIOR = 5
PENALIZE_FLAPPING = -10
MIN_FLAP_COUNT = 3

# --------------------------------------------------------------
# Function: analyze_behavior
# Scans the blockchain for each (asn, prefix) and summarizes stats
# --------------------------------------------------------------
def analyze_behavior():
    chain = blockchain.load_chain()
    history = defaultdict(lambda: {"announce": 0, "withdraw": 0})

    for block in chain:
        for ann in block["announcements"]:
            asn = ann["asn"]
            prefix = ann["prefix"]
            ann_type = ann.get("type", "announce")
            key = f"{asn}_{prefix}"
            if ann_type == "announce":
                history[key]["announce"] += 1
            elif ann_type == "withdraw":
                history[key]["withdraw"] += 1

    return history

# --------------------------------------------------------------
# Function: apply_trust_adjustments
# Evaluates trends and adjusts trust state accordingly
# --------------------------------------------------------------
def apply_trust_adjustments():
    print(f"📊 Running periodic trust evaluation at {datetime.utcnow().isoformat()}")
    behavior_summary = analyze_behavior()

    for key, stats in behavior_summary.items():
        asn, prefix = key.split("_", 1)
        asn = int(asn)
        current_score = trust_state.get_trust(asn, prefix)

        # Trust logic based on observed behavior
        if stats["withdraw"] >= MIN_FLAP_COUNT:
            new_score = max(0, current_score + PENALIZE_FLAPPING)
            reason = "prefix flapping detected"
        elif stats["announce"] > 5 and stats["withdraw"] == 0:
            new_score = min(100, current_score + REWARD_GOOD_BEHAVIOR)
            reason = "consistent good behavior"
        else:
            continue  # No change

        trust_state.set_trust(asn, prefix, new_score, reason=reason)
        print(f"✅ Trust score updated for {asn} {prefix}: {current_score} → {new_score} ({reason})")

# Entry point
if __name__ == "__main__":
    apply_trust_adjustments()
