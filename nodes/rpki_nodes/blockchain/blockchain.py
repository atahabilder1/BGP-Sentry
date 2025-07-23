# --------------------------------------------------------------
# File: blockchain.py
# Purpose: Handles local Blockchain A storage and operations
# Used By:
#   - node.py (to get latest block and add new blocks)
#   - trust_engine_instant.py (to scan past blocks)
#   - trust_engine_periodic.py (to analyze long-term behavior)
# --------------------------------------------------------------

import json
import os
from blockchain.block import Block

# File where Blockchain A data is persisted
CHAIN_FILE = "shared_data/blockchain.json"

# --------------------------------------------------------------
# Function: load_chain
# Returns full blockchain history as list of block dicts
# --------------------------------------------------------------
def load_chain():
    if not os.path.exists(CHAIN_FILE):
        return []
    with open(CHAIN_FILE, "r") as f:
        return json.load(f)

# --------------------------------------------------------------
# Function: save_chain
# Writes full chain (list of blocks) to file
# --------------------------------------------------------------
def save_chain(chain_data):
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain_data, f, indent=4)

# --------------------------------------------------------------
# Function: add_block
# Appends a new block to the chain and saves it
# Input: block (Block object)
# --------------------------------------------------------------
def add_block(block):
    chain = load_chain()
    chain.append(block.to_dict())
    save_chain(chain)

# --------------------------------------------------------------
# Function: get_last_block
# Returns the most recent block or None if chain is empty
# --------------------------------------------------------------
def get_last_block():
    chain = load_chain()
    if not chain:
        return None
    return chain[-1]

# --------------------------------------------------------------
# Function: get_chain_length
# Returns the number of blocks currently in the chain
# --------------------------------------------------------------
def get_chain_length():
    return len(load_chain())
