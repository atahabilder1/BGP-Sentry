require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  defaultNetwork: "localhost",
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  paths: {
    sources: ".",
    tests: ".",
    cache: "./.cache",
    artifacts: "./artifacts",
  },
  networks: {
    localhost: {
      url: "http://127.0.0.1:8545"
    }
  }
};
