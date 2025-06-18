# --------------------------------------------------------------
# block.py
# --------------------------------------------------------------
# This file defines the two core classes:
#   1. BGPAnnouncement - represents a single BGP routing update
#   2. Block - represents a blockchain block containing a batch
#              of BGP announcements
#
# Used by:
#   - bgp_collector.py (uses BGPAnnouncement)
#   - node.py (uses both classes to build new blocks)
#   - blockchain.py (serializes and stores blocks)
# --------------------------------------------------------------

import hashlib
import json
import time

# --------------------------------------------------------------
# Class: BGPAnnouncement
# Represents a single BGP route announcement.
# --------------------------------------------------------------
class BGPAnnouncement:
    def __init__(self, asn, prefix, as_path, next_hop):
        self.asn = asn                    # Origin ASN of the announcement
        self.prefix = prefix              # IP prefix being announced
        self.as_path = as_path            # AS path to reach the prefix
        self.next_hop = next_hop          # IP address of the next hop
        self.timestamp = int(time.time()) # Timestamp of the announcement

    # Convert object to a serializable dictionary
    def to_dict(self):
        return {
            "asn": self.asn,
            "prefix": self.prefix,
            "as_path": self.as_path,
            "next_hop": self.next_hop,
            "timestamp": self.timestamp
        }

# --------------------------------------------------------------
# Class: Block
# Represents a block in the blockchain.
# Each block contains a list of BGP announcements and metadata.
# --------------------------------------------------------------
class Block:
    def __init__(self, index, previous_hash, proposer, announcements):
        self.index = index                    # Block height/index
        self.timestamp = int(time.time())     # Block creation timestamp
        self.previous_hash = previous_hash    # Hash of the previous block
        self.proposer = proposer              # ASN that proposed this block
        self.announcements = announcements    # List of BGPAnnouncement objects
        self.hash = self.compute_hash()       # Hash of this block's content

    # Computes SHA-256 hash of the block (excluding the `hash` field itself)
    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "proposer": self.proposer,
            "announcements": [a.to_dict() for a in self.announcements]
        }, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    # Convert block to a serializable dictionary
    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "proposer": self.proposer,
            "announcements": [a.to_dict() for a in self.announcements],
            "hash": self.hash
        }
