# --------------------------------------------------------------
# File: deploy_and_test.py
# Purpose: Compile, deploy, and interact with the staking contract
# Used By: Developer or administrator
# Dependencies: web3.py, solcx
# --------------------------------------------------------------

from web3 import Web3
from solcx import compile_standard, install_solc
import json
import os

# -------------------------------
# Step 1: Load and Compile Solidity
# -------------------------------
install_solc("0.8.0")

contract_path = "StakingContract.sol"
with open(contract_path, "r") as f:
    contract_source_code = f.read()

compiled_sol = compile_standard({
    "language": "Solidity",
    "sources": {
        "StakingContract.sol": {
            "content": contract_source_code
        }
    },
    "settings": {
        "outputSelection": {
            "*": {
                "*": ["abi", "metadata", "evm.bytecode"]
            }
        }
    }
}, solc_version="0.8.0")

bytecode = compiled_sol["contracts"]["StakingContract.sol"]["StakingContract"]["evm"]["bytecode"]["object"]
abi = compiled_sol["contracts"]["StakingContract.sol"]["StakingContract"]["abi"]

# -------------------------------
# Step 2: Connect to Blockchain
# -------------------------------
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))  # Ganache or local node
chain_id = 1337
my_address = w3.eth.accounts[0]
private_key = os.getenv("PRIVATE_KEY")  # Use .env for private keys in real projects

# -------------------------------
# Step 3: Deploy the Contract
# -------------------------------
StakingContract = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(my_address)

transaction = StakingContract.constructor().build_transaction({
    "chainId": chain_id,
    "from": my_address,
    "nonce": nonce,
    "gas": 2000000,
    "gasPrice": w3.to_wei("20", "gwei")
})

signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print(f"✅ Contract deployed at: {tx_receipt.contractAddress}")

# -------------------------------
# Step 4: Interact with Contract
# -------------------------------
contract = w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)

# Sample read
stake = contract.functions.getStake(my_address).call()
print(f"Current stake for {my_address}: {stake}")
