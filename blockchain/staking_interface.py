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
# Setup Ethereum connection (Infura / Alchemy / Local Node)
# --------------------------------------------------------------
INFURA_URL = os.getenv("INFURA_URL", "https://mainnet.infura.io/v3/YOUR_PROJECT_ID")  # Replace with your actual URL
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

# --------------------------------------------------------------
# Smart Contract Settings
# Replace these with actual contract details
# --------------------------------------------------------------
CONTRACT_ADDRESS = Web3.to_checksum_address("0xYourStakingContractAddress")
ABI_FILE_PATH = "smart_contract/compiled/StakingContractABI.json"  # Assumes ABI JSON exists here

# Load ABI from JSON file
with open(ABI_FILE_PATH, "r") as f:
    contract_abi = json.load(f)

staking_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# --------------------------------------------------------------
# Function: get_staked_amount
# Given a wallet address, returns how much USDC is staked
# Returns: amount in USDC (float) or 0.0 if not staked
# --------------------------------------------------------------
def get_staked_amount(wallet_address):
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        raw_amount = staking_contract.functions.getStake(wallet_address).call()
        return raw_amount / 1e6  # Assuming USDC has 6 decimals
    except Exception as e:
        print(f"⚠️ Error checking stake for {wallet_address}: {e}")
        return 0.0

# --------------------------------------------------------------
# Example usage (for testing only)
# --------------------------------------------------------------
if __name__ == "__main__":
    test_wallet = "0x1234567890abcdef1234567890abcdef12345678"
    amount = get_staked_amount(test_wallet)
    print(f"💰 Wallet {test_wallet} has staked: {amount} USDC")
