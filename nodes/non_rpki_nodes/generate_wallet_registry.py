import os
import json
import re

# Assume this script runs from inside "non_rpki_nodes"
wallet_file = "web3_wallet.txt"
output_path = os.path.join("..", "rpki_nodes", "nonrpki_wallet_registry.json")

# Extract wallet addresses from the web3_wallet.txt content
with open(wallet_file, "r") as f:
    lines = f.readlines()

wallets = []
for line in lines:
    match = re.search(r"Account\s+#\d+:\s+(0x[a-fA-F0-9]{40})", line)
    if match:
        wallets.append(match.group(1))

# List non-RPKI AS folders in current directory (e.g., as02, as04, ...)
as_folders = sorted([d for d in os.listdir() if os.path.isdir(d) and d.startswith("as")])

# Create mapping: as02 → wallet
mapping = {}
for i, folder in enumerate(as_folders):
    if i < len(wallets):
        mapping[folder] = wallets[i]
    else:
        mapping[folder] = "NO_WALLET_AVAILABLE"

# Save the mapping as JSON
with open(output_path, "w") as f:
    json.dump(mapping, f, indent=4)

print("✅ Wallet registry generated at:", output_path)
