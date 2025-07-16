# --------------------------------------------------------------
# File: node.py
# Purpose: Main RPKI node logic — block proposer and validator
# Used By: RPKI AS nodes to read announcements and write to Blockchain A
# Calls:
#   - bgp_collector.py for reading BGP stream
#   - blockchain.py to append blocks
#   - trust_state.py to validate trust score for each announcement
#   - staking_interface.py to query Blockchain B (optional)
#   - block.py to structure blocks and announcements
# Config:
#   - Reads ASN from config_<asn>.json inside rpki_nodes/
# --------------------------------------------------------------

import json
import os
import time
from blockchain.block import Block
from blockchain import blockchain, trust_state
from blockchain.staking_interface import check_stake_amount
from bgp_feed.bgp_collector import collect_bgp_announcements

# Config constants
TRUST_THRESHOLD = 70
MINIMUM_STAKE_AMOUNT = 100  # USDC
TRUST_BOOST_FOR_STAKE = 20
MAX_ANNOUNCEMENTS = 5

# --------------------------------------------------------------
# Function: load_config
# Reads local ASN and validator list from config file
# --------------------------------------------------------------
def load_config(asn):
    config_path = f"nodes/rpki_nodes/config_{asn}.json"
    with open(config_path, "r") as f:
        return json.load(f)

# --------------------------------------------------------------
# Function: compute_effective_trust
# Uses trust score + stake amount to decide acceptance
# --------------------------------------------------------------
def compute_effective_trust(asn, prefix, wallet_address):
    score = trust_state.get_trust(asn, prefix)

    if score >= TRUST_THRESHOLD:
        return score

    # Check stake from Blockchain B
    if wallet_address:
        staked_amount = check_stake_amount(wallet_address)
        if staked_amount >= MINIMUM_STAKE_AMOUNT:
            return min(score + TRUST_BOOST_FOR_STAKE, 100)
    return score

# --------------------------------------------------------------
# Function: filter_acceptable_announcements
# Verifies if each announcement should be accepted
# --------------------------------------------------------------
def validate_announcements(announcements):
    valid = []
    for ann in announcements:
        eff_score = compute_effective_trust(ann.asn, ann.prefix, ann.wallet_address)

        if eff_score >= TRUST_THRESHOLD:
            print(f"✅ Accepted {ann.prefix} from ASN {ann.asn} (Effective Trust: {eff_score})")
            valid.append(ann)
        else:
            print(f"❌ Rejected {ann.prefix} from ASN {ann.asn} (Effective Trust: {eff_score})")
    return valid

# --------------------------------------------------------------
# Function: run_node
# Main loop: checks turn, collects announcements, proposes blocks
# --------------------------------------------------------------
def run_node(asn):
    config = load_config(asn)
    validators = config["validators"]
    my_asn = config["my_asn"]

    while True:
        block_height = blockchain.get_chain_length()
        last_block = blockchain.get_last_block()
        previous_hash = last_block["hash"] if last_block else "0" * 64

        # Round-robin proposer check
        validator_list = list(validators.keys())
        proposer_index = block_height % len(validator_list)
        is_my_turn = validator_list[proposer_index] == str(my_asn)

        if is_my_turn:
            print(f"🔄 It's ASN {my_asn}'s turn to propose block {block_height}")
            all_announcements = collect_bgp_announcements(MAX_ANNOUNCEMENTS)
            accepted_announcements = validate_announcements(all_announcements)

            if accepted_announcements:
                block = Block(
                    index=block_height,
                    previous_hash=previous_hash,
                    proposer=my_asn,
                    announcements=accepted_announcements
                )
                blockchain.add_block(block)
                print(f"📦 Block {block_height} added to chain by ASN {my_asn}")
            else:
                print("⚠️ No valid announcements. Block skipped.")
        else:
            print(f"⏳ Waiting... Block {block_height} proposer is ASN {validator_list[proposer_index]}")

        time.sleep(10)

# --------------------------------------------------------------
# Entry point
# Pass ASN as argument to run the respective RPKI node
# --------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python node.py <asn>")
        exit(1)

    asn = int(sys.argv[1])
    run_node(asn)
