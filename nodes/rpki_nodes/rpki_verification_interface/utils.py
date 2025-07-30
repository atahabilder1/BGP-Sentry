import json
import os

def load_verification_registry(path=None):
    """Load the RPKI verification registry."""
    if path is None:
        # Default path to the actual registry location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(
            current_dir, 
            "..", 
            "shared_blockchain_stack", 
            "shared_data", 
            "shared_registry", 
            "rpki_verification_registry.json"
        )
    
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Registry file not found: {path}")
        return {}
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in registry file: {path}")
        return {}

def convert_as_format(as_input):
    """Convert between AS number formats (as01 <-> 1)"""
    if isinstance(as_input, str) and as_input.startswith('as'):
        # Convert "as01" to 1
        return int(as_input[2:])
    elif isinstance(as_input, int):
        # Convert 1 to "as01" (with proper zero-padding)
        return f"as{as_input:02d}"
    else:
        return as_input
