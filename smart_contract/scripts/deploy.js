// scripts/deploy.js

const { ethers } = require("hardhat");

async function main() {
  console.log("🔧 Deploying StakingContract...");

  const Staking = await ethers.getContractFactory("StakingContract");
  const staking = await Staking.deploy(); // No constructor args

  await staking.waitForDeployment();

  console.log("✅ StakingContract deployed to:", await staking.getAddress());
}

main().catch((error) => {
  console.error("❌ Deployment error:", error);
  process.exit(1);
});