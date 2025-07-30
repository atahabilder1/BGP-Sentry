#!/usr/bin/env python3
"""
Real signature utilities for cryptographic operations
"""
import logging
import json
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

class SignatureUtils:
    """Utilities for handling cryptographic signatures"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.public_key_registry = self._load_public_key_registry()
    
    def _load_public_key_registry(self):
        """Load the public key registry"""
        try:
            registry_path = Path(__file__).parent.parent / "shared_data" / "shared_registry" / "public_key_registry.json"
            self.logger.info(f"Loading public key registry from: {registry_path}")
            
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
            
            # Convert PEM strings to key objects
            public_keys = {}
            for as_id, pem_string in registry_data.items():
                try:
                    public_key = serialization.load_pem_public_key(
                        pem_string.encode(), 
                        backend=default_backend()
                    )
                    public_keys[as_id] = public_key
                    self.logger.debug(f"Loaded public key for {as_id}")
                except Exception as e:
                    self.logger.error(f"Failed to load public key for {as_id}: {e}")
            
            self.logger.info(f"Successfully loaded {len(public_keys)} public keys")
            return public_keys
            
        except Exception as e:
            self.logger.error(f"Failed to load public key registry: {e}")
            return {}
    
    def verify_signature(self, message, signature_hex, as_id):
        """Verify a cryptographic signature"""
        try:
            if as_id not in self.public_key_registry:
                self.logger.error(f"No public key found for AS {as_id}")
                return False
            
            public_key = self.public_key_registry[as_id]
            signature = bytes.fromhex(signature_hex)
            
            # Create hash of message
            if isinstance(message, str):
                message = message.encode()
            message_hash = hashlib.sha256(message).digest()
            
            # Verify signature
            public_key.verify(
                signature,
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            self.logger.debug(f"Signature verification successful for AS {as_id}")
            return True
            
        except InvalidSignature:
            self.logger.warning(f"Invalid signature for AS {as_id}")
            return False
        except Exception as e:
            self.logger.error(f"Signature verification error for AS {as_id}: {e}")
            return False
    
    def sign_message(self, message, private_key_path):
        """Sign a message with private key"""
        try:
            # Load private key
            with open(private_key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            # Create hash of message
            if isinstance(message, str):
                message = message.encode()
            message_hash = hashlib.sha256(message).digest()
            
            # Sign the hash
            signature = private_key.sign(
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            signature_hex = signature.hex()
            self.logger.debug(f"Message signed successfully, signature: {signature_hex[:32]}...")
            return signature_hex
            
        except Exception as e:
            self.logger.error(f"Message signing failed: {e}")
            return None
