const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const targetAddress = process.env.ADDRESS;
  if (!targetAddress) {
    console.error("❌ Please set ADDRESS environment variable.");
    process.exit(1);
  }

  const deploymentPath = path.join(__dirname, "../deployments/localhost/StakingContract.json");
  if (!fs.existsSync(deploymentPath)) {
    console.error("❌ Deployment file not found. Please deploy the contract first.");
    process.exit(1);
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
  const contractAddress = deployment.address;

  const contract = await ethers.getContractAt("StakingContract", contractAddress);
  const stake = await contract.getStake(targetAddress);

  console.log(`📊 Stake for ${targetAddress}: ${ethers.formatEther(stake)} ETH`);
}

main().catch((err) => {
  console.error("❌ Error:", err);
  process.exit(1);
});
