import json

def load_verification_registry(path="rpki_verification_registry.json"):
    """Load the RPKI verification registry."""
    with open(path, "r") as f:
        return json.load(f)
