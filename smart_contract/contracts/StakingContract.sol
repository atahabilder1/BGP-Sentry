// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title StakingContract for USDC-based Staking
/// @notice Non-RPKI nodes stake USDC, RPKI nodes can verify stake status
/// @dev Uses ERC-20 interface (e.g., USDC), works on any EVM-compatible chain

interface IERC20 {
    function transferFrom(
        address sender,
        address recipient,
        uint256 amount
    ) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract StakingContract {
    address public owner;
    IERC20 public usdcToken;
    uint256 public minStakeAmount = 100 * (10 ** 6); // 100 USDC (6 decimals)

    mapping(address => uint256) public stakes;

    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);

    constructor(address _usdcTokenAddress) {
        owner = msg.sender;
        usdcToken = IERC20(_usdcTokenAddress);
    }

    /// @notice Stake USDC tokens into the contract
    /// @param amount Amount of USDC to stake (6 decimal precision)
    function stake(uint256 amount) external {
        require(amount >= minStakeAmount, "Minimum 100 USDC required");
        require(
            usdcToken.transferFrom(msg.sender, address(this), amount),
            "USDC transfer failed"
        );

        stakes[msg.sender] += amount;
        emit Staked(msg.sender, amount);
    }

    /// @notice Unstake all staked USDC tokens
    function unstake() external {
        uint256 amount = stakes[msg.sender];
        require(amount > 0, "No funds to unstake");

        stakes[msg.sender] = 0;
        require(usdcToken.transfer(msg.sender, amount), "USDC unstake failed");

        emit Unstaked(msg.sender, amount);
    }

    /// @notice View the staked USDC amount of a user
    function getStake(address user) external view returns (uint256) {
        return stakes[user];
    }
}
