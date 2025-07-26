# --------------------------------------------------------------
# File: staking_interface.py
# Purpose: Interface with staking smart contract on Blockchain B (Ethereum)
# Called By: RPKI validator node during announcement verification
# Calls: Ethereum node via Web3.py
# --------------------------------------------------------------

from web3 import Web3
import json
import os

# --------------------------------------------------------------
# Setup Ethereum connection (Hardhat local testnet)
# --------------------------------------------------------------
WEB3_PROVIDER_URI = "http://127.0.0.1:8545"  # Hardhat local testnet
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))

if not web3.is_connected():
    raise ConnectionError(f"❌ Failed to connect to Ethereum node at {WEB3_PROVIDER_URI}")

# --------------------------------------------------------------
# Smart Contract Settings
# Update CONTRACT_ADDRESS after deployment
# --------------------------------------------------------------
CONTRACT_ADDRESS = Web3.to_checksum_address("0x5FbDB2315678afecb367f032d93F642f64180aa3")

# ✅ Fix: Use relative path to ABI
ABI_FILE_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "..", "smart_contract", "artifacts", "contracts", "StakingContract.sol", "StakingContract.json"
))

# --------------------------------------------------------------
# Load ABI
# --------------------------------------------------------------
try:
    with open(ABI_FILE_PATH, "r") as f:
        artifact = json.load(f)
        contract_abi = artifact["abi"]
except FileNotFoundError:
    raise FileNotFoundError(f"❌ ABI file not found at {ABI_FILE_PATH}. Run 'npx hardhat compile'.")
except KeyError:
    raise KeyError(f"❌ ABI field missing in artifact: {ABI_FILE_PATH}")

# --------------------------------------------------------------
# Create Contract Instance
# --------------------------------------------------------------
staking_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# --------------------------------------------------------------
# Function: check_stake_amount
# Given a wallet address, returns how much is staked
# --------------------------------------------------------------
def check_stake_amount(wallet_address):
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        raw_amount = staking_contract.functions.getStake(wallet_address).call()
        return raw_amount
    except ValueError as e:
        print(f"⚠️ Invalid address {wallet_address}: {e}")
        return 0
    except Exception as e:
        print(f"⚠️ Error checking stake for {wallet_address}: {e}")
        return 0

# --------------------------------------------------------------
# Optional: Quick Test
# --------------------------------------------------------------
if __name__ == "__main__":
    test_wallet = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    amount = check_stake_amount(test_wallet)
    print(f"💰 Wallet {test_wallet} has staked: {amount} wei")
