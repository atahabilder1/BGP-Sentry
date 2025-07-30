from utils import load_verification_registry, convert_as_format

def is_as_verified(as_number, registry_path=None):
    """Check if an AS is RPKI verified."""
    try:
        registry = load_verification_registry(registry_path)
        
        # Convert to registry format
        if isinstance(as_number, int):
            registry_key = f"as{as_number:02d}"
        else:
            # Handle string input
            as_str = str(as_number)
            if as_str.isdigit():
                registry_key = f"as{int(as_str):02d}"
            else:
                registry_key = as_str
        
        result = registry.get(registry_key, False)
        print(f"🔍 Checking {registry_key}: {'✅ RPKI Valid' if result else '❌ RPKI Invalid'}")
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_all_verified_ases():
    """Get all RPKI-verified ASes from registry"""
    registry = load_verification_registry()
    return [as_id for as_id, verified in registry.items() if verified]

def get_all_unverified_ases():
    """Get all non-RPKI ASes (these need trust engine monitoring)"""
    registry = load_verification_registry()
    return [as_id for as_id, verified in registry.items() if not verified]

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # No arguments - show summary
        print("=== RPKI Verification Registry Summary ===")
        verified = get_all_verified_ases()
        unverified = get_all_unverified_ases()
        
        print(f"✅ RPKI Verified ASes ({len(verified)}): {verified}")
        print(f"❌ Non-RPKI ASes ({len(unverified)}): {unverified}")
        print(f"\nNote: Non-RPKI ASes need trust engine monitoring")
        
    elif len(sys.argv) == 2:
        # Single AS check
        asn = sys.argv[1]
        if is_as_verified(asn):
            print(f"{asn} ✅ is RPKI verified.")
        else:
            print(f"{asn} ❌ is NOT RPKI verified (needs trust engine monitoring).")
            
    else:
        print("Usage:")
        print("  python verifier.py                    # Show summary")
        print("  python verifier.py <as_number>        # Check specific AS")
