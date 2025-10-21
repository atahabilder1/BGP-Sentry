#!/usr/bin/env python3
"""
=============================================================================
BGPCOIN Token Ledger - Incentive System for BGP-Sentry Blockchain
=============================================================================

Token Name: BGPCOIN
Purpose: Protocol-level incentive tokens for RPKI observer honesty and participation

Economic Model (Circular Economy):
┌─────────────────────────────────────────────────────────────────┐
│  Protocol Treasury (10,000,000 BGPCOIN)                        │
│         ↓                                                       │
│  RPKI Observers (Earn Rewards)                                 │
│         ↓                                                       │
│  Network Services (Governance, Analytics, Support)             │
│         ↓                                                       │
│  Coin Processing (50% Burn / 50% Recycle)                     │
│         ↓                                                       │
│  Back to Treasury (Sustainable)                                │
└─────────────────────────────────────────────────────────────────┘

Reward Formula:
    C_earned = C_base × A_accuracy × P_participation × Q_quality

Where:
- C_base: Base reward (10 coins/day monitoring, 100 coins attack detection)
- A_accuracy: Historical accuracy multiplier (0.5 - 1.5)
- P_participation: Participation consistency (0.8 - 1.2)
- Q_quality: Evidence quality (0.9 - 1.3)

Author: BGP-Sentry Team
=============================================================================
"""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import RPKI Node Registry
from rpki_node_registry import RPKINodeRegistry

class BGPCoinLedger:
    """
    Manages BGPCOIN token economy for BGP-Sentry blockchain.

    Implements circular economy with:
    - Limited supply (10 million total)
    - Reward distribution for block commits and voting
    - 50% burn / 50% recycle on spending
    - Governance mechanisms
    """

    def __init__(self, ledger_path="blockchain_data/state"):
        """
        Initialize BGPCOIN ledger.

        Args:
            ledger_path: Path to store token ledger data
        """
        self.ledger_dir = Path(ledger_path)
        self.ledger_file = self.ledger_dir / "bgpcoin_ledger.json"
        self.transaction_log = self.ledger_dir / "bgpcoin_transactions.jsonl"

        # Token configuration
        self.token_name = "BGPCOIN"
        self.token_symbol = "BGPC"
        self.total_supply = 10_000_000  # 10 million coins

        # Thread safety
        self.lock = threading.RLock()

        # Reward configuration
        self.rewards = {
            "block_commit": 10,           # Base reward for committing block
            "vote_approve": 1,            # Reward for voting approve
            "first_commit_bonus": 5,      # Bonus for being first to commit
            "attack_detection": 100,      # Large reward for detecting attack
            "daily_monitoring": 10,       # Daily reward for active monitoring
        }

        # Multiplier ranges (from proposal)
        self.multiplier_ranges = {
            "accuracy": (0.5, 1.5),       # Historical accuracy
            "participation": (0.8, 1.2),  # Participation consistency
            "quality": (0.9, 1.3)         # Evidence quality
        }

        # Penalty configuration
        self.penalties = {
            "false_reject": -2,           # Penalty for incorrect rejection
            "false_approve": -5,          # Penalty for approving fake announcement
            "missed_participation": -1,   # Penalty for not participating
        }

        # Initialize ledger data
        self.ledger_data = {
            "version": "1.0",
            "token_name": self.token_name,
            "token_symbol": self.token_symbol,
            "total_supply": self.total_supply,
            "protocol_treasury": self.total_supply,  # Initially all in treasury
            "balances": {},              # AS number -> balance
            "node_stats": {},            # AS number -> stats (accuracy, participation, quality)
            "total_burned": 0,           # Total coins permanently burned
            "total_recycled": 0,         # Total coins recycled to treasury
            "total_distributed": 0,      # Total coins distributed as rewards
            "last_updated": datetime.now().isoformat()
        }

        # Load existing ledger or initialize nodes with 0 balance
        self._load_ledger()

        # Initialize all RPKI nodes from registry if not already in ledger
        rpki_nodes = RPKINodeRegistry.get_all_rpki_nodes()
        for as_num in rpki_nodes:
            if as_num not in self.ledger_data["balances"]:
                self.ledger_data["balances"][as_num] = 0
                self.ledger_data["node_stats"][as_num] = {
                    "accuracy": 1.0,       # Start with neutral multiplier
                    "participation": 1.0,
                    "quality": 1.0,
                    "blocks_committed": 0,
                    "votes_cast": 0,
                    "correct_votes": 0,
                    "false_votes": 0,
                    "total_earned": 0,
                    "total_spent": 0
                }

        # Save initial state
        self._save_ledger()

    def _load_ledger(self):
        """Load BGPCOIN ledger from disk"""
        try:
            if self.ledger_file.exists():
                with open(self.ledger_file, 'r') as f:
                    loaded_data = json.load(f)

                # Merge with default structure (for backward compatibility)
                self.ledger_data.update(loaded_data)
                print(f"💰 Loaded BGPCOIN ledger: {len(self.ledger_data['balances'])} nodes")
            else:
                print(f"💰 Initializing new BGPCOIN ledger")

        except Exception as e:
            print(f"Error loading BGPCOIN ledger: {e}")

    def _save_ledger(self):
        """Save BGPCOIN ledger to disk atomically"""
        try:
            with self.lock:
                self.ledger_data["last_updated"] = datetime.now().isoformat()

                # Atomic write
                temp_file = self.ledger_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(self.ledger_data, f, indent=2)

                temp_file.replace(self.ledger_file)

        except Exception as e:
            print(f"Error saving BGPCOIN ledger: {e}")

    def _log_transaction(self, transaction_type: str, from_as: int, amount: float, details: Dict):
        """Log BGPCOIN transaction to transaction log"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": transaction_type,
                "from_as": from_as,
                "amount": amount,
                "details": details
            }

            with open(self.transaction_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            print(f"Error logging BGPCOIN transaction: {e}")

    def calculate_earned_coins(self, base_reward: float, as_number: int) -> float:
        """
        Calculate earned coins using the proposal formula:
        C_earned = C_base × A_accuracy × P_participation × Q_quality

        Args:
            base_reward: Base coin amount before multipliers
            as_number: AS number of the node

        Returns:
            Final earned amount after multipliers
        """
        try:
            stats = self.ledger_data["node_stats"].get(as_number, {})

            accuracy = stats.get("accuracy", 1.0)
            participation = stats.get("participation", 1.0)
            quality = stats.get("quality", 1.0)

            earned = base_reward * accuracy * participation * quality

            return round(earned, 2)

        except Exception as e:
            print(f"Error calculating earned coins: {e}")
            return base_reward

    def award_block_commit_reward(self, committer_as: int, voter_as_list: List[int],
                                   is_first: bool = False) -> Dict:
        """
        Award BGPCOIN for successfully committing a block.

        Args:
            committer_as: AS number that committed the block
            voter_as_list: List of AS numbers that voted approve
            is_first: True if this node was first to commit (bonus)

        Returns:
            Dict with reward details
        """
        try:
            with self.lock:
                # Calculate committer reward
                base_reward = self.rewards["block_commit"]
                if is_first:
                    base_reward += self.rewards["first_commit_bonus"]

                committer_reward = self.calculate_earned_coins(base_reward, committer_as)

                # Check treasury has enough coins
                if self.ledger_data["protocol_treasury"] < committer_reward:
                    print(f"⚠️ Treasury depleted! Cannot award {committer_reward} BGPCOIN")
                    return {"success": False, "reason": "treasury_depleted"}

                # Award to committer
                self.ledger_data["balances"][committer_as] += committer_reward
                self.ledger_data["protocol_treasury"] -= committer_reward
                self.ledger_data["total_distributed"] += committer_reward

                # Update committer stats
                self.ledger_data["node_stats"][committer_as]["blocks_committed"] += 1
                self.ledger_data["node_stats"][committer_as]["total_earned"] += committer_reward

                # Log transaction
                self._log_transaction("block_commit_reward", committer_as, committer_reward, {
                    "is_first": is_first,
                    "voters": voter_as_list
                })

                # Award voters
                voter_rewards = {}
                for voter_as in voter_as_list:
                    voter_reward = self.calculate_earned_coins(
                        self.rewards["vote_approve"],
                        voter_as
                    )

                    if self.ledger_data["protocol_treasury"] >= voter_reward:
                        self.ledger_data["balances"][voter_as] += voter_reward
                        self.ledger_data["protocol_treasury"] -= voter_reward
                        self.ledger_data["total_distributed"] += voter_reward

                        # Update voter stats
                        self.ledger_data["node_stats"][voter_as]["votes_cast"] += 1
                        self.ledger_data["node_stats"][voter_as]["correct_votes"] += 1
                        self.ledger_data["node_stats"][voter_as]["total_earned"] += voter_reward

                        voter_rewards[voter_as] = voter_reward

                        # Log voter reward
                        self._log_transaction("vote_reward", voter_as, voter_reward, {
                            "committer": committer_as
                        })

                # Save ledger
                self._save_ledger()

                result = {
                    "success": True,
                    "committer_as": committer_as,
                    "committer_reward": committer_reward,
                    "voter_rewards": voter_rewards,
                    "total_awarded": committer_reward + sum(voter_rewards.values()),
                    "treasury_balance": self.ledger_data["protocol_treasury"]
                }

                print(f"💰 BGPCOIN REWARDS:")
                print(f"   AS{committer_as} (committer): +{committer_reward} BGPCOIN")
                for voter_as, reward in voter_rewards.items():
                    print(f"   AS{voter_as} (voter): +{reward} BGPCOIN")
                print(f"   Treasury remaining: {self.ledger_data['protocol_treasury']:,.0f} BGPCOIN")

                return result

        except Exception as e:
            print(f"Error awarding block commit reward: {e}")
            return {"success": False, "error": str(e)}

    def spend_coins(self, as_number: int, amount: float, purpose: str) -> bool:
        """
        Spend BGPCOIN with 50% burn / 50% recycle mechanism.

        Args:
            as_number: AS number spending coins
            amount: Amount to spend
            purpose: Purpose of spending (governance, analytics, support)

        Returns:
            True if successful
        """
        try:
            with self.lock:
                # Check balance
                if self.ledger_data["balances"].get(as_number, 0) < amount:
                    print(f"❌ AS{as_number} insufficient balance: {amount} BGPCOIN needed")
                    return False

                # Deduct from balance
                self.ledger_data["balances"][as_number] -= amount

                # 50% burn, 50% recycle (from proposal)
                burned = amount * 0.5
                recycled = amount * 0.5

                self.ledger_data["total_burned"] += burned
                self.ledger_data["total_recycled"] += recycled
                self.ledger_data["protocol_treasury"] += recycled

                # Update stats
                self.ledger_data["node_stats"][as_number]["total_spent"] += amount

                # Log transaction
                self._log_transaction("spend", as_number, amount, {
                    "purpose": purpose,
                    "burned": burned,
                    "recycled": recycled
                })

                # Save ledger
                self._save_ledger()

                print(f"💸 AS{as_number} spent {amount} BGPCOIN for {purpose}")
                print(f"   🔥 Burned: {burned} BGPCOIN")
                print(f"   ♻️  Recycled: {recycled} BGPCOIN")

                return True

        except Exception as e:
            print(f"Error spending coins: {e}")
            return False

    def get_balance(self, as_number: int) -> float:
        """Get BGPCOIN balance for a node"""
        return self.ledger_data["balances"].get(as_number, 0)

    def get_node_stats(self, as_number: int) -> Dict:
        """Get statistics for a node"""
        return self.ledger_data["node_stats"].get(as_number, {})

    def get_ledger_summary(self) -> Dict:
        """Get summary of BGPCOIN economy"""
        return {
            "token_name": self.token_name,
            "total_supply": self.total_supply,
            "treasury_balance": self.ledger_data["protocol_treasury"],
            "total_distributed": self.ledger_data["total_distributed"],
            "total_burned": self.ledger_data["total_burned"],
            "total_recycled": self.ledger_data["total_recycled"],
            "circulating_supply": sum(self.ledger_data["balances"].values()),
            "nodes_count": len(self.ledger_data["balances"])
        }

    def update_node_multipliers(self, as_number: int, accuracy: float = None,
                                participation: float = None, quality: float = None):
        """
        Update node multipliers based on performance.

        Args:
            as_number: AS number
            accuracy: New accuracy multiplier (0.5 - 1.5)
            participation: New participation multiplier (0.8 - 1.2)
            quality: New quality multiplier (0.9 - 1.3)
        """
        try:
            with self.lock:
                stats = self.ledger_data["node_stats"][as_number]

                if accuracy is not None:
                    # Clamp to valid range
                    accuracy = max(0.5, min(1.5, accuracy))
                    stats["accuracy"] = accuracy

                if participation is not None:
                    participation = max(0.8, min(1.2, participation))
                    stats["participation"] = participation

                if quality is not None:
                    quality = max(0.9, min(1.3, quality))
                    stats["quality"] = quality

                self._save_ledger()

        except Exception as e:
            print(f"Error updating multipliers: {e}")

    def award_special_reward(self, as_number: int, amount: float, reason: str,
                            details: Dict = None) -> bool:
        """
        Award special BGPCOIN reward (e.g., attack detection).

        Args:
            as_number: AS number to award
            amount: Amount to award
            reason: Reason for reward
            details: Additional details

        Returns:
            True if successful
        """
        try:
            with self.lock:
                # Check treasury has enough coins
                if self.ledger_data["protocol_treasury"] < amount:
                    print(f"⚠️ Treasury depleted! Cannot award {amount} BGPCOIN")
                    return False

                # Award coins
                self.ledger_data["balances"][as_number] += amount
                self.ledger_data["protocol_treasury"] -= amount
                self.ledger_data["total_distributed"] += amount

                # Update stats
                self.ledger_data["node_stats"][as_number]["total_earned"] += amount

                # Log transaction
                self._log_transaction("special_reward", as_number, amount, {
                    "reason": reason,
                    "details": details or {}
                })

                # Save ledger
                self._save_ledger()

                return True

        except Exception as e:
            print(f"Error awarding special reward: {e}")
            return False

    def apply_penalty(self, as_number: int, amount: float, reason: str,
                     details: Dict = None) -> bool:
        """
        Apply BGPCOIN penalty (e.g., false accusation).

        Args:
            as_number: AS number to penalize
            amount: Penalty amount (positive value)
            reason: Reason for penalty
            details: Additional details

        Returns:
            True if successful
        """
        try:
            with self.lock:
                # Deduct penalty from balance (can go negative)
                self.ledger_data["balances"][as_number] -= amount

                # Log transaction
                self._log_transaction("penalty", as_number, -amount, {
                    "reason": reason,
                    "details": details or {}
                })

                # Save ledger
                self._save_ledger()

                return True

        except Exception as e:
            print(f"Error applying penalty: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("BGPCOIN TOKEN LEDGER - TEST")
    print("=" * 80)
    print()

    # Initialize ledger
    ledger = BGPCoinLedger("test_blockchain_data/state")

    # Show initial state
    summary = ledger.get_ledger_summary()
    print(f"📊 Initial State:")
    print(f"   Total Supply: {summary['total_supply']:,} BGPCOIN")
    print(f"   Treasury: {summary['treasury_balance']:,} BGPCOIN")
    print(f"   Nodes: {summary['nodes_count']}")
    print()

    # Test block commit reward
    print("🎯 Test 1: Block Commit Reward")
    result = ledger.award_block_commit_reward(
        committer_as=1,
        voter_as_list=[3, 5, 7],
        is_first=True  # First to commit bonus
    )
    print()

    # Check balances
    print("💰 Node Balances:")
    for as_num in [1, 3, 5, 7]:
        balance = ledger.get_balance(as_num)
        print(f"   AS{as_num:02d}: {balance} BGPCOIN")
    print()

    # Test spending with burn/recycle
    print("💸 Test 2: Spending BGPCOIN (50% burn / 50% recycle)")
    ledger.spend_coins(as_number=1, amount=10, purpose="governance_vote")
    print()

    # Final summary
    summary = ledger.get_ledger_summary()
    print("📊 Final State:")
    print(f"   Treasury: {summary['treasury_balance']:,.2f} BGPCOIN")
    print(f"   Distributed: {summary['total_distributed']:,.2f} BGPCOIN")
    print(f"   Burned: {summary['total_burned']:,.2f} BGPCOIN")
    print(f"   Recycled: {summary['total_recycled']:,.2f} BGPCOIN")
    print(f"   Circulating: {summary['circulating_supply']:,.2f} BGPCOIN")
