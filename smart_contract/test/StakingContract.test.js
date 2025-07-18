// test/StakingContract.test.js

const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("StakingContract", function () {
  let staking;
  let user;

  beforeEach(async function () {
    // Option 1: Use your existing deployed address (persistent local state)
    staking = await ethers.getContractAt("StakingContract", "0x5FbDB2315678afecb367f032d93F642f64180aa3");

    // Option 2: Deploy fresh for each test (uncomment if preferred; comment out above)
    // const Staking = await ethers.getContractFactory("StakingContract");
    // staking = await Staking.deploy();
    // await staking.waitForDeployment();

    [, user] = await ethers.getSigners(); // Account #1 as user
  });

  it("should allow staking and unstaking ETH", async function () {
    const stakeAmount = ethers.parseEther("0.2");
    await staking.connect(user).stake({ value: stakeAmount });
    const userStake = await staking.getStake(user.address);
    expect(ethers.formatEther(userStake)).to.equal("0.2");

    await staking.connect(user).unstake();
    const finalStake = await staking.getStake(user.address);
    expect(ethers.formatEther(finalStake)).to.equal("0.0");
  });

  it("should revert if stake below minimum", async function () {
    const lowAmount = ethers.parseEther("0.05");
    await expect(
      staking.connect(user).stake({ value: lowAmount })
    ).to.be.revertedWith("Minimum 0.1 ETH required");
  });
});