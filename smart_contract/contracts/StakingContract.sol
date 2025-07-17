pragma solidity ^0.8.0;

contract StakingContract {
    address public owner;
    uint256 public minStakeAmount = 100 * (10 ** 6); // 100 USDC with 6 decimals

    // Maps wallet address to staked amount
    mapping(address => uint256) public stakes;

    // Events
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    // Stake USDC
    function stake() external payable {
        require(
            msg.value >= minStakeAmount,
            "Minimum 100 USDC required to stake"
        );
        stakes[msg.sender] += msg.value;
        emit Staked(msg.sender, msg.value);
    }

    // Unstake funds (for future use)
    function unstake() external {
        uint256 amount = stakes[msg.sender];
        require(amount > 0, "No funds to unstake");
        stakes[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
        emit Unstaked(msg.sender, amount);
    }

    // View current stake
    function getStake(address user) external view returns (uint256) {
        return stakes[user];
    }
}