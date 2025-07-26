from utils import load_verification_registry

def is_as_verified(as_number, registry_path="rpki_verification_registry.json"):
    """
    Check if an AS (e.g., 'as05') is RPKI verified.

    Args:
        as_number (str): Autonomous system ID like 'as05'
        registry_path (str): Path to verification registry

    Returns:
        bool: True if RPKI verified, False otherwise
    """
    registry = load_verification_registry(registry_path)
    return registry.get(as_number, False)

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python verifier.py <as_number>")
        print("Example: python verifier.py as05")
        sys.exit(1)

    asn = sys.argv[1]
    if is_as_verified(asn):
        print(f"{asn} ✅ is RPKI verified.")
    else:
        print(f"{asn} ❌ is NOT RPKI verified.")
