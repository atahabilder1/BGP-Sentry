import logging
from pathlib import Path
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# --------------------------------------
# Directory Configuration
# --------------------------------------
# All paths are defined relative to the BGP_Announcement_Recorder project root

def find_project_root(start_path):
    """
    Find the BGP_Announcement_Recorder directory by walking up from start_path.
    Returns: Path object or raises FileNotFoundError if not found.
    """
    current = Path(start_path).resolve()
    while current != current.parent:
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
# Example modification: RPKI_NODE_DIR = PROJECT_ROOT / "other_nodes" / "rpki_nodes"

# Shared Data Directory: Contains shared_registry/public_key_registry.json
SHARED_DATA_DIR = RPKI_NODE_DIR / "shared_blockchain_stack" / "shared_data"
# Example modification: SHARED_DATA_DIR = RPKI_NODE_DIR / "rpki_verification_system"

# Public Key Registry Path: Path to public_key_registry.json
REGISTRY_PATH = SHARED_DATA_DIR / "shared_registry" / "public_key_registry.json"
# Example modifications:
# - No shared_registry: REGISTRY_PATH = SHARED_DATA_DIR / "public_key_registry.json"
# - Different filename: REGISTRY_PATH = SHARED_DATA_DIR / "shared_registry" / "key_registry.json"

# ASN List: ASNs to process (as01, as03, ..., as17)
ASN_LIST = [f"as{i:02d}" for i in range(1, 18, 2)]
# Example modifications:
# - All ASNs: ASN_LIST = [f"as{i:02d}" for i in range(1, 18)]
# - Specific ASNs: ASN_LIST = ["as01", "as03", "as11"]

# Registry Key Format: Function to determine registry key for each ASN
def get_registry_key(asn):
    # Default: Use uppercase format (e.g., 'AS01') to match previous registry
    return f"AS{int(asn[2:]):02d}"
# Example modifications:
# - Lowercase: return asn
# - Numeric: return str(int(asn[2:]))
# - Custom: return f"ASN_{asn[2:]}"

# --------------------------------------
# End Directory Configuration
# --------------------------------------

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("update_public_key_registry.log", mode='a'),
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

def get_public_key_pem(private_key):
    """
    Derive public key from private key in PEM format.
    Returns: Public key PEM string or None if derivation fails.
    """
    logger.info("Deriving public key")
    try:
        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        logger.debug("Public key derived: %s...", public_key_pem[:50])
        return public_key_pem
    except Exception as e:
        logger.error("Failed to derive public key: %s", str(e))
        return None

def update_public_key_registry(asn, public_key_pem, registry_path):
    """
    Update public_key_registry.json with public key for ASN.
    Returns: True if successful, False otherwise.
    """
    logger.info("Updating public key registry for %s", asn)
    try:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(registry_path, "r") as f:
                registry = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            registry = {}
        
        registry_key = get_registry_key(asn)
        registry[registry_key] = public_key_pem
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2)
        logger.debug("Public key registry updated with key %s", registry_key)
        return True
    except Exception as e:
        logger.error("Failed to update public key registry for %s: %s", asn, str(e))
        return False

def main():
    """
    Iterate through private keys, derive public keys, and update registry.
    """
    logger.info("Starting public key registry update")
    
    project_root = PROJECT_ROOT.resolve()
    rpki_node_dir = RPKI_NODE_DIR.resolve()
    shared_data_dir = SHARED_DATA_DIR
    logger.debug("Project root: %s", project_root)
    logger.debug("RPKI node directory: %s", rpki_node_dir)
    logger.debug("Shared data directory: %s", shared_data_dir)

    for asn in ASN_LIST:
        logger.info("Processing ASN: %s", asn)
        private_key_path = RPKI_NODE_DIR / asn / "blockchain_node" / "private_key.pem"
        
        # Load private key
        private_key = load_private_key(private_key_path)
        if not private_key:
            print(f"\033[31m❌ Error: Failed to load private key for {asn}\033[0m")
            continue

        # Derive public key
        public_key_pem = get_public_key_pem(private_key)
        if not public_key_pem:
            print(f"\033[31m❌ Error: Failed to derive public key for {asn}\033[0m")
            continue

        # Update public key registry
        if not update_public_key_registry(asn, public_key_pem, REGISTRY_PATH):
            print(f"\033[31m❌ Error: Failed to update public key registry for {asn}\033[0m")
            continue

        print(f"\033[32m✅ Success: Updated public key for {asn}\033[0m")

    logger.info("Completed public key registry update")

if __name__ == "__main__":
    main()