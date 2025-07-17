const hre = require("hardhat");

async function main() {
  // Get the contract factory
  const StakingContract = await hre.ethers.getContractFactory(
    "StakingContract"
  );

  // Deploy the contract
  const stakingContract = await StakingContract.deploy();

  // Wait for deployment to complete
  await stakingContract.waitForDeployment();

  // Log the contract address
  console.log(
    "StakingContract deployed to:",
    await stakingContract.getAddress()
  );
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
