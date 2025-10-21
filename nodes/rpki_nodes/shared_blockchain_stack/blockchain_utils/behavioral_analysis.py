#!/usr/bin/env python3
"""
=============================================================================
Monthly Behavioral Analysis - Long-term BGPCOIN Rewards
=============================================================================

Purpose: Analyze long-term node behavior and adjust multipliers/rewards

This system runs monthly to:
1. Analyze each node's voting accuracy over the past month
2. Assess participation consistency
3. Evaluate evidence quality
4. Update multipliers (accuracy, participation, quality)
5. Award bonus BGPCOIN for exceptional behavior
6. Penalize persistent misbehavior

Analysis Metrics:
- Voting Accuracy: % of correct votes (approve when consensus approves)
- Participation Rate: % of votes cast vs total opportunities
- Quality Score: Based on evidence provided with votes
- Behavioral Patterns: Detect anomalies, attacks, honest mistakes

Multiplier Adjustments (from proposal):
- Accuracy: 0.5 - 1.5 (based on voting correctness)
- Participation: 0.8 - 1.2 (based on active participation)
- Quality: 0.9 - 1.3 (based on evidence quality)

Monthly Bonus Rewards:
- Top Performer: 500 BGPCOIN
- High Accuracy (>95%): 200 BGPCOIN
- Perfect Participation (100%): 100 BGPCOIN
- Consistent Quality: 150 BGPCOIN

Penalties:
- Low Accuracy (<50%): Multiplier reduced, -100 BGPCOIN
- Poor Participation (<30%): Multiplier reduced, -50 BGPCOIN
- Suspected Malicious: Severe multiplier reduction, investigation

Author: BGP-Sentry Team
=============================================================================
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import statistics

class BehavioralAnalyzer:
    """
    Analyzes long-term node behavior and adjusts BGPCOIN rewards.
    """

    def __init__(self, blockchain_interface, bgpcoin_ledger, analysis_path="blockchain_data/state"):
        """
        Initialize behavioral analyzer.

        Args:
            blockchain_interface: BlockchainInterface instance
            bgpcoin_ledger: BGPCoinLedger instance
            analysis_path: Path to store analysis results
        """
        self.blockchain = blockchain_interface
        self.ledger = bgpcoin_ledger
        self.analysis_dir = Path(analysis_path)
        self.analysis_file = self.analysis_dir / "behavioral_analysis.json"
        self.history_file = self.analysis_dir / "analysis_history.jsonl"

        # Reward thresholds
        self.thresholds = {
            "excellent_accuracy": 0.95,    # >95% accuracy
            "good_accuracy": 0.80,         # >80% accuracy
            "poor_accuracy": 0.50,         # <50% accuracy (penalty)

            "perfect_participation": 1.0,  # 100% participation
            "good_participation": 0.70,    # >70% participation
            "poor_participation": 0.30,    # <30% participation (penalty)

            "high_quality": 1.2,           # Quality multiplier >1.2
            "low_quality": 1.0             # Quality multiplier <1.0
        }

        # Monthly bonus rewards
        self.monthly_bonuses = {
            "top_performer": 500,          # Best overall node
            "high_accuracy": 200,          # >95% accuracy
            "perfect_participation": 100,  # 100% participation
            "consistent_quality": 150      # High quality evidence
        }

        # Penalties
        self.monthly_penalties = {
            "low_accuracy": -100,          # <50% accuracy
            "poor_participation": -50,     # <30% participation
            "suspected_malicious": -500    # Detected malicious behavior
        }

    def run_monthly_analysis(self, days=30):
        """
        Run monthly behavioral analysis for all nodes.

        Args:
            days: Number of days to analyze (default 30)

        Returns:
            Dict with analysis results and rewards awarded
        """
        print("=" * 80)
        print(f"📊 MONTHLY BEHAVIORAL ANALYSIS ({days} days)")
        print("=" * 80)
        print()

        # Get all nodes
        nodes = list(self.ledger.ledger_data["balances"].keys())

        # Analyze each node
        results = {}
        for as_number in nodes:
            result = self._analyze_node(as_number, days)
            results[as_number] = result

        # Calculate rankings
        rankings = self._calculate_rankings(results)

        # Award bonuses and update multipliers
        awards = self._distribute_monthly_rewards(results, rankings)

        # Save analysis results
        self._save_analysis(results, rankings, awards)

        print()
        print("=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)

        return {
            "results": results,
            "rankings": rankings,
            "awards": awards
        }

    def _analyze_node(self, as_number: int, days: int) -> Dict:
        """
        Analyze single node's behavior over time period.

        Args:
            as_number: AS number to analyze
            days: Number of days to analyze

        Returns:
            Dict with node analysis results
        """
        print(f"🔍 Analyzing AS{as_number}...")

        # Get node stats
        stats = self.ledger.ledger_data["node_stats"].get(as_number, {})

        # Calculate metrics
        total_votes = stats.get("votes_cast", 0)
        correct_votes = stats.get("correct_votes", 0)
        false_votes = stats.get("false_votes", 0)
        blocks_committed = stats.get("blocks_committed", 0)

        # Voting accuracy
        if total_votes > 0:
            accuracy = correct_votes / total_votes
        else:
            accuracy = 0.0

        # Participation rate (assuming ~10 voting opportunities per day)
        expected_votes = days * 10
        participation_rate = min(1.0, total_votes / expected_votes) if expected_votes > 0 else 0

        # Current quality multiplier
        quality = stats.get("quality", 1.0)

        # Behavioral flags
        flags = []
        if accuracy < self.thresholds["poor_accuracy"]:
            flags.append("low_accuracy")
        if participation_rate < self.thresholds["poor_participation"]:
            flags.append("poor_participation")
        if false_votes > correct_votes:
            flags.append("suspected_malicious")

        result = {
            "as_number": as_number,
            "total_votes": total_votes,
            "correct_votes": correct_votes,
            "false_votes": false_votes,
            "blocks_committed": blocks_committed,
            "accuracy": accuracy,
            "participation_rate": participation_rate,
            "quality_multiplier": quality,
            "flags": flags,
            "current_balance": self.ledger.get_balance(as_number)
        }

        print(f"   Accuracy: {accuracy:.1%}, Participation: {participation_rate:.1%}, Blocks: {blocks_committed}")

        return result

    def _calculate_rankings(self, results: Dict) -> Dict:
        """
        Calculate node rankings based on analysis.

        Args:
            results: Analysis results for all nodes

        Returns:
            Dict with rankings
        """
        # Calculate overall scores
        scores = {}
        for as_number, result in results.items():
            # Overall score: weighted average
            score = (
                result["accuracy"] * 0.5 +          # 50% weight on accuracy
                result["participation_rate"] * 0.3 + # 30% weight on participation
                result["quality_multiplier"] * 0.2   # 20% weight on quality
            )
            scores[as_number] = score

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        rankings = {
            "top_performer": ranked[0][0] if ranked else None,
            "top_5": [as_num for as_num, _ in ranked[:5]],
            "scores": scores
        }

        return rankings

    def _distribute_monthly_rewards(self, results: Dict, rankings: Dict) -> Dict:
        """
        Distribute monthly bonus rewards and update multipliers.

        Args:
            results: Analysis results
            rankings: Node rankings

        Returns:
            Dict with awards distributed
        """
        print()
        print("💰 DISTRIBUTING MONTHLY REWARDS")
        print()

        awards = {}

        for as_number, result in results.items():
            node_awards = {
                "bonuses": {},
                "penalties": {},
                "multiplier_changes": {},
                "total_bgpcoin": 0
            }

            # Update multipliers based on performance
            new_accuracy_mult = self._calculate_accuracy_multiplier(result["accuracy"])
            new_participation_mult = self._calculate_participation_multiplier(result["participation_rate"])

            # Apply multiplier changes
            self.ledger.update_node_multipliers(
                as_number,
                accuracy=new_accuracy_mult,
                participation=new_participation_mult
            )

            node_awards["multiplier_changes"]["accuracy"] = new_accuracy_mult
            node_awards["multiplier_changes"]["participation"] = new_participation_mult

            # Top performer bonus
            if as_number == rankings["top_performer"]:
                bonus = self.monthly_bonuses["top_performer"]
                node_awards["bonuses"]["top_performer"] = bonus
                node_awards["total_bgpcoin"] += bonus
                print(f"🏆 AS{as_number}: Top Performer (+{bonus} BGPCOIN)")

            # High accuracy bonus
            if result["accuracy"] >= self.thresholds["excellent_accuracy"]:
                bonus = self.monthly_bonuses["high_accuracy"]
                node_awards["bonuses"]["high_accuracy"] = bonus
                node_awards["total_bgpcoin"] += bonus
                print(f"🎯 AS{as_number}: Excellent Accuracy (+{bonus} BGPCOIN)")

            # Perfect participation bonus
            if result["participation_rate"] >= self.thresholds["perfect_participation"]:
                bonus = self.monthly_bonuses["perfect_participation"]
                node_awards["bonuses"]["perfect_participation"] = bonus
                node_awards["total_bgpcoin"] += bonus
                print(f"✅ AS{as_number}: Perfect Participation (+{bonus} BGPCOIN)")

            # Quality bonus
            if result["quality_multiplier"] >= self.thresholds["high_quality"]:
                bonus = self.monthly_bonuses["consistent_quality"]
                node_awards["bonuses"]["consistent_quality"] = bonus
                node_awards["total_bgpcoin"] += bonus
                print(f"⭐ AS{as_number}: High Quality (+{bonus} BGPCOIN)")

            # Penalties
            if "low_accuracy" in result["flags"]:
                penalty = self.monthly_penalties["low_accuracy"]
                node_awards["penalties"]["low_accuracy"] = penalty
                node_awards["total_bgpcoin"] += penalty  # Negative
                print(f"⚠️  AS{as_number}: Low Accuracy ({penalty} BGPCOIN)")

            if "poor_participation" in result["flags"]:
                penalty = self.monthly_penalties["poor_participation"]
                node_awards["penalties"]["poor_participation"] = penalty
                node_awards["total_bgpcoin"] += penalty  # Negative
                print(f"⚠️  AS{as_number}: Poor Participation ({penalty} BGPCOIN)")

            if "suspected_malicious" in result["flags"]:
                penalty = self.monthly_penalties["suspected_malicious"]
                node_awards["penalties"]["suspected_malicious"] = penalty
                node_awards["total_bgpcoin"] += penalty  # Negative
                print(f"🚨 AS{as_number}: Suspected Malicious ({penalty} BGPCOIN)")

            # Award total to node (can be negative for penalties)
            if node_awards["total_bgpcoin"] > 0:
                # Positive reward - comes from treasury
                current_balance = self.ledger.get_balance(as_number)
                self.ledger.ledger_data["balances"][as_number] = current_balance + node_awards["total_bgpcoin"]
                self.ledger.ledger_data["protocol_treasury"] -= node_awards["total_bgpcoin"]
                self.ledger.ledger_data["total_distributed"] += node_awards["total_bgpcoin"]
            elif node_awards["total_bgpcoin"] < 0:
                # Penalty - deduct from node balance
                current_balance = self.ledger.get_balance(as_number)
                deduction = abs(node_awards["total_bgpcoin"])
                self.ledger.ledger_data["balances"][as_number] = max(0, current_balance - deduction)

            awards[as_number] = node_awards

        # Save ledger
        self.ledger._save_ledger()

        return awards

    def _calculate_accuracy_multiplier(self, accuracy: float) -> float:
        """
        Calculate accuracy multiplier based on voting accuracy.
        Range: 0.5 - 1.5 (from proposal)

        Args:
            accuracy: Voting accuracy (0.0 - 1.0)

        Returns:
            Multiplier value
        """
        if accuracy >= 0.95:
            return 1.5  # Excellent
        elif accuracy >= 0.80:
            return 1.2  # Good
        elif accuracy >= 0.60:
            return 1.0  # Average
        elif accuracy >= 0.40:
            return 0.7  # Below average
        else:
            return 0.5  # Poor

    def _calculate_participation_multiplier(self, participation: float) -> float:
        """
        Calculate participation multiplier.
        Range: 0.8 - 1.2 (from proposal)

        Args:
            participation: Participation rate (0.0 - 1.0)

        Returns:
            Multiplier value
        """
        if participation >= 0.90:
            return 1.2  # Excellent participation
        elif participation >= 0.70:
            return 1.1  # Good participation
        elif participation >= 0.50:
            return 1.0  # Average
        elif participation >= 0.30:
            return 0.9  # Below average
        else:
            return 0.8  # Poor participation

    def _save_analysis(self, results: Dict, rankings: Dict, awards: Dict):
        """Save analysis results to file"""
        try:
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "results": results,
                "rankings": rankings,
                "awards": awards
            }

            # Save current analysis
            with open(self.analysis_file, 'w') as f:
                json.dump(analysis_data, f, indent=2)

            # Append to history
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(analysis_data) + '\n')

            print()
            print(f"📁 Analysis saved to {self.analysis_file}")

        except Exception as e:
            print(f"Error saving analysis: {e}")


# Example usage and testing
if __name__ == "__main__":
    from blockchain_interface import BlockchainInterface
    from bgpcoin_ledger import BGPCoinLedger

    print("=" * 80)
    print("BEHAVIORAL ANALYSIS - TEST")
    print("=" * 80)
    print()

    # Initialize components
    blockchain = BlockchainInterface("test_blockchain_data/chain")
    ledger = BGPCoinLedger("test_blockchain_data/state")
    analyzer = BehavioralAnalyzer(blockchain, ledger, "test_blockchain_data/state")

    # Simulate some activity
    print("Simulating node activity...")
    ledger.ledger_data["node_stats"][1]["votes_cast"] = 250
    ledger.ledger_data["node_stats"][1]["correct_votes"] = 245  # 98% accuracy
    ledger.ledger_data["node_stats"][1]["blocks_committed"] = 15

    ledger.ledger_data["node_stats"][3]["votes_cast"] = 180
    ledger.ledger_data["node_stats"][3]["correct_votes"] = 150  # 83% accuracy
    ledger.ledger_data["node_stats"][3]["blocks_committed"] = 8

    ledger.ledger_data["node_stats"][5]["votes_cast"] = 50
    ledger.ledger_data["node_stats"][5]["correct_votes"] = 20   # 40% accuracy (poor)
    ledger.ledger_data["node_stats"][5]["blocks_committed"] = 2
    print()

    # Run monthly analysis
    result = analyzer.run_monthly_analysis(days=30)

    print()
    print("📊 Top 5 Nodes:")
    for i, as_num in enumerate(result["rankings"]["top_5"], 1):
        score = result["rankings"]["scores"][as_num]
        print(f"   {i}. AS{as_num:02d} - Score: {score:.3f}")
