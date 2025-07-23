# --------------------------------------------------------------
# File: block.py
# Purpose: Define data structures for BGPAnnouncement and Block
# Used By:
#   - blockchain.py (serialization and persistence)
#   - bgp_collector.py (parsing announcements)
#   - node.py (block creation)
# --------------------------------------------------------------

import hashlib
import json
import time

# --------------------------------------------------------------
# Class: BGPAnnouncement
# Represents a single BGP route announcement or withdrawal
# --------------------------------------------------------------
class BGPAnnouncement:
    def __init__(self, asn, prefix, as_path, next_hop, timestamp=None, ann_type="announce", wallet_address=""):
        self.asn = asn                      # Originating ASN
        self.prefix = prefix                # IP prefix
        self.as_path = as_path              # AS path
        self.next_hop = next_hop            # IP of next hop router
        self.timestamp = timestamp or int(time.time())  # UNIX timestamp
        self.type = ann_type                # "announce" or "withdraw"
        self.wallet_address = wallet_address  # Required to check stake

    def to_dict(self):
        return {
            "asn": self.asn,
            "prefix": self.prefix,
            "as_path": self.as_path,
            "next_hop": self.next_hop,
            "timestamp": self.timestamp,
            "type": self.type,
            "wallet_address": self.wallet_address
        }

# --------------------------------------------------------------
# Class: Block
# Represents a block in the local Blockchain A
# Contains a batch of announcements endorsed by one RPKI node
# --------------------------------------------------------------
class Block:
    def __init__(self, index, previous_hash, proposer, announcements):
        self.index = index                        # Block height
        self.timestamp = int(time.time())         # Timestamp of creation
        self.previous_hash = previous_hash        # Hash of previous block
        self.proposer = proposer                  # ASN that proposed the block
        self.announcements = announcements        # List of BGPAnnouncement
        self.hash = self.compute_hash()           # Hash of this block

    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "proposer": self.proposer,
            "announcements": [a.to_dict() for a in self.announcements]
        }, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "proposer": self.proposer,
            "announcements": [a.to_dict() for a in self.announcements],
            "hash": self.hash
        }
