# --------------------------------------------------------------
# File: trust_state.py
# Purpose: Store, update, and read trust scores for (ASN, prefix) pairs
# Used By:
#   - node.py (to check trust before accepting BGP announcements)
#   - trust_engine_instant.py (real-time trust penalties)
#   - trust_engine_periodic.py (monthly behavior analysis)
#   - RPKI node scripts (to directly update trust for confirmed hijacks)
# Calls:
#   - shared_data/trust_state.json (persistent trust store)
#   - shared_data/trust_log.jsonl (append-only audit log)
# --------------------------------------------------------------

import json
import os
from datetime import datetime

STATE_FILE = "shared_data/trust_state.json"
AUDIT_LOG_FILE = "shared_data/trust_log.jsonl"

# --------------------------------------------------------------
# Utility: Load trust state from JSON file
# Returns: dict[(asn, prefix)] = trust_score
# --------------------------------------------------------------
def load_trust_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

# --------------------------------------------------------------
# Utility: Save trust state dict to disk
# --------------------------------------------------------------
def save_trust_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

# --------------------------------------------------------------
# Function: get_trust
# Returns: current trust score for (asn, prefix), default = 70
# --------------------------------------------------------------
def get_trust(asn, prefix):
    state = load_trust_state()
    key = f"{asn}_{prefix}"
    return state.get(key, 70)

# --------------------------------------------------------------
# Function: set_trust
# Updates trust score and writes to both state and audit log
# --------------------------------------------------------------
def set_trust(asn, prefix, new_score, reason=""):
    state = load_trust_state()
    key = f"{asn}_{prefix}"
    state[key] = new_score
    save_trust_state(state)

    log_entry = {
        "asn": asn,
        "prefix": prefix,
        "new_score": new_score,
        "timestamp": datetime.utcnow().isoformat(),
        "reason": reason
    }

    with open(AUDIT_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# --------------------------------------------------------------
# Function: update_trust_score
# Purpose: Lightweight setter for trust score (no logging)
# Used by: RPKI nodes for silent updates (optional)
# --------------------------------------------------------------
def update_trust_score(asn, prefix, new_score):
    state = load_trust_state()
    key = f"{asn}_{prefix}"
    state[key] = new_score
    save_trust_state(state)
