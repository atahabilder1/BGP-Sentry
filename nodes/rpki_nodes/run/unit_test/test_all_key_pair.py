import logging
from pathlib import Path
import json
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

# --------------------------------------
# Directory Configuration
# --------------------------------------
# All paths are defined relative to the BGP_Announcement_Recorder project root
# The root is dynamically found by searching for 'BGP_Announcement_Recorder' directory

def find_project_root(start_path):
    """
    Find the BGP_Announcement_Recorder directory by walking up from start_path.
    Returns: Path object or raises FileNotFoundError if not found.
    """
    current = Path(start_path).resolve()
    while current != current.parent:  # Stop at filesystem root
        if current.name == "BGP_Announcement_Recorder":
            return current
        current = current.parent
    raise FileNotFoundError(
        "Could not find 'BGP_Announcement_Recorder' directory. "
        "Ensure script is run from within the project or set PROJECT_ROOT manually."
    )

# Project Root: BGP_Announcement_Recorder directory
PROJECT_ROOT = find_project_root(__file__)
# Example modifications:
# - Manual absolute path: PROJECT_ROOT = Path("/home/anik/code/BGP_Announcement_Recorder")
# - Home-based path: PROJECT_ROOT = Path.home() / "code" / "BGP_Announcement_Recorder"

# RPKI Node Directory: Contains as01, as03, ..., as17 and shared_blockchain_stack
RPKI_NODE_DIR = PROJECT_ROOT / "nodes" / "rpki_nodes"
# Notes:
# - Relative to PROJECT_ROOT: nodes/rpki_nodes
# - Example modification: RPKI_NODE_DIR = PROJECT_ROOT / "other_nodes" / "rpki_nodes"

# Shared Data Directory: Contains shared_registry/public_key_registry.json
SHARED_DATA_DIR = RPKI_NODE_DIR / "shared_blockchain_stack" / "shared_data"
# Notes:
# - Relative to RPKI_NODE_DIR: shared_blockchain_stack/shared_data
# - Example modifications:
#   - If registry is in rpki_verification_system: SHARED_DATA_DIR = RPKI_NODE_DIR / "rpki_verification_system"
#   - If shared_data is elsewhere: SHARED_DATA_DIR = RPKI_NODE_DIR / "other_shared_data"

# Public Key Registry Path: Path to public_key_registry.json
REGISTRY_PATH = SHARED_DATA_DIR / "shared_registry" / "public_key_registry.json"
# Notes:
# - Relative to SHARED_DATA_DIR: shared_registry/public_key_registry.json
# - Example modifications:
#   - No shared_registry subdirectory: REGISTRY_PATH = SHARED_DATA_DIR / "public_key_registry.json"
#   - Different filename: REGISTRY_PATH = SHARED_DATA_DIR / "shared_registry" / "key_registry.json"
#   - Alternative path: REGISTRY_PATH = RPKI_NODE_DIR / "rpki_verification_system" / "rpki_verification_registry.json"

# ASN List: List of ASNs to test (default: as01, as03, ..., as17)
ASN_LIST = [f"as{i:02d}" for i in range(1, 18, 2)]
# Example modifications:
# - All ASNs (as01 to as17): ASN_LIST = [f"as{i:02d}" for i in range(1, 18)]
# - Specific ASNs: ASN_LIST = ["as01", "as03", "as11"]
# - Numeric ASNs: ASN_LIST = [f"as{i}" for i in [1, 3, 5, 7, 9, 11, 13, 15, 17]]

# Private Key Path Template: Function to construct private key path for each ASN
def get_private_key_path(asn):
    # Default: asXX/blockchain_node/private_key.pem for all ASNs
    return RPKI_NODE_DIR / asn / "blockchain_node" / "private_key.pem"
# Example modifications:
# - Use as01/private_key.pem for as01:
#   if asn == "as01":
#       return RPKI_NODE_DIR / asn / "private_key.pem"
#   return RPKI_NODE_DIR / asn / "blockchain_node" / "private_key.pem"
# - Custom subdirectory: return RPKI_NODE_DIR / asn / "keys" / "private_key.pem"

# Registry Key Lookup: Function to handle ASN naming in public_key_registry.json
def get_registry_key(asn):
    # Returns possible keys to check (e.g., 'as01', 'AS01', '1')
    return [asn, asn.upper(), str(int(asn[2:]))]
# Example modifications:
# - Only lowercase: return [asn]
# - Only numeric: return [str(int(asn[2:]))]
# - Custom format: return [asn, f"ASN_{asn[2:]}"]

# --------------------------------------
# End Directory Configuration
# --------------------------------------

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("test_all_key_pairs.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_private_key(private_key_path):
    """
    Load private key from a PEM file.
    Returns: Private key object or None if loading fails.
    """
    logger.info("Loading private key from %s", private_key_path)
    try:
        with open(private_key_path, 'rb') as f:
            pem = f.read()
        private_key = serialization.load_pem_private_key(
            pem,
            password=None,
            backend=default_backend()
        )
        logger.debug("Private key loaded: type=%s, size=%d bits", 
                     type(private_key).__name__, private_key.key_size)
        return private_key
    except Exception as e:
        logger.error("Failed to load private key from %s: %s", private_key_path, str(e))
        return None

def load_public_key_registry(registry_path):
    """
    Load public key registry from specified path.
    Returns: Dictionary of ASN to public key PEM strings or None if loading fails.
    """
    logger.info("Loading public key registry from %s", registry_path)
    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        logger.debug("Public key registry loaded with %d entries", len(registry))
        return registry
    except Exception as e:
        logger.error("Failed to load public key registry: %s", str(e))
        return None

def test_key_pair(asn, private_key, public_key_pem):
    """
    Test if a private key matches a public key by signing and verifying a message.
    Args:
        asn: ASN identifier (e.g., 'as01', 'AS11').
        private_key: Private key object.
        public_key_pem: Public key in PEM format (string).
    Returns: True if keys match, False otherwise.
    """
    logger.info("Testing key pair for ASN: %s", asn)
    try:
        # Load public key
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        logger.debug("Public key loaded for %s: type=%s, size=%d bits", 
                     asn, type(public_key).__name__, public_key.key_size)

        # Test message to sign
        test_message = b"Test message to verify key pair"
        message_hash = hashes.SHA256()
        data_hash = hashlib.sha256(test_message).digest()

        # Sign the message
        signature = private_key.sign(
            data_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        logger.debug("Message signed for %s, signature length: %d bytes", asn, len(signature))

        # Verify the signature
        public_key.verify(
            signature,
            data_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        logger.info("Key pair test successful for %s", asn)
        return True

    except InvalidSignature:
        # Log a snippet of the public key for debugging
        logger.error("Key pair test failed for %s: Signature verification failed. Public key snippet: %s...", 
                     asn, public_key_pem[:50])
        return False
    except Exception as e:
        logger.error("Key pair test failed for %s: %s", asn, str(e))
        return False

def main():
    """
    Loop through ASNs, load private keys, and test against public keys in registry.
    """
    logger.info("Starting key pair test for all nodes")
    
    # Resolve project root and other directories
    project_root = PROJECT_ROOT.resolve()
    rpki_node_dir = RPKI_NODE_DIR.resolve()
    shared_data_dir = SHARED_DATA_DIR
    logger.debug("Project root: %s", project_root)
    logger.debug("RPKI node directory: %s", rpki_node_dir)
    logger.debug("Shared data directory: %s", shared_data_dir)

    # Load public key registry
    registry = load_public_key_registry(REGISTRY_PATH)
    if not registry:
        print("\033[31m❌ Error: Failed to load public key registry\033[0m")
        logger.error("Aborting due to registry load failure")
        return

    # Store private keys and ASNs
    key_pairs = []
    for asn in ASN_LIST:
        private_key_path = get_private_key_path(asn)
        
        private_key = load_private_key(private_key_path)
        if private_key:
            key_pairs.append({"asn": asn, "private_key": private_key})
        else:
            print(f"\033[31m❌ Error: Failed to load private key for {asn}\033[0m")
            logger.warning("Skipping %s due to private key load failure", asn)

    # Test each key pair
    for pair in key_pairs:
        asn = pair["asn"]
        private_key = pair["private_key"]
        
        # Try possible registry keys (e.g., 'as01', 'AS01', '1')
        public_key_pem = None
        registry_key_used = None
        for key in get_registry_key(asn):
            public_key_pem = registry.get(key)
            if public_key_pem:
                registry_key_used = key
                break
        if not public_key_pem:
            print(f"\033[31m❌ Error: No public key found for {asn} in registry\033[0m")
            logger.error("No public key found for %s", asn)
            continue

        result = test_key_pair(asn, private_key, public_key_pem)
        if result:
            print(f"\033[32m✅ Success: {asn} key pair matches\033[0m")
        else:
            print(f"\033[31m❌ Error: {asn} key pair does not match (registry key: {registry_key_used})\033[0m")

    logger.info("Completed key pair tests")

if __name__ == "__main__":
    main()