#!/usr/bin/env python3
"""
Cryptographic signature utilities for BGP-Sentry blockchain.

Provides two modes:
  1. In-memory key generation (for dynamic simulation nodes)
  2. File-based key loading (backward compat with 9-node setup)

Each RPKI node gets an RSA-2048 key pair generated at startup.
Transactions and consensus votes are signed with the node's private key
and verified using the shared public key registry.
"""
import logging
import json
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


class SignatureUtils:
    """Utilities for handling cryptographic signatures."""

    # ------------------------------------------------------------------
    # In-memory key generation (used by NodeManager for dynamic nodes)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_key_pair():
        """
        Generate an RSA-2048 key pair in memory.

        Returns:
            tuple: (private_key, public_key, public_key_pem)
                - private_key: RSA private key object (for signing)
                - public_key: RSA public key object (for verification)
                - public_key_pem: PEM-encoded public key string (for registry)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        return private_key, public_key, public_pem

    @staticmethod
    def sign_with_key(message, private_key):
        """
        Sign a message using an in-memory RSA private key.

        Args:
            message: str or bytes to sign
            private_key: RSA private key object

        Returns:
            Hex-encoded signature string, or None on error
        """
        try:
            if isinstance(message, str):
                message = message.encode()
            message_hash = hashlib.sha256(message).digest()
            signature = private_key.sign(
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return signature.hex()
        except Exception as e:
            logger.error(f"sign_with_key failed: {e}")
            return None

    @staticmethod
    def verify_with_key(message, signature_hex, public_key):
        """
        Verify a signature using an in-memory RSA public key.

        Args:
            message: str or bytes that was signed
            signature_hex: Hex-encoded signature
            public_key: RSA public key object

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
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False
        except Exception as e:
            logger.error(f"verify_with_key failed: {e}")
            return False

    # ------------------------------------------------------------------
    # File-based key loading (backward compat)
    # ------------------------------------------------------------------
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.public_key_registry = self._load_public_key_registry()

    def _load_public_key_registry(self):
        """Load the public key registry from disk (old 9-node setup)."""
        try:
            registry_path = (
                Path(__file__).parent.parent
                / "shared_data" / "shared_registry" / "public_key_registry.json"
            )
            if not registry_path.exists():
                return {}

            self.logger.info(f"Loading public key registry from: {registry_path}")
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)

            public_keys = {}
            for as_id, pem_string in registry_data.items():
                try:
                    public_key = serialization.load_pem_public_key(
                        pem_string.encode(),
                        backend=default_backend(),
                    )
                    public_keys[as_id] = public_key
                except Exception as e:
                    self.logger.error(f"Failed to load public key for {as_id}: {e}")

            self.logger.info(f"Loaded {len(public_keys)} public keys from disk")
            return public_keys

        except Exception as e:
            self.logger.error(f"Failed to load public key registry: {e}")
            return {}

    def verify_signature(self, message, signature_hex, as_id):
        """Verify a cryptographic signature (file-based registry)."""
        try:
            if as_id not in self.public_key_registry:
                return False

            public_key = self.public_key_registry[as_id]
            if isinstance(message, str):
                message = message.encode()
            message_hash = hashlib.sha256(message).digest()

            public_key.verify(
                bytes.fromhex(signature_hex),
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True

        except InvalidSignature:
            return False
        except Exception as e:
            self.logger.error(f"Signature verification error for AS {as_id}: {e}")
            return False

    def sign_message(self, message, private_key_path):
        """Sign a message with private key from file."""
        try:
            with open(private_key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend(),
                )

            if isinstance(message, str):
                message = message.encode()
            message_hash = hashlib.sha256(message).digest()

            signature = private_key.sign(
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return signature.hex()

        except Exception as e:
            self.logger.error(f"Message signing failed: {e}")
            return None
