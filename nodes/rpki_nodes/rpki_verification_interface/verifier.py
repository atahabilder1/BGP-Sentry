import sys
from pathlib import Path

# Add blockchain_utils to path for RPKINodeRegistry
_blockchain_utils = Path(__file__).resolve().parent.parent / "shared_blockchain_stack" / "blockchain_utils"
sys.path.insert(0, str(_blockchain_utils))

from rpki_node_registry import RPKINodeRegistry


def is_as_verified(as_number, registry_path=None):
    """Check if an AS is RPKI verified using the RPKINodeRegistry."""
    try:
        if isinstance(as_number, str):
            # Handle "as01" format or plain number string
            cleaned = as_number.lower().replace("as", "")
            as_num = int(cleaned)
        else:
            as_num = int(as_number)

        result = RPKINodeRegistry.is_rpki_node(as_num)
        return result

    except Exception as e:
        print(f"Error: {e}")
        return False


def get_all_verified_ases():
    """Get all RPKI-verified ASes from registry."""
    return RPKINodeRegistry.get_all_rpki_nodes()


def get_all_unverified_ases():
    """Get all non-RPKI ASes (these need trust engine monitoring)."""
    return RPKINodeRegistry.get_all_non_rpki_nodes()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("=== RPKI Verification Registry Summary ===")
        verified = get_all_verified_ases()
        unverified = get_all_unverified_ases()
        print(f"RPKI Verified ASes ({len(verified)}): {verified}")
        print(f"Non-RPKI ASes ({len(unverified)}): {unverified}")

    elif len(sys.argv) == 2:
        asn = sys.argv[1]
        if is_as_verified(asn):
            print(f"{asn} is RPKI verified.")
        else:
            print(f"{asn} is NOT RPKI verified (needs trust engine monitoring).")
