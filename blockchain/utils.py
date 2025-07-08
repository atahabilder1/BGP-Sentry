# --------------------------------------------------------------
# File: utils.py
# Purpose: Common utilities for key handling and signing
# Used By:
#   - RPKI nodes to sign messages
#   - Trust engines to verify RPKI reports
# --------------------------------------------------------------

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import os

# --------------------------------------------------------------
# Function: load_private_key
# Loads PEM-encoded private key from file
# --------------------------------------------------------------
def load_private_key(asn):
    key_path = f"nodes/rpki_nodes/keys/private/private_key_{asn}.pem"
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

# --------------------------------------------------------------
# Function: load_public_key
# Loads PEM-encoded public key from file
# --------------------------------------------------------------
def load_public_key(asn):
    key_path = f"nodes/rpki_nodes/keys/public/public_key_{asn}.pem"
    with open(key_path, "rb") as f:
        return serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )

# --------------------------------------------------------------
# Function: sign_data
# Input: data (string), asn
# Output: binary signature
# --------------------------------------------------------------
def sign_data(data, asn):
    private_key = load_private_key(asn)
    return private_key.sign(
        data.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256()
    )

# --------------------------------------------------------------
# Function: verify_signature
# Input: data (string), signature (bytes), signer ASN
# Returns True if valid, False otherwise
# --------------------------------------------------------------
def verify_signature(data, signature, asn):
    try:
        public_key = load_public_key(asn)
        public_key.verify(
            signature,
            data.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
