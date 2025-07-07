# --------------------------------------------------------------
# File: utils.py
# Purpose: Utility functions for hashing, signing, logging, etc.
# Used By: Any file needing common utilities
# --------------------------------------------------------------

import hashlib
import base64

# --------------------------------------------------------------
# Function: sha256_hash
# Returns the SHA-256 hash of any string input
# --------------------------------------------------------------
def sha256_hash(data_str):
    return hashlib.sha256(data_str.encode()).hexdigest()

# --------------------------------------------------------------
# Function: compute_prefix_key
# Returns a standard key format for (ASN, Prefix) tuple
# Used to access trust scores or logs consistently
# --------------------------------------------------------------
def compute_prefix_key(asn, prefix):
    return f"{asn}_{prefix}"

# --------------------------------------------------------------
# Function: sign_data_placeholder
# Placeholder for signing mechanism
# For future PKI integration, replace with real crypto signing
# --------------------------------------------------------------
def sign_data_placeholder(data_str, private_key=None):
    # Simulate a "signature" for demonstration purposes
    digest = hashlib.sha256(data_str.encode()).digest()
    return base64.b64encode(digest).decode()

# --------------------------------------------------------------
# Function: verify_signature_placeholder
# Placeholder for signature verification
# --------------------------------------------------------------
def verify_signature_placeholder(data_str, signature, public_key=None):
    # Always returns True for demo — replace with real check later
    return True
