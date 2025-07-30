from utils import load_verification_registry, convert_as_format

def is_as_verified(as_number, registry_path=None):
    """Check if an AS is RPKI verified."""
    print(f"DEBUG: Input = {repr(as_number)}, type = {type(as_number)}")
    
    try:
        registry = load_verification_registry(registry_path)
        
        # Convert to registry format
        if isinstance(as_number, int):
            registry_key = f"as{as_number:02d}"
            print(f"DEBUG: Integer path, registry_key = {registry_key}")
        else:
            # Handle string input
            as_str = str(as_number)
            print(f"DEBUG: String path, as_str = {repr(as_str)}")
            if as_str.isdigit():
                registry_key = f"as{int(as_str):02d}"
                print(f"DEBUG: Digit string, registry_key = {registry_key}")
            else:
                registry_key = as_str
                print(f"DEBUG: Non-digit string, registry_key = {registry_key}")
        
        result = registry.get(registry_key, False)
        print(f"DEBUG: Looking up '{registry_key}' in registry")
        print(f"DEBUG: Registry has key: {registry_key in registry}")
        print(f"DEBUG: Registry value: {registry.get(registry_key, 'NOT FOUND')}")
        print(f"🔍 Checking {registry_key}: {'✅ RPKI Valid' if result else '❌ RPKI Invalid'}")
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python verifier_debug.py <as_number>")
        sys.exit(1)
    
    asn = sys.argv[1]
    print(f"MAIN: Processing argument {repr(asn)}")
    result = is_as_verified(asn)
    print(f"MAIN: Function returned {result}")
    
    if result:
        print(f"{asn} ✅ is RPKI verified.")
    else:
        print(f"{asn} ❌ is NOT RPKI verified (needs trust engine monitoring).")
