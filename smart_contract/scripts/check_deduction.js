require("dotenv").config();
const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const userAddress = process.env.ADDRESS;
  const amountEth = process.env.AMOUNT;

  if (!userAddress || !ethers.isAddress(userAddress)) {
    console.error("❌ Please set a valid ADDRESS in .env or as env variable.");
    process.exit(1);
  }

  if (!amountEth || isNaN(amountEth)) {
    console.error("❌ Please set a valid AMOUNT in ETH.");
    process.exit(1);
  }

  // ✅ Load deployed address and ABI from deployment JSON
  const deploymentPath = path.join(__dirname, "../deployments/localhost/StakingContract.json");
  const { address: contractAddress, abi } = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));

  const [admin] = await ethers.getSigners();
  const contract = new ethers.Contract(contractAddress, abi, admin);

  const initialStake = await contract.getStake(userAddress);
  console.log(`📊 Initial stake for ${userAddress}: ${ethers.formatEther(initialStake)} ETH`);

  const deductionAmount = ethers.parseEther(amountEth);
  const tx = await contract.deductStake(userAddress, deductionAmount);
  await tx.wait();

  const updatedStake = await contract.getStake(userAddress);
  console.log(`✅ Deducted ${amountEth} ETH. New stake: ${ethers.formatEther(updatedStake)} ETH`);
}

main().catch((err) => {
  console.error("❌ Error:", err);
  process.exit(1);
});
