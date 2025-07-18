const { ethers } = require("hardhat");
const fs = require("fs");

async function main() {
    // Load contract address from deployment file
    let contractAddress;
    try {
        const deployment = JSON.parse(fs.readFileSync("./deployments/StakingContract.json"));
        contractAddress = deployment.address;
    } catch (error) {
        console.error("Deployment file not found. Please deploy the contract first.");
        process.exit(1);
    }

    // Connect to the contract
    let contract;
    try {
        contract = await ethers.getContractAt("StakingContract", contractAddress);
        console.log("Connected to StakingContract at:", contractAddress);
    } catch (error) {
        console.error("Failed to connect to contract:", error.message);
        process.exit(1);
    }

    // Get all signers (20 default Hardhat accounts)
    const signers = await ethers.getSigners();

    // Check staked and native ETH balances
    console.log("\nChecking staked amounts and native ETH balances for all accounts:");
    for (let i = 0; i < signers.length; i++) {
        const addr = signers[i].address;
        try {
            const stake = await contract.getStake(addr);
            const balance = await ethers.provider.getBalance(addr);
            console.log(
                `Account ${i} (${addr}):\n` +
                `  Staked Amount: ${ethers.formatEther(stake)} ETH\n` +
                `  Native ETH Balance: ${ethers.formatEther(balance)} ETH`
            );
        } catch (error) {
            console.error(`Error fetching data for ${addr}:`, error.message);
        }
    }

    // Get total contract balance
    try {
        const totalBalance = await ethers.provider.getBalance(contractAddress);
        console.log(`\n✅ Total contract balance: ${ethers.formatEther(totalBalance)} ETH`);
    } catch (error) {
        console.error("Error fetching contract balance:", error.message);
    }
}

main().catch((err) => {
    console.error("Script failed:", err);
    process.exit(1);
});