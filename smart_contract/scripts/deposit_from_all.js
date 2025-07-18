const { ethers } = require("hardhat");

async function main() {
  const contractAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3"; // 🔁 Replace with deployed address
  const contract = await ethers.getContractAt("StakingContract", contractAddress);

  const signers = await ethers.getSigners();

  for (let i = 0; i < signers.length; i++) {
    const signer = signers[i];
    const tx = await contract.connect(signer).stake({
      value: ethers.parseEther("100")
    });
    await tx.wait();
    console.log(`Account ${i} (${signer.address}) staked 100 ETH`);
  }

  // Display final contract balance
  const finalBalance = await ethers.provider.getBalance(contractAddress);
  console.log(`\n✅ Contract final balance: ${ethers.formatEther(finalBalance)} ETH`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
