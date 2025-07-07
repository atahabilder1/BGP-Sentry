# --------------------------------------------------------------
# File: rpki_65001.py
# Purpose: Logic for RPKI-enabled validator node (ASN 65001)
# Used By:
#   - Runs as a validator node in the simulation
#   - Interacts with Blockchain A and Trust Engine
# Calls:
#   - bgp_collector.collect_bgp_announcements()
#   - blockchain.add_block()
#   - blockchain.get_last_block()
#   - trust_state.get_trust_score(), update_trust_score()
#   - staking_interface.get_stake_amount()
# --------------------------------------------------------------

import json
import time
from blockchain.block import Block
from blockchain import blockchain
from bgp_feed.bgp_collector import collect_bgp_announcements
from blockchain.trust_state import get_trust_score, update_trust_score
from blockchain.staking_interface import get_stake_amount
from utils import sign_data_placeholder

# Load configuration
with open("nodes/rpki_nodes/config_65001.json", "r") as f:
    config = json.load(f)

MY_ASN = config["my_asn"]
VALIDATOR_LIST = config.get("validators", {"65001": True, "65002": True})
TRUST_THRESHOLD = 70
STAKE_BOOST_THRESHOLD = 50
STAKE_REQUIRED = 100  # Minimum USDC
STAKE_BOOST = 20

def is_my_turn(block_height):
    validators = sorted(list(VALIDATOR_LIST.keys()))
    proposer_index = block_height % len(validators)
    return int(validators[proposer_index]) == MY_ASN

def verify_and_accept(announcement):
    asn = announcement.asn
    prefix = announcement.prefix
    score = get_trust_score(asn, prefix)

    # If score is high enough, accept
    if score >= TRUST_THRESHOLD:
        return True

    # If not, check for stake to give temporary boost
    stake = get_stake_amount(asn)
    if score >= STAKE_BOOST_THRESHOLD and stake >= STAKE_REQUIRED:
        return True

    return False

def main():
    print(f"✅ Starting RPKI node for ASN {MY_ASN}")
    while True:
        height = blockchain.get_chain_length()
        last_block = blockchain.get_last_block()
        previous_hash = last_block["hash"] if last_block else "0" * 64

        if is_my_turn(height):
            print(f"🔄 ASN {MY_ASN} proposing block {height}")
            announcements = collect_bgp_announcements()
            accepted = []

            for ann in announcements:
                if verify_and_accept(ann):
                    ann.endorsed_by = MY_ASN
                    ann.signature = sign_data_placeholder(json.dumps(ann.to_dict()))
                    accepted.append(ann)
                else:
                    print(f"❌ Announcement rejected from ASN {ann.asn} for prefix {ann.prefix}")

            if accepted:
                block = Block(
                    index=height,
                    previous_hash=previous_hash,
                    proposer=MY_ASN,
                    announcements=accepted
                )
                blockchain.add_block(block)
                print(f"📦 Block {height} added with {len(accepted)} announcements")
            else:
                print("⚠️ No valid announcements to add.")
        else:
            print(f"⏳ Not my turn to propose. Waiting...")

        time.sleep(10)

if __name__ == "__main__":
    main()
