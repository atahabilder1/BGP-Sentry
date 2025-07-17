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

# Check if connected to Ethereum node
if not web3.is_connected():
    raise ConnectionError("Failed to connect to Ethereum node at {}".format(WEB3_PROVIDER_URI))

# --------------------------------------------------------------
# Smart Contract Settings
# Replace CONTRACT_ADDRESS with actual deployed address
# --------------------------------------------------------------
CONTRACT_ADDRESS = Web3.to_checksum_address("0x5FbDB2315678afecb367f032d93F642f64180aa3")  # Update after deployment
ABI_FILE_PATH = "smart_contract/artifacts/contracts/StakingContract.sol/StakingContract.json"

# Load ABI from Hardhat artifact
try:
    with open(ABI_FILE_PATH, "r") as f:
        artifact = json.load(f)
        contract_abi = artifact["abi"]  # Extract the abi field
except FileNotFoundError:
    raise FileNotFoundError(f"ABI file not found at {ABI_FILE_PATH}. Run 'npx hardhat compile' in smart_contract/")
except KeyError:
    raise KeyError("ABI field missing in {}".format(ABI_FILE_PATH))

staking_contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# --------------------------------------------------------------
# Function: check_stake_amount
# Given a wallet address, returns how much is staked
# Returns: amount (int) or 0 if not staked or error occurs
# --------------------------------------------------------------
def check_stake_amount(wallet_address):
    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
        raw_amount = staking_contract.functions.getStake(wallet_address).call()
        return raw_amount  # No decimal conversion, as contract uses uint256
    except ValueError as e:
        print(f"⚠️ Invalid address {wallet_address}: {e}")
        return 0
    except Exception as e:
        print(f"⚠️ Error checking stake for {wallet_address}: {e}")
        return 0

# --------------------------------------------------------------
# Example usage (for testing only)
# --------------------------------------------------------------
if __name__ == "__main__":
    # Use a Hardhat test account (from 'npx hardhat node' output)
    test_wallet = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"  # Example Hardhat account
    amount = check_stake_amount(test_wallet)
    print(f"💰 Wallet {test_wallet} has staked: {amount} units")