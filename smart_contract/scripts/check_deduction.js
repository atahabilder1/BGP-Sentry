require("dotenv").config();
const { ethers } = require("hardhat");

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

  const contractAddress = "0x5FC8d32690cc91D4c39d9d3abcBD16989F875707";
  const contract = await ethers.getContractAt("StakingContract", contractAddress);
  const [admin] = await ethers.getSigners();

  const initialStake = await contract.getStake(userAddress);
  console.log(`📊 Initial stake for ${userAddress}: ${ethers.formatEther(initialStake)} ETH`);

  const deductionAmount = ethers.parseEther(amountEth);
  const tx = await contract.connect(admin).deductStake(userAddress, deductionAmount);
  await tx.wait();

  const updatedStake = await contract.getStake(userAddress);
  console.log(`✅ Deducted ${amountEth} ETH. New stake: ${ethers.formatEther(updatedStake)} ETH`);
}

main().catch((err) => {
  console.error("❌ Error:", err);
  process.exit(1);
});
