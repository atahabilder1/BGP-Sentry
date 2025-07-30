module.exports = async ({ getNamedAccounts, deployments }) => {
  const { deploy } = deployments;
  const { deployer } = await getNamedAccounts();

  console.log(`🚀 Deploying from address: ${deployer}`);

  await deploy("StakingContract", {
    from: deployer,
    log: true,
  });
};

module.exports.tags = ["StakingContract"];
