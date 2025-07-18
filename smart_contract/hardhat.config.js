// Import Hardhat toolbox plugins (ethers, waffle, chai, etc.)
require("@nomicfoundation/hardhat-toolbox");

/** 
 * @type import('hardhat/config').HardhatUserConfig 
 */
module.exports = {
  solidity: "0.8.28",

  // Define multiple networks
  networks: {
    // 🧪 Local Hardhat network (used when running `npx hardhat node`)
    hardhat: {
      chainId: 31337, // Default Hardhat chain ID
      // Enable persistent storage by specifying a database path
      db: {
        path: "./hardhat-data" // Directory to store blockchain state
      },
      accounts: {
        mnemonic: "test test test test test test test test test test test junk", // Consistent mnemonic for deterministic accounts
        count: 20 // Number of accounts to generate
      },
      saveDeployments: true // Save deployment data to disk
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337 // Match Hardhat's chain ID
    },

    // ✅ Add Sepolia or other testnets here later if needed
    // sepolia: {
    //   url: "https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
    //   accounts: ["0xYOUR_PRIVATE_KEY"]
    // }
  },

  // Optional: Specify paths for artifacts and deployments
  paths: {
    artifacts: "./artifacts",
    cache: "./cache",
    deployments: "./deployments" // Store deployment data
  }
};