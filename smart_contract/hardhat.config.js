require("@nomicfoundation/hardhat-toolbox");
require("hardhat-deploy"); // ✅ Add deploy plugin

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  solidity: "0.8.28",

  networks: {
    hardhat: {
      chainId: 31337,
      saveDeployments: true, // ✅ Ensure deployment info is saved
      accounts: {
        mnemonic: "test test test test test test test test test test test junk",
        count: 20
      },
      // Optional: persistent chain state between runs (if desired)
      db: {
        path: "./hardhat-data"
      }
    },

    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
      saveDeployments: true
    }
  },

  namedAccounts: {
    deployer: {
      default: 0 // 👈 First account is used as deployer by default
    }
  },

  paths: {
    artifacts: "./artifacts",
    cache: "./cache",
    deployments: "./deployments" // ✅ Store deployment addresses here
  }
};
