# StakingContract Deployment and Operations Guide

This repository contains a `StakingContract` smart contract designed for staking native ETH on an EVM-compatible blockchain, such as the Hardhat local testnet. The contract allows users to stake ETH, unstake it, and query staked amounts. This README provides a step-by-step guide to set up your environment, deploy the contract, stake funds, check balances, and perform other operations as of **04:29 AM EDT on Friday, July 18, 2025**.

## Table of Contents
- [StakingContract Deployment and Operations Guide](#stakingcontract-deployment-and-operations-guide)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [The admin account](#the-admin-account)
  - [Compiling the Contract](#compiling-the-contract)
  - [Deploying the Contract](#deploying-the-contract)
  - [Staking Funds for All Accounts](#staking-funds-for-all-accounts)
  - [Checking Balances and Staked Amounts](#checking-balances-and-staked-amounts)
  - [Performing Other Operations](#performing-other-operations)
    - [Unstaking Funds](#unstaking-funds)
    - [Querying Specific Accounts](#querying-specific-accounts)
  - [Troubleshooting](#troubleshooting)
  - [Additional Notes](#additional-notes)
  - [Next Steps](#next-steps)

## Prerequisites

- **Node.js**: Version 14.x or higher (recommended: 20.x or later).
- **npm**: Comes with Node.js, or install separately.
- **Git**: To clone the repository (optional if downloading manually).

## Installation

1. **Clone or Download the Repository**:
   ```bash
   git clone https://github.com/yourusername/BGP_Announcement_Recorder.git
   cd BGP_Announcement_Recorder/smart_contract
   ```

   Alternatively, download the ZIP file from the repository and extract it to `~/code/BGP_Announcement_Recorder/smart_contract`.

2. **Install Hardhat and Dependencies**:
   ```bash
   npm init -y
   npm install --save-dev hardhat
   npx hardhat init
   ```

   Select "Create a JavaScript project" and accept the default options if prompted.

3. **Install the Hardhat Toolbox**:
   ```bash
   npm install --save-dev @nomicfoundation/hardhat-toolbox
   ```

4. **Install Ethers.js**:
   ```bash
   npm install ethers
   ```

## Configuration

Update `hardhat.config.js` with the following:

```javascript
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.28",
  networks: {
    hardhat: {
      chainId: 31337,
      db: { path: "./hardhat-data" },
      accounts: {
        mnemonic: "test test test test test test test test test test test junk",
        count: 20
      },
      saveDeployments: true
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337
    }
  },
  paths: {
    artifacts: "./artifacts",
    cache: "./cache",
    deployments: "./deployments"
  }
};
```

## The admin account 
0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
This account can adjust the amount and it can also withdraw the amount. 

## Compiling the Contract

```bash
npx hardhat compile
```

## Deploying the Contract

1. **Start the Hardhat Node**:
   ```bash
   npx hardhat node
   ```

2. **Deploy the Contract**:
   ```bash
   npx hardhat run scripts/deploy.js --network localhost
   ```

## Staking Funds for All Accounts

```bash
npx hardhat run scripts/deposit_from_all.js --network localhost
```

Expected output: each of 20 accounts stakes 100 ETH and contract holds 4000 ETH.

## Checking Balances and Staked Amounts

```bash
ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8 npx hardhat run scripts/check_single_stake.js --network localhost

```

Expected: Each account shows `100 ETH` staked, `~9900 ETH` remaining.

## Performing Other Operations

### Unstaking Funds

```bash
npx hardhat run scripts/unstake.js --network localhost
```

Expected: Account's staked ETH is withdrawn and ETH balance increases.

### Querying Specific Accounts

```bash
npx hardhat run scripts/check_specific_accounts.js --network localhost
```

Expected: Shows staked balance and native ETH balance of selected addresses.

## Troubleshooting

- **Missing Deployment File**:
  ```bash
  npx hardhat run scripts/deploy.js --network localhost
  ```

- **BAD_DATA Error**:
  Check the contract bytecode:
  ```bash
  npx hardhat console --network localhost
  const code = await ethers.provider.getCode("0xYourDeployedAddress");
  ```

- **EADDRINUSE**:
  ```bash
  lsof -i :8545
  kill -9 <PID>
  npx hardhat node
  ```

- **Reset Node**:
  ```bash
  rm -rf hardhat-data
  mkdir hardhat-data
  npx hardhat node
  ```

## Additional Notes

- Each staking transaction uses ~21,160 gas.
- Never reuse testnet private keys on mainnet.
- Update Hardhat if needed:
  ```bash
  npm install --save-dev hardhat@latest
  ```

## Next Steps

- Follow the deployment → staking → checking flow.
- Share errors for support or troubleshooting help.