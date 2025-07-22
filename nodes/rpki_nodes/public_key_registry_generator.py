import os
import json
from cryptography.hazmat.primitives import serialization

# Current directory contains as01, as03, ..., as19
rpki_base = "."  # ← you're inside rpki_nodes
output_file = "public_key_registry.json"
registry = {}

# Loop through all asXX folders
for folder in os.listdir(rpki_base):
    folder_path = os.path.join(rpki_base, folder)
    if not os.path.isdir(folder_path) or not folder.startswith("as"):
        continue

    asn = folder.replace("as", "").zfill(2)
    full_as = f"AS65{asn}"
    private_key_filename = f"as_{asn}_private_key.pem"
    private_key_path = os.path.join(folder_path, private_key_filename)

    if not os.path.exists(private_key_path):
        print(f"⚠️  Skipping {folder}: private key not found.")
        continue

    # Load private key and extract public key
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
        public_key = private_key.public_key()

    # Convert public key to PEM
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    # Store in registry
    registry[full_as] = public_pem

# Write to file in the current directory
with open(output_file, "w") as f:
    json.dump(registry, f, indent=2)

print(f"✅ public_key_registry.json created with {len(registry)} entries.")
