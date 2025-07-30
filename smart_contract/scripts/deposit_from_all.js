const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  // Load deployed contract address from deployment JSON
  const deploymentPath = path.join(__dirname, "../deployments/localhost/StakingContract.json");
  const deploymentData = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
  const contractAddress = deploymentData.address;

  console.log(`📍 Using deployed contract at: ${contractAddress}`);
  const contract = await ethers.getContractAt("StakingContract", contractAddress);

  const signers = await ethers.getSigners();
  let totalStaked = 0;

  for (let i = 0; i < signers.length; i++) {
    const signer = signers[i];

    // Random ETH amount between 3 and 3.5
    const ethAmount = (3 + Math.random() * 0.5).toFixed(4);
    totalStaked += parseFloat(ethAmount);

    const tx = await contract.connect(signer).stake({
      value: ethers.parseEther(ethAmount) // ✅ Use ethers.parseEther (v6+)
    });
    await tx.wait();

    const stake = await contract.getStake(signer.address);
    console.log(`✅ Account ${i} (${signer.address}) staked ${ethAmount} ETH`);
    console.log(`   ↳ Contract recorded: ${ethers.formatEther(stake)} ETH\n`);
  }

  const contractBalance = await ethers.provider.getBalance(contractAddress);
  console.log(`🏁 Final Contract Balance: ${ethers.formatEther(contractBalance)} ETH`);
  console.log(`🧮 Expected Total (approx): ${totalStaked.toFixed(4)} ETH`);
}

main().catch((err) => {
  console.error("❌ Error:", err);
  process.exit(1);
});
