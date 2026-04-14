#!/usr/bin/env python3
"""
Blockchain Explorer - Browse, inspect, and verify BGP-Sentry blockchain data.

Interactive CLI tool for exploring blockchain blocks after an experiment run.
Supports browsing by block number, filtering by block type, inspecting
attack verdicts, searching by prefix/AS, and verifying chain integrity.

Usage:
    python3 analysis/blockchain_explorer.py <blockchain.json>

Examples:
    # Explore the primary chain
    python3 analysis/blockchain_explorer.py blockchain_data/chain/blockchain.json

    # Explore a specific experiment's chain
    python3 analysis/blockchain_explorer.py results/caida_100/20260218_120000/blockchain_stats.json

Commands (interactive):
    list [N]              Show last N blocks (default 20)
    block <number>        Show full detail of a specific block
    verdicts              List all attack verdict blocks
    verdict <id>          Show detail of a specific verdict by verdict_id
    search prefix <prefix>   Find all blocks referencing an IP prefix
    search as <asn>          Find all blocks referencing an AS number
    types                 Show block type distribution
    verify                Run full chain integrity verification
    tail [N]              Follow last N blocks (like tail)
    export <file>         Export filtered results to JSON
    help                  Show this help
    quit                  Exit

Author: BGP-Sentry Team
"""

import json
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional


class BlockchainExplorer:
    """Interactive blockchain explorer for BGP-Sentry chain data."""

    def __init__(self, blockchain_path: str):
        self.path = Path(blockchain_path)
        self.blocks = []
        self._load(blockchain_path)

    def _load(self, path: str):
        """Load blockchain data from file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(p, "r") as f:
            data = json.load(f)

        # Handle both blockchain.json and blockchain_stats.json formats
        if "blocks" in data:
            self.blocks = data["blocks"]
        elif "blockchain_info" in data:
            # blockchain_stats.json doesn't contain blocks directly
            # Try to find the actual blockchain.json from the same directory
            chain_file = p.parent / "blockchain_data" / "chain" / "blockchain.json"
            if not chain_file.exists():
                # Try parent patterns
                for candidate in [
                    p.parent.parent / "blockchain_data" / "chain" / "blockchain.json",
                    p.parent / "blockchain.json",
                ]:
                    if candidate.exists():
                        chain_file = candidate
                        break

            if chain_file.exists():
                with open(chain_file, "r") as f:
                    chain_data = json.load(f)
                self.blocks = chain_data.get("blocks", [])
            else:
                print(f"Warning: Could not locate blockchain.json from {path}")
                self.blocks = []
        else:
            self.blocks = data if isinstance(data, list) else []

        print(f"Loaded {len(self.blocks)} blocks from {path}")

    # ── Query Methods ──

    def get_block(self, block_number: int) -> Optional[Dict]:
        """Get a specific block by number."""
        for block in self.blocks:
            if block.get("block_number") == block_number:
                return block
        return None

    def get_blocks_by_type(self, block_type: str) -> List[Dict]:
        """Get all blocks of a specific type."""
        return [
            b for b in self.blocks
            if b.get("metadata", {}).get("block_type") == block_type
        ]

    def get_verdict_blocks(self) -> List[Dict]:
        """Get all attack verdict blocks."""
        return self.get_blocks_by_type("attack_verdict")

    def find_verdict_by_id(self, verdict_id: str) -> Optional[Dict]:
        """Find a verdict block by verdict_id."""
        for block in self.get_verdict_blocks():
            for tx in block.get("transactions", []):
                if tx.get("verdict_id") == verdict_id or tx.get("transaction_id") == verdict_id:
                    return {"block": block, "verdict": tx}
        return None

    def search_by_prefix(self, prefix: str) -> List[Dict]:
        """Find all blocks containing transactions referencing an IP prefix."""
        results = []
        for block in self.blocks:
            for tx in block.get("transactions", []):
                tx_prefix = (
                    tx.get("ip_prefix")
                    or tx.get("bgp_data", {}).get("ip_prefix")
                    or tx.get("attack_details", {}).get("prefix")
                    or ""
                )
                if prefix in tx_prefix:
                    results.append({
                        "block_number": block["block_number"],
                        "block_type": block.get("metadata", {}).get("block_type"),
                        "timestamp": block.get("timestamp"),
                        "transaction": tx,
                    })
        return results

    def search_by_as(self, asn: int) -> List[Dict]:
        """Find all blocks referencing a specific AS number."""
        results = []
        for block in self.blocks:
            for tx in block.get("transactions", []):
                # Check all AS fields
                related = False
                for field in ["observer_as", "sender_asn", "attacker_as", "proposer_as"]:
                    if tx.get(field) == asn:
                        related = True
                        break
                if not related:
                    bgp = tx.get("bgp_data", {})
                    if bgp.get("sender_asn") == asn:
                        related = True
                if not related:
                    details = tx.get("attack_details", {})
                    if details.get("attacker_as") == asn or details.get("leaker_as") == asn:
                        related = True

                if related:
                    results.append({
                        "block_number": block["block_number"],
                        "block_type": block.get("metadata", {}).get("block_type"),
                        "timestamp": block.get("timestamp"),
                        "transaction": tx,
                    })
        return results

    def get_type_distribution(self) -> Dict[str, int]:
        """Count blocks by type."""
        types = Counter()
        for block in self.blocks:
            bt = block.get("metadata", {}).get("block_type", "unknown")
            types[bt] += 1
        return dict(types)

    # ── Integrity Verification ──

    def verify_integrity(self) -> Dict:
        """Full chain integrity verification: hashes, linkage, Merkle roots."""
        if not self.blocks:
            return {"valid": True, "message": "Empty chain", "errors": []}

        errors = []

        for i, block in enumerate(self.blocks):
            # Verify block hash
            calculated_hash = self._calculate_block_hash(block)
            if calculated_hash != block.get("block_hash"):
                errors.append(
                    f"Block #{block.get('block_number')}: hash mismatch "
                    f"(expected {block.get('block_hash')[:16]}..., "
                    f"got {calculated_hash[:16]}...)"
                )

            # Verify previous_hash linkage (skip genesis)
            if i > 0:
                expected_prev = self.blocks[i - 1].get("block_hash")
                actual_prev = block.get("previous_hash")
                if actual_prev != expected_prev:
                    errors.append(
                        f"Block #{block.get('block_number')}: previous_hash mismatch "
                        f"(links to {actual_prev[:16]}..., "
                        f"but block #{i-1} hash is {expected_prev[:16]}...)"
                    )

            # Verify Merkle root
            calculated_merkle = self._calculate_merkle_root(
                block.get("transactions", [])
            )
            if calculated_merkle != block.get("merkle_root"):
                errors.append(
                    f"Block #{block.get('block_number')}: Merkle root mismatch"
                )

        return {
            "valid": len(errors) == 0,
            "total_blocks": len(self.blocks),
            "errors": errors,
            "message": "Chain integrity verified" if not errors
                       else f"{len(errors)} integrity error(s) found",
        }

    def _calculate_block_hash(self, block: Dict) -> str:
        block_copy = block.copy()
        block_copy.pop("block_hash", None)
        block_string = json.dumps(block_copy, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def _calculate_merkle_root(self, transactions: List[Dict]) -> str:
        if not transactions:
            return "0" * 64
        tx_hashes = []
        for tx in transactions:
            tx_string = json.dumps(tx, sort_keys=True, separators=(",", ":"))
            tx_hashes.append(hashlib.sha256(tx_string.encode("utf-8")).hexdigest())
        combined = "".join(tx_hashes)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    # ── Display Methods ──

    def format_block_summary(self, block: Dict) -> str:
        """One-line summary of a block."""
        num = block.get("block_number", "?")
        btype = block.get("metadata", {}).get("block_type", "?")
        ts = block.get("timestamp", "?")[:19]
        tx_count = len(block.get("transactions", []))
        bhash = block.get("block_hash", "?")[:12]

        # Extract key info from first transaction
        info = ""
        txs = block.get("transactions", [])
        if txs:
            tx = txs[0]
            if btype == "attack_verdict":
                verdict = tx.get("verdict", "?")
                atype = tx.get("attack_type", "?")
                info = f"  {verdict} ({atype})"
            elif btype in ("transaction", "batch"):
                prefix = (tx.get("ip_prefix") or
                          tx.get("bgp_data", {}).get("ip_prefix", ""))
                status = tx.get("consensus_status", "")
                if prefix:
                    info = f"  {prefix}"
                if status:
                    info += f" [{status}]"

        return f"  #{num:>5}  {btype:<16} {ts}  hash={bhash}..  tx={tx_count}{info}"

    def format_block_detail(self, block: Dict) -> str:
        """Full detail of a block."""
        lines = []
        lines.append(f"{'='*70}")
        lines.append(f"Block #{block.get('block_number')}")
        lines.append(f"{'='*70}")
        lines.append(f"  Timestamp:     {block.get('timestamp')}")
        lines.append(f"  Block Hash:    {block.get('block_hash')}")
        lines.append(f"  Previous Hash: {block.get('previous_hash')}")
        lines.append(f"  Merkle Root:   {block.get('merkle_root')}")

        meta = block.get("metadata", {})
        lines.append(f"  Block Type:    {meta.get('block_type', '?')}")
        lines.append(f"  TX Count:      {meta.get('transaction_count', len(block.get('transactions', [])))}")

        txs = block.get("transactions", [])
        for j, tx in enumerate(txs):
            lines.append(f"")
            lines.append(f"  Transaction [{j}]:")

            # Smart display based on record type
            record_type = tx.get("record_type", "bgp")

            if record_type == "attack_verdict":
                lines.append(f"    Type:          ATTACK VERDICT")
                lines.append(f"    Verdict ID:    {tx.get('verdict_id', tx.get('transaction_id'))}")
                lines.append(f"    Verdict:       {tx.get('verdict')}")
                lines.append(f"    Attack Type:   {tx.get('attack_type')}")
                lines.append(f"    Attacker AS:   {tx.get('attacker_as')}")
                lines.append(f"    Confidence:    {tx.get('confidence')}")
                votes = tx.get("votes", {})
                if votes:
                    lines.append(f"    Yes Votes:     {votes.get('yes_count', '?')}")
                    lines.append(f"    No Votes:      {votes.get('no_count', '?')}")
                    lines.append(f"    Total Votes:   {votes.get('total', '?')}")
                    voters = votes.get("voters", {})
                    if voters:
                        lines.append(f"    Voters:")
                        for voter_as, vote_data in voters.items():
                            v = vote_data.get("vote", "?")
                            lines.append(f"      AS{voter_as}: {v}")
            else:
                lines.append(f"    TX ID:         {tx.get('transaction_id')}")
                lines.append(f"    Observer AS:   {tx.get('observer_as')}")
                bgp = tx.get("bgp_data", {})
                if bgp:
                    lines.append(f"    Sender ASN:    {bgp.get('sender_asn')}")
                    lines.append(f"    IP Prefix:     {bgp.get('ip_prefix')}")
                    lines.append(f"    Type:          {bgp.get('announcement_type')}")
                    val = bgp.get("validation_result", {})
                    if val:
                        lines.append(f"    RPKI Valid:    {val.get('rpki_valid')}")
                else:
                    # Flat transaction format
                    if tx.get("ip_prefix"):
                        lines.append(f"    IP Prefix:     {tx.get('ip_prefix')}")
                    if tx.get("sender_asn"):
                        lines.append(f"    Sender ASN:    {tx.get('sender_asn')}")

                status = tx.get("consensus_status")
                if status:
                    lines.append(f"    Consensus:     {status}")
                    lines.append(f"    Approve Count: {tx.get('approve_count', '?')}")

        return "\n".join(lines)

    def format_verdict_detail(self, result: Dict) -> str:
        """Format a verdict search result."""
        block = result["block"]
        verdict = result["verdict"]
        lines = []
        lines.append(f"{'='*70}")
        lines.append(f"ATTACK VERDICT: {verdict.get('verdict_id', verdict.get('transaction_id'))}")
        lines.append(f"{'='*70}")
        lines.append(f"  Block #:       {block.get('block_number')}")
        lines.append(f"  Block Hash:    {block.get('block_hash')}")
        lines.append(f"  Timestamp:     {block.get('timestamp')}")
        lines.append(f"  Previous Hash: {block.get('previous_hash')}")
        lines.append(f"")
        lines.append(f"  Verdict:       {verdict.get('verdict')}")
        lines.append(f"  Attack Type:   {verdict.get('attack_type')}")
        lines.append(f"  Attacker AS:   {verdict.get('attacker_as')}")
        lines.append(f"  Confidence:    {verdict.get('confidence')}")
        lines.append(f"  Proposal ID:   {verdict.get('proposal_id')}")
        lines.append(f"")

        votes = verdict.get("votes", {})
        if votes:
            lines.append(f"  Vote Breakdown:")
            lines.append(f"    YES: {votes.get('yes_count', '?')}  "
                         f"NO: {votes.get('no_count', '?')}  "
                         f"Total: {votes.get('total', '?')}")
            voters = votes.get("voters", {})
            if voters:
                lines.append(f"")
                lines.append(f"  Per-Voter Detail:")
                for voter_as, vote_data in voters.items():
                    v = vote_data.get("vote", "?")
                    ts = vote_data.get("timestamp", "?")[:19]
                    lines.append(f"    AS{voter_as}: {v:>4}  ({ts})")

        details = verdict.get("attack_details", {})
        if details:
            lines.append(f"")
            lines.append(f"  Attack Details:")
            for k, v in details.items():
                lines.append(f"    {k}: {v}")

        # Verify this block's hash
        calc_hash = self._calculate_block_hash(block)
        hash_ok = calc_hash == block.get("block_hash")
        lines.append(f"")
        lines.append(f"  Chain Verification:")
        lines.append(f"    Block hash valid: {'YES' if hash_ok else 'NO (TAMPERED!)'}")

        # Check linkage
        bn = block.get("block_number", 0)
        if bn > 0:
            prev_block = self.get_block(bn - 1)
            if prev_block:
                link_ok = block.get("previous_hash") == prev_block.get("block_hash")
                lines.append(f"    Chain link valid: {'YES' if link_ok else 'NO (BROKEN!)'}")

        return "\n".join(lines)


def interactive_loop(explorer: BlockchainExplorer):
    """Run the interactive command loop."""
    print(f"\nBGP-Sentry Blockchain Explorer")
    print(f"  {len(explorer.blocks)} blocks loaded")
    dist = explorer.get_type_distribution()
    for btype, count in sorted(dist.items()):
        print(f"    {btype}: {count}")
    print(f"\nType 'help' for commands.\n")

    while True:
        try:
            line = input("explorer> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        try:
            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "help":
                print("""
Commands:
  list [N]                  Show last N blocks (default 20)
  block <number>            Show full detail of a block
  verdicts                  List all attack verdict blocks
  verdict <verdict_id>      Show detail of a specific verdict
  search prefix <prefix>    Find blocks referencing an IP prefix
  search as <asn>           Find blocks referencing an AS number
  types                     Show block type distribution
  verify                    Run full chain integrity verification
  tail [N]                  Show last N blocks
  export <file> [type]      Export blocks to JSON (optionally filter by type)
  quit                      Exit
""")

            elif cmd == "list" or cmd == "tail":
                n = int(parts[1]) if len(parts) > 1 else 20
                for block in explorer.blocks[-n:]:
                    print(explorer.format_block_summary(block))

            elif cmd == "block":
                if len(parts) < 2:
                    print("Usage: block <number>")
                    continue
                bn = int(parts[1])
                block = explorer.get_block(bn)
                if block:
                    print(explorer.format_block_detail(block))
                else:
                    print(f"Block #{bn} not found")

            elif cmd == "verdicts":
                verdict_blocks = explorer.get_verdict_blocks()
                if not verdict_blocks:
                    print("No attack verdict blocks found on this chain.")
                else:
                    print(f"\n{len(verdict_blocks)} attack verdict block(s):\n")
                    for block in verdict_blocks:
                        print(explorer.format_block_summary(block))

            elif cmd == "verdict":
                if len(parts) < 2:
                    print("Usage: verdict <verdict_id>")
                    continue
                vid = parts[1]
                result = explorer.find_verdict_by_id(vid)
                if result:
                    print(explorer.format_verdict_detail(result))
                else:
                    print(f"Verdict '{vid}' not found. Try 'verdicts' to list all.")

            elif cmd == "search":
                if len(parts) < 3:
                    print("Usage: search prefix <prefix>  OR  search as <asn>")
                    continue
                subcmd = parts[1].lower()
                query = parts[2]

                if subcmd == "prefix":
                    results = explorer.search_by_prefix(query)
                    if results:
                        print(f"\n{len(results)} match(es) for prefix '{query}':\n")
                        for r in results[:50]:
                            tx = r["transaction"]
                            print(f"  Block #{r['block_number']:>5}  "
                                  f"{r['block_type']:<16}  "
                                  f"{r['timestamp'][:19]}  "
                                  f"tx={tx.get('transaction_id', tx.get('verdict_id', '?'))[:30]}")
                    else:
                        print(f"No blocks found for prefix '{query}'")

                elif subcmd == "as":
                    asn = int(query)
                    results = explorer.search_by_as(asn)
                    if results:
                        print(f"\n{len(results)} match(es) for AS{asn}:\n")
                        for r in results[:50]:
                            tx = r["transaction"]
                            print(f"  Block #{r['block_number']:>5}  "
                                  f"{r['block_type']:<16}  "
                                  f"{r['timestamp'][:19]}  "
                                  f"tx={tx.get('transaction_id', tx.get('verdict_id', '?'))[:30]}")
                    else:
                        print(f"No blocks found for AS{asn}")
                else:
                    print("Usage: search prefix <prefix>  OR  search as <asn>")

            elif cmd == "types":
                dist = explorer.get_type_distribution()
                total = sum(dist.values())
                print(f"\nBlock type distribution ({total} total):\n")
                for btype, count in sorted(dist.items(), key=lambda x: -x[1]):
                    pct = 100 * count / max(total, 1)
                    bar = "#" * int(pct / 2)
                    print(f"  {btype:<20} {count:>6}  ({pct:5.1f}%)  {bar}")

            elif cmd == "verify":
                print("Verifying chain integrity...")
                result = explorer.verify_integrity()
                print(f"\n  Result:       {'VALID' if result['valid'] else 'INVALID'}")
                print(f"  Total Blocks: {result['total_blocks']}")
                if result["errors"]:
                    print(f"  Errors ({len(result['errors'])}):")
                    for err in result["errors"][:10]:
                        print(f"    - {err}")
                else:
                    print(f"  All block hashes, chain linkage, and Merkle roots verified.")

            elif cmd == "export":
                if len(parts) < 2:
                    print("Usage: export <file> [block_type]")
                    continue
                outfile = parts[1]
                btype_filter = parts[2] if len(parts) > 2 else None

                blocks = explorer.blocks
                if btype_filter:
                    blocks = explorer.get_blocks_by_type(btype_filter)

                with open(outfile, "w") as f:
                    json.dump(blocks, f, indent=2, default=str)
                print(f"Exported {len(blocks)} blocks to {outfile}")

            else:
                print(f"Unknown command: {cmd}. Type 'help' for commands.")

        except Exception as e:
            print(f"Error: {e}")


def main():
    if len(sys.argv) < 2:
        print("BGP-Sentry Blockchain Explorer")
        print()
        print("Usage:")
        print("  python3 analysis/blockchain_explorer.py <blockchain.json>")
        print()
        print("Examples:")
        print("  python3 analysis/blockchain_explorer.py blockchain_data/chain/blockchain.json")
        print()
        print("Non-interactive (single command):")
        print("  python3 analysis/blockchain_explorer.py blockchain.json --verify")
        print("  python3 analysis/blockchain_explorer.py blockchain.json --verdicts")
        print("  python3 analysis/blockchain_explorer.py blockchain.json --search-prefix 8.8.8.0/24")
        print("  python3 analysis/blockchain_explorer.py blockchain.json --search-as 15169")
        return 1

    blockchain_path = sys.argv[1]

    try:
        explorer = BlockchainExplorer(blockchain_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    # Non-interactive mode
    if len(sys.argv) > 2:
        flag = sys.argv[2]

        if flag == "--verify":
            result = explorer.verify_integrity()
            print(json.dumps(result, indent=2))
            return 0 if result["valid"] else 1

        elif flag == "--verdicts":
            verdicts = explorer.get_verdict_blocks()
            for v in verdicts:
                print(explorer.format_block_summary(v))
            return 0

        elif flag == "--search-prefix" and len(sys.argv) > 3:
            results = explorer.search_by_prefix(sys.argv[3])
            print(json.dumps(results, indent=2, default=str))
            return 0

        elif flag == "--search-as" and len(sys.argv) > 3:
            results = explorer.search_by_as(int(sys.argv[3]))
            print(json.dumps(results, indent=2, default=str))
            return 0

        elif flag == "--types":
            dist = explorer.get_type_distribution()
            print(json.dumps(dist, indent=2))
            return 0

        else:
            print(f"Unknown flag: {flag}")
            return 1

    # Interactive mode
    interactive_loop(explorer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
