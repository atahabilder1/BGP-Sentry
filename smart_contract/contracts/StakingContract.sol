// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Minimalist StakingContract for Native ETH Staking
/// @notice Non-RPKI nodes stake ETH, RPKI nodes can query stake status
/// @dev Simple staking with native ETH on any EVM-compatible chain

contract StakingContract {
    uint256 public minStakeAmount = 0.1 ether; // Example: 0.1 ETH minimum

    mapping(address => uint256) public stakes;

    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);

    /// @notice Stake native ETH into the contract
    /// @dev Payable function to receive ETH
    function stake() external payable {
        require(msg.value >= minStakeAmount, "Minimum 0.1 ETH required");

        stakes[msg.sender] += msg.value;
        emit Staked(msg.sender, msg.value);
    }

    /// @notice Unstake all staked ETH
    function unstake() external {
        uint256 amount = stakes[msg.sender];
        require(amount > 0, "No funds to unstake");

        stakes[msg.sender] = 0;
        payable(msg.sender).transfer(amount); // Send ETH back

        emit Unstaked(msg.sender, amount);
    }

    /// @notice View the staked ETH amount of a user
    function getStake(address user) external view returns (uint256) {
        return stakes[user];
    }
}