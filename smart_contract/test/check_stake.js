const { ethers } = require("hardhat");  // Use Hardhat's ethers for getSigners()
const fs = require("fs");
const path = require("path");

async function main() {
  // Load ABI from Hardhat artifacts (same as before)
  const artifactPath = path.join(__dirname, "../artifacts/contracts/StakingContract.sol/StakingContract.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const abi = artifact.abi;

  // Deployed contract address
  const contractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3";

  // Create contract instance (read-only, using default provider)
  const contract = await ethers.getContractAt(abi, contractAddress);

  // Get signers (array of Signer objects)
  const signers = await ethers.getSigners();

  console.log("🔍 Stake balances for all accounts:\n");

  // Loop through signers and query stake
  for (const signer of signers) {
    const stake = await contract.getStake(signer.address);
    console.log(`🧑‍💻 ${signer.address} → ${ethers.formatEther(stake)} ETH`);
  }
}

main().catch((err) => {
  console.error("❌ Error:", err);
  process.exit(1);
});