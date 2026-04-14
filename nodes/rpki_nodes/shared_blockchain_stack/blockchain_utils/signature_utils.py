#!/usr/bin/env python3
"""
Cryptographic signature utilities for BGP-Sentry blockchain.

Uses Ed25519 for fast signing and verification (replaces RSA-2048).

Ed25519 advantages over RSA-2048:
  - Key generation: ~100x faster
  - Signing: ~20x faster (~0.05ms vs ~1ms)
  - Verification: ~5x faster
  - Key size: 32 bytes vs 256 bytes
  - Deterministic (no padding randomness)

Each RPKI node gets an Ed25519 key pair generated at startup.
Transactions and consensus votes are signed with the node's private key
and verified using the shared public key registry.
"""
import logging
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


class SignatureUtils:
    """Utilities for handling cryptographic signatures."""

    # ------------------------------------------------------------------
    # In-memory key generation (Ed25519)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_key_pair():
        """
        Generate an Ed25519 key pair in memory.

        Returns:
            tuple: (private_key, public_key, public_key_pem)
                - private_key: Ed25519 private key object (for signing)
                - public_key: Ed25519 public key object (for verification)
                - public_key_pem: PEM-encoded public key string (for registry)
        """
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        return private_key, public_key, public_pem

    @staticmethod
    def sign_with_key(message, private_key):
        """
        Sign a message using an in-memory Ed25519 private key.

        Args:
            message: str or bytes to sign
            private_key: Ed25519 private key object

        Returns:
            Hex-encoded signature string, or None on error
        """
        try:
            if isinstance(message, str):
                message = message.encode()
            # Ed25519 signs the message directly (no separate hashing needed,
            # but we hash first to keep a fixed-size input for consistency)
            message_hash = hashlib.sha256(message).digest()
            signature = private_key.sign(message_hash)
            return signature.hex()
        except Exception as e:
            logger.error(f"sign_with_key failed: {e}")
            return None

    @staticmethod
    def verify_with_key(message, signature_hex, public_key):
        """
        Verify a signature using an in-memory Ed25519 public key.

        Args:
            message: str or bytes that was signed
            signature_hex: Hex-encoded signature
            public_key: Ed25519 public key object

        Returns:
            True if valid, False otherwise
        """
        try:
            if isinstance(message, str):
                message = message.encode()
            message_hash = hashlib.sha256(message).digest()
            public_key.verify(
                bytes.fromhex(signature_hex),
                message_hash,
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            logger.error(f"verify_with_key failed: {e}")
            return False
