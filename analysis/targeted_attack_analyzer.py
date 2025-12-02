#!/usr/bin/env python3
"""
Targeted Attack & Unconfirmed Transaction Analyzer

This script performs post-hoc analysis focusing on:
1. SINGLE_WITNESS transactions (0 votes - potential targeted attacks)
2. INSUFFICIENT_CONSENSUS transactions (1-2 votes - partial agreement)
3. Chronological misbehavior patterns (timing, repeated attempts)
4. Correlation of single-witness events across nodes
5. Potential upgrade candidates (low consensus → high confidence)

Usage:
    python3 targeted_attack_analyzer.py <experiment_results_dir>

Example:
    python3 targeted_attack_analyzer.py ../experiment_results/run_2025_12_02_14_30/
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import statistics


class TargetedAttackAnalyzer:
    """Analyzes targeted attacks and unconfirmed transactions from experiment results"""

    def __init__(self, experiment_dir: str):
        self.experiment_dir = Path(experiment_dir)
        self.nodes_dir = self.experiment_dir / "nodes"

        # Data structures for analysis
        self.single_witness_txs = []  # 0 votes
        self.insufficient_consensus_txs = []  # 1-2 votes
        self.confirmed_txs = []  # 3+ votes

        # Cross-node correlation
        self.prefix_patterns = defaultdict(list)  # {(prefix, asn): [transactions]}
        self.temporal_clusters = []  # Time-based groupings

        # Misbehavior tracking
        self.repeated_attempts = defaultdict(int)  # {(prefix, asn): count}
        self.upgrade_candidates = []  # Transactions that might deserve upgrade

        print(f"[*] Initializing analyzer for: {self.experiment_dir}")

    def load_all_blockchains(self) -> Dict[str, List[dict]]:
        """Load blockchain data from all nodes"""
        blockchains = {}

        if not self.nodes_dir.exists():
            print(f"[!] Error: Nodes directory not found: {self.nodes_dir}")
            return blockchains

        node_dirs = sorted(self.nodes_dir.glob("as*"))

        for node_dir in node_dirs:
            node_name = node_dir.name
            blockchain_file = node_dir / "blockchain_node" / "blockchain_data" / "chain" / "blockchain.json"

            if not blockchain_file.exists():
                print(f"[!] Warning: Blockchain not found for {node_name}")
                continue

            try:
                with open(blockchain_file, 'r') as f:
                    data = json.load(f)
                    blockchain = data.get("blocks", [])
                    blockchains[node_name] = blockchain
                    print(f"[+] Loaded {len(blockchain)} blocks from {node_name}")
            except Exception as e:
                print(f"[!] Error loading {node_name}: {e}")

        return blockchains

    def extract_transactions_by_consensus_status(self, blockchains: Dict[str, List[dict]]):
        """Categorize transactions by consensus status"""
        print("\n" + "="*80)
        print("EXTRACTING TRANSACTIONS BY CONSENSUS STATUS")
        print("="*80)

        # Use first node as reference (all nodes should have identical blockchains)
        if not blockchains:
            print("[!] No blockchain data available")
            return

        reference_node = list(blockchains.keys())[0]
        blockchain = blockchains[reference_node]

        for block in blockchain:
            for tx in block.get("transactions", []):
                consensus_status = tx.get("consensus_status", "UNKNOWN")
                approve_count = tx.get("approve_count", 0)
                signature_count = tx.get("signature_count", 0)
                consensus_reached = tx.get("consensus_reached", False)

                # If no explicit status, infer from signature count and consensus_reached flag
                if consensus_status == "UNKNOWN":
                    if consensus_reached or signature_count >= 3:
                        consensus_status = "CONFIRMED"
                        approve_count = signature_count
                    elif signature_count >= 1:
                        consensus_status = "INSUFFICIENT_CONSENSUS"
                        approve_count = signature_count
                    else:
                        consensus_status = "SINGLE_WITNESS"
                        approve_count = 0

                if consensus_status == "SINGLE_WITNESS" or approve_count == 0:
                    self.single_witness_txs.append(tx)
                elif consensus_status == "INSUFFICIENT_CONSENSUS" or (0 < approve_count < 3):
                    self.insufficient_consensus_txs.append(tx)
                elif consensus_status == "CONFIRMED" or approve_count >= 3:
                    self.confirmed_txs.append(tx)

                # Track prefix patterns for all transactions
                prefix = tx.get("ip_prefix")
                sender_asn = tx.get("sender_asn")
                if prefix and sender_asn:
                    key = (prefix, sender_asn)
                    self.prefix_patterns[key].append(tx)
                    self.repeated_attempts[key] += 1

        print(f"\n[+] Transaction Distribution:")
        print(f"    - CONFIRMED (3+ votes):              {len(self.confirmed_txs)}")
        print(f"    - INSUFFICIENT_CONSENSUS (1-2 votes): {len(self.insufficient_consensus_txs)}")
        print(f"    - SINGLE_WITNESS (0 votes):           {len(self.single_witness_txs)}")
        print(f"    - TOTAL:                              {len(self.confirmed_txs) + len(self.insufficient_consensus_txs) + len(self.single_witness_txs)}")

    def analyze_single_witness_transactions(self):
        """Deep dive into SINGLE_WITNESS transactions (potential targeted attacks)"""
        print("\n" + "="*80)
        print("ANALYZING SINGLE_WITNESS TRANSACTIONS (0 Votes)")
        print("="*80)

        if not self.single_witness_txs:
            print("[*] No SINGLE_WITNESS transactions found (all transactions reached consensus)")
            return

        print(f"\n[!] Found {len(self.single_witness_txs)} SINGLE_WITNESS transactions")
        print("[!] These are potential targeted attacks or node-specific observations\n")

        # Analyze by attack status
        attack_txs = [tx for tx in self.single_witness_txs if tx.get("is_attack", False)]
        non_attack_txs = [tx for tx in self.single_witness_txs if not tx.get("is_attack", False)]

        print(f"Breakdown by Attack Status:")
        print(f"    - Marked as ATTACK:     {len(attack_txs)}")
        print(f"    - Marked as LEGITIMATE: {len(non_attack_txs)}")

        # This is a RED FLAG: legitimate announcements with 0 votes
        if non_attack_txs:
            print(f"\n[!] RED FLAG: {len(non_attack_txs)} legitimate announcements with 0 votes!")
            print("    Possible reasons:")
            print("    1. Network partition (node isolated)")
            print("    2. Timing issue (votes arrived after timeout)")
            print("    3. Node malfunction (observers didn't broadcast)")
            print("    4. Truly unique observation (only one node saw it)")

        # Analyze by observer
        observer_counts = Counter([tx.get("observer_asn") for tx in self.single_witness_txs])
        print(f"\nSINGLE_WITNESS by Observer Node:")
        for observer_asn, count in observer_counts.most_common():
            print(f"    - AS{observer_asn}: {count} transactions")

        # Analyze by prefix
        prefix_counts = Counter([tx.get("ip_prefix") for tx in self.single_witness_txs])
        print(f"\nSINGLE_WITNESS by IP Prefix (Top 10):")
        for prefix, count in prefix_counts.most_common(10):
            print(f"    - {prefix}: {count} transactions")

        # Temporal analysis
        timestamps = [tx.get("timestamp") for tx in self.single_witness_txs if tx.get("timestamp")]
        if timestamps and len(timestamps) > 1:
            print(f"\nTemporal Distribution:")
            print(f"    - First SINGLE_WITNESS: {min(timestamps)}")
            print(f"    - Last SINGLE_WITNESS:  {max(timestamps)}")
            # Note: timestamps might be strings, so we can't calculate span
            if isinstance(timestamps[0], (int, float)):
                print(f"    - Time span: {max(timestamps) - min(timestamps):.2f} seconds")

    def analyze_insufficient_consensus_transactions(self):
        """Analyze INSUFFICIENT_CONSENSUS transactions (1-2 votes)"""
        print("\n" + "="*80)
        print("ANALYZING INSUFFICIENT_CONSENSUS TRANSACTIONS (1-2 Votes)")
        print("="*80)

        if not self.insufficient_consensus_txs:
            print("[*] No INSUFFICIENT_CONSENSUS transactions found")
            return

        print(f"\n[*] Found {len(self.insufficient_consensus_txs)} INSUFFICIENT_CONSENSUS transactions")
        print("[*] These represent partial agreement (not enough for full consensus)\n")

        # Breakdown by vote count
        vote_1 = [tx for tx in self.insufficient_consensus_txs if tx.get("approve_count") == 1]
        vote_2 = [tx for tx in self.insufficient_consensus_txs if tx.get("approve_count") == 2]

        print(f"Breakdown by Vote Count:")
        print(f"    - 1 approve vote:  {len(vote_1)}")
        print(f"    - 2 approve votes: {len(vote_2)}")

        # Analyze by attack status
        attack_txs = [tx for tx in self.insufficient_consensus_txs if tx.get("is_attack", False)]
        non_attack_txs = [tx for tx in self.insufficient_consensus_txs if not tx.get("is_attack", False)]

        print(f"\nBreakdown by Attack Status:")
        print(f"    - Marked as ATTACK:     {len(attack_txs)}")
        print(f"    - Marked as LEGITIMATE: {len(non_attack_txs)}")

        # Analyze if attacks got more/less votes
        if attack_txs:
            attack_votes = [tx.get("approve_count", 0) for tx in attack_txs]
            print(f"\nAttack Transactions Voting Pattern:")
            print(f"    - Average approve votes: {statistics.mean(attack_votes):.2f}")
            print(f"    - This suggests: {'Attacks are being questioned by network' if statistics.mean(attack_votes) < 1.5 else 'Attacks are getting some support'}")

        # Find upgrade candidates (2 votes - close to consensus)
        if vote_2:
            print(f"\n[*] UPGRADE CANDIDATES: {len(vote_2)} transactions with 2 votes")
            print("    These are ONE VOTE AWAY from full consensus (3/9)")
            print("    Consider manual review for potential upgrade to CONFIRMED")

            for tx in vote_2[:5]:  # Show first 5 examples
                prefix = tx.get("ip_prefix")
                sender_asn = tx.get("sender_asn")
                is_attack = tx.get("is_attack", False)
                print(f"    - {prefix} from AS{sender_asn} ({'ATTACK' if is_attack else 'LEGITIMATE'})")

    def analyze_chronological_misbehavior(self):
        """Detect chronological misbehavior patterns"""
        print("\n" + "="*80)
        print("ANALYZING CHRONOLOGICAL MISBEHAVIOR PATTERNS")
        print("="*80)

        # Pattern 1: Repeated attempts (same prefix/ASN multiple times)
        repeated = {k: v for k, v in self.repeated_attempts.items() if v > 5}

        if repeated:
            print(f"\n[!] REPEATED ATTEMPTS DETECTED:")
            print(f"    Found {len(repeated)} (prefix, ASN) pairs with >5 announcements")
            print("    This could indicate:")
            print("    1. Route flapping (legitimate but unstable)")
            print("    2. Attack retry attempts (malicious)")
            print("    3. BGP instability (network issues)\n")

            for (prefix, asn), count in sorted(repeated.items(), key=lambda x: x[1], reverse=True)[:10]:
                txs = self.prefix_patterns[(prefix, asn)]
                attack_count = sum(1 for tx in txs if tx.get("is_attack", False))
                print(f"    - {prefix} from AS{asn}: {count} attempts ({attack_count} marked as attacks)")
        else:
            print("\n[+] No excessive repeated attempts detected")

        # Pattern 2: Burst attacks (many transactions in short time)
        print(f"\n[*] TEMPORAL BURST ANALYSIS:")
        self._detect_temporal_bursts()

        # Pattern 3: Escalation pattern (SINGLE_WITNESS -> INSUFFICIENT -> CONFIRMED)
        print(f"\n[*] CONSENSUS ESCALATION ANALYSIS:")
        self._detect_escalation_patterns()

    def _detect_temporal_bursts(self):
        """Detect bursts of transactions in short time windows"""
        BURST_WINDOW = 60  # 60 second window
        BURST_THRESHOLD = 10  # 10+ transactions = burst

        all_txs = self.single_witness_txs + self.insufficient_consensus_txs + self.confirmed_txs

        # Sort by timestamp (skip if timestamps are strings - can't compute time diff)
        timestamped_txs = [(tx.get("timestamp", 0), tx) for tx in all_txs if tx.get("timestamp")]

        if not timestamped_txs:
            print(f"    [*] No timestamps available for burst analysis")
            return

        # Check if timestamps are numeric
        if not isinstance(timestamped_txs[0][0], (int, float)):
            print(f"    [*] Timestamps are not numeric, skipping burst analysis")
            return

        timestamped_txs.sort(key=lambda x: x[0])

        bursts = []
        window_start = 0

        for i, (ts, tx) in enumerate(timestamped_txs):
            # Count transactions in 60s window
            window_txs = [t for t, _ in timestamped_txs[window_start:] if ts - t <= BURST_WINDOW]

            if len(window_txs) >= BURST_THRESHOLD:
                bursts.append((ts, len(window_txs)))

            # Slide window
            while window_start < len(timestamped_txs) and ts - timestamped_txs[window_start][0] > BURST_WINDOW:
                window_start += 1

        if bursts:
            print(f"    [!] Detected {len(bursts)} temporal bursts (>={BURST_THRESHOLD} txs in {BURST_WINDOW}s)")
            for ts, count in bursts[:5]:  # Show first 5
                print(f"        - Time {ts:.0f}s: {count} transactions")
        else:
            print(f"    [+] No temporal bursts detected (threshold: {BURST_THRESHOLD} txs in {BURST_WINDOW}s)")

    def _detect_escalation_patterns(self):
        """Detect patterns where same prefix/ASN gets increasing consensus over time"""
        escalations = []

        for (prefix, asn), txs in self.prefix_patterns.items():
            if len(txs) < 2:
                continue

            # Sort by timestamp
            txs_sorted = sorted(txs, key=lambda x: x.get("timestamp", 0))

            # Check for escalation (increasing approve_count over time)
            prev_count = txs_sorted[0].get("approve_count", 0)
            escalated = False

            for tx in txs_sorted[1:]:
                curr_count = tx.get("approve_count", 0)
                if curr_count > prev_count:
                    escalated = True
                prev_count = curr_count

            if escalated:
                escalations.append((prefix, asn, txs_sorted))

        if escalations:
            print(f"    [*] Found {len(escalations)} escalation patterns (increasing consensus over time)")
            for prefix, asn, txs in escalations[:5]:  # Show first 5
                counts = [tx.get("approve_count", 0) for tx in txs]
                print(f"        - {prefix} from AS{asn}: votes over time {counts}")
        else:
            print(f"    [+] No escalation patterns detected")

    def cross_node_correlation_analysis(self, blockchains: Dict[str, List[dict]]):
        """Check if SINGLE_WITNESS events are consistent across nodes"""
        print("\n" + "="*80)
        print("CROSS-NODE CORRELATION ANALYSIS")
        print("="*80)

        # For each node, extract SINGLE_WITNESS transactions
        node_single_witness = {}

        for node_name, blockchain in blockchains.items():
            single_witness = []
            for block in blockchain:
                for tx in block.get("transactions", []):
                    if tx.get("consensus_status") == "SINGLE_WITNESS" or tx.get("approve_count", 0) == 0:
                        single_witness.append((tx.get("ip_prefix"), tx.get("sender_asn"), tx.get("observer_asn")))
            node_single_witness[node_name] = set(single_witness)

        # Check consistency
        if not node_single_witness:
            print("[*] No SINGLE_WITNESS transactions to correlate")
            return

        print(f"\n[*] Checking SINGLE_WITNESS consistency across {len(blockchains)} nodes:")

        # All nodes should have identical SINGLE_WITNESS sets (deterministic blockchain)
        reference_node = list(node_single_witness.keys())[0]
        reference_set = node_single_witness[reference_node]

        all_consistent = True
        for node_name, sw_set in node_single_witness.items():
            if sw_set != reference_set:
                all_consistent = False
                diff = sw_set.symmetric_difference(reference_set)
                print(f"    [!] {node_name}: INCONSISTENT ({len(diff)} differences)")
            else:
                print(f"    [+] {node_name}: CONSISTENT")

        if all_consistent:
            print("\n[+] All nodes have identical SINGLE_WITNESS records (blockchain consensus working)")
        else:
            print("\n[!] BLOCKCHAIN FORK DETECTED: Nodes have different SINGLE_WITNESS records")
            print("    This indicates a consensus failure or network partition")

    def generate_upgrade_recommendations(self):
        """Recommend transactions for manual upgrade"""
        print("\n" + "="*80)
        print("UPGRADE RECOMMENDATIONS")
        print("="*80)

        # Criteria for upgrade:
        # 1. INSUFFICIENT_CONSENSUS with 2 votes (close to threshold)
        # 2. Marked as legitimate (not attack)
        # 3. High trust score

        candidates = []
        for tx in self.insufficient_consensus_txs:
            if tx.get("approve_count") == 2 and not tx.get("is_attack", False):
                trust_score = tx.get("observer_trust_score", 0)
                candidates.append((tx, trust_score))

        # Sort by trust score
        candidates.sort(key=lambda x: x[1], reverse=True)

        if candidates:
            print(f"\n[*] Found {len(candidates)} upgrade candidates (2 votes, legitimate, high trust)")
            print("    These transactions are ONE VOTE away from consensus")
            print("    Consider manual review and potential upgrade to CONFIRMED status\n")

            for i, (tx, trust_score) in enumerate(candidates[:10], 1):  # Top 10
                prefix = tx.get("ip_prefix")
                sender_asn = tx.get("sender_asn")
                observer_asn = tx.get("observer_asn")
                timestamp = tx.get("timestamp", 0)

                print(f"    {i}. {prefix} from AS{sender_asn} (observed by AS{observer_asn})")
                print(f"       Trust Score: {trust_score:.2f} | Time: {timestamp:.0f}s")
        else:
            print("\n[*] No upgrade candidates found")

    def generate_summary_report(self):
        """Generate executive summary"""
        print("\n" + "="*80)
        print("EXECUTIVE SUMMARY")
        print("="*80)

        total_txs = len(self.confirmed_txs) + len(self.insufficient_consensus_txs) + len(self.single_witness_txs)

        if total_txs == 0:
            print("\n[!] No transactions found in experiment")
            return

        consensus_rate = (len(self.confirmed_txs) / total_txs) * 100
        partial_rate = (len(self.insufficient_consensus_txs) / total_txs) * 100
        single_rate = (len(self.single_witness_txs) / total_txs) * 100

        print(f"\n📊 CONSENSUS BREAKDOWN:")
        print(f"    - Total Transactions:        {total_txs}")
        print(f"    - CONFIRMED (3+ votes):      {len(self.confirmed_txs):4d} ({consensus_rate:5.2f}%)")
        print(f"    - INSUFFICIENT (1-2 votes):  {len(self.insufficient_consensus_txs):4d} ({partial_rate:5.2f}%)")
        print(f"    - SINGLE_WITNESS (0 votes):  {len(self.single_witness_txs):4d} ({single_rate:5.2f}%)")

        print(f"\n🎯 CONSENSUS QUALITY:")
        if consensus_rate >= 90:
            print(f"    ✅ EXCELLENT: {consensus_rate:.1f}% consensus rate")
        elif consensus_rate >= 70:
            print(f"    ⚠️  GOOD: {consensus_rate:.1f}% consensus rate")
        elif consensus_rate >= 50:
            print(f"    ⚠️  MODERATE: {consensus_rate:.1f}% consensus rate")
        else:
            print(f"    ❌ POOR: {consensus_rate:.1f}% consensus rate")

        print(f"\n🚨 TARGETED ATTACK ANALYSIS:")
        single_attacks = sum(1 for tx in self.single_witness_txs if tx.get("is_attack", False))
        if self.single_witness_txs:
            print(f"    - SINGLE_WITNESS transactions: {len(self.single_witness_txs)}")
            print(f"    - Marked as attacks: {single_attacks}")
            print(f"    - Potential targeted attacks: {len(self.single_witness_txs) - single_attacks}")
        else:
            print(f"    ✅ No SINGLE_WITNESS transactions (no targeted attacks detected)")

        print(f"\n💡 RECOMMENDATIONS:")
        if single_rate > 10:
            print(f"    1. Investigate high SINGLE_WITNESS rate ({single_rate:.1f}%)")
            print(f"    2. Check for network partition or node isolation")
            print(f"    3. Consider increasing timeout values")

        if partial_rate > 20:
            print(f"    1. High INSUFFICIENT_CONSENSUS rate ({partial_rate:.1f}%)")
            print(f"    2. Consider lowering consensus threshold (currently 3/9)")
            print(f"    3. Review vote deduplication logic")

        if consensus_rate >= 90:
            print(f"    ✅ System performing well - no immediate action needed")

        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)

    def run_full_analysis(self):
        """Run complete analysis pipeline"""
        print("\n" + "="*80)
        print("TARGETED ATTACK & UNCONFIRMED TRANSACTION ANALYZER")
        print("="*80)
        print(f"Experiment Directory: {self.experiment_dir}")
        print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Load data
        blockchains = self.load_all_blockchains()

        if not blockchains:
            print("\n[!] ERROR: No blockchain data found")
            print("    Make sure you're pointing to a valid experiment results directory")
            return

        # Extract and categorize transactions
        self.extract_transactions_by_consensus_status(blockchains)

        # Run analyses
        self.analyze_single_witness_transactions()
        self.analyze_insufficient_consensus_transactions()
        self.analyze_chronological_misbehavior()
        self.cross_node_correlation_analysis(blockchains)
        self.generate_upgrade_recommendations()

        # Generate summary
        self.generate_summary_report()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 targeted_attack_analyzer.py <experiment_results_dir>")
        print("\nExample:")
        print("    python3 targeted_attack_analyzer.py ../experiment_results/run_2025_12_02_14_30/")
        sys.exit(1)

    experiment_dir = sys.argv[1]

    # Verify directory exists
    if not Path(experiment_dir).exists():
        print(f"[!] ERROR: Directory not found: {experiment_dir}")
        sys.exit(1)

    # Run analysis
    analyzer = TargetedAttackAnalyzer(experiment_dir)
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
