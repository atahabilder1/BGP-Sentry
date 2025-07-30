// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title StakingContract with Admin Control (Account #0 Admin: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266)
 * @notice Allows non-RPKI nodes to stake native ETH and admin to deduct stake
 * @dev Deployed on Hardhat; accepts random ETH values from 3.0 to 3.5 during testing
 */

contract StakingContract {
    uint256 public minStakeAmount = 0.1 ether;
    address public admin = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;

    mapping(address => uint256) public stakes;

    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event Deducted(address indexed user, uint256 amount, address indexed to);

    /// @notice Restrict access to only the admin address
    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    /// @notice Allow users to stake ETH (must be >= minStakeAmount)
    function stake() external payable {
        require(msg.value >= minStakeAmount, "Minimum 0.1 ETH required");
        stakes[msg.sender] += msg.value;
        emit Staked(msg.sender, msg.value);
    }

    /// @notice Allow users to unstake their full balance
    function unstake() external {
        uint256 amount = stakes[msg.sender];
        require(amount > 0, "No funds to unstake");
        stakes[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
        emit Unstaked(msg.sender, amount);
    }

    /// @notice Admin can deduct from a user's stake and transfer to admin
    /// @param user The address whose stake will be reduced
    /// @param amount The amount to deduct
    function deductStake(address user, uint256 amount) external onlyAdmin {
        require(stakes[user] >= amount, "Insufficient staked balance");
        stakes[user] -= amount;
        payable(admin).transfer(amount);
        emit Deducted(user, amount, admin);
    }

    /// @notice View a user’s staked ETH
    /// @param user The address to check
    /// @return The amount of ETH staked by that address
    function getStake(address user) external view returns (uint256) {
        return stakes[user];
    }
}
