# --------------------------------------------------------------
# blockchain.py
# --------------------------------------------------------------
# This module manages the local blockchain file.
# It provides functions to:
#   - Load the blockchain from disk
#   - Append a new block
#   - Get the latest block
#   - Get the chain height (length)
#
# Used by:
#   - node.py (to propose new blocks and get chain info)
# --------------------------------------------------------------

import json
import os
from block import Block  # Used for type reference when needed

# Path to the local blockchain file
CHAIN_FILE = "data/blockchain.json"

# --------------------------------------------------------------
# Function: load_chain
# Loads the blockchain from disk (JSON format).
# Returns a list of block dictionaries.
# --------------------------------------------------------------
def load_chain():
    if not os.path.exists(CHAIN_FILE):
        return []  # Return empty list if no chain exists

    with open(CHAIN_FILE, "r") as f:
        data = json.load(f)
        return data

# --------------------------------------------------------------
# Function: save_chain
# Writes the given chain (list of blocks) to disk.
# --------------------------------------------------------------
def save_chain(chain_data):
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain_data, f, indent=4)

# --------------------------------------------------------------
# Function: add_block
# Adds a new block to the chain and saves it.
# Input: block (Block object)
# --------------------------------------------------------------
def add_block(block):
    chain = load_chain()                  # Load current chain
    chain.append(block.to_dict())        # Append new block (converted to dict)
    save_chain(chain)                    # Save updated chain

# --------------------------------------------------------------
# Function: get_last_block
# Returns the last block (as a dict) from the blockchain.
# Returns None if the chain is empty.
# --------------------------------------------------------------
def get_last_block():
    chain = load_chain()
    if not chain:
        return None
    return chain[-1]

# --------------------------------------------------------------
# Function: get_chain_length
# Returns the current height (number of blocks) in the chain.
# --------------------------------------------------------------
def get_chain_length():
    return len(load_chain())
