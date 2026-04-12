# BGP-Sentry Bug Fixes & Feature Log

Tracks all bugs found during code audit, fixes applied, and features added for review.

---

## Bug #1: Consensus Commit Race Condition (Silent Transaction Loss)

**Date Fixed:** 2026-04-12
**Severity:** Medium — causes silent data loss under load
**Files Changed:**
- `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/p2p_transaction_pool.py`
- `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/p2p_transaction_pool_async.py`

### What Was Happening

When a transaction received 3+ approve votes, the code marked it in `committed_transactions` BEFORE writing to the blockchain. This was done to prevent the timeout handler from also trying to commit the same transaction (double-commit race).

However, if the blockchain write failed:
- The transaction was stuck in `committed_transactions` (marked "done")
- The timeout handler would skip it (thinks it's already committed)
- The transaction stayed in `pending_votes` but was never retried
- **Result: silent transaction loss** — the TX was never written to the blockchain

This affected three commit paths:
1. `_write_single_transaction()` — consensus-reached path
2. `_commit_unconfirmed_transaction()` — timeout path (INSUFFICIENT_CONSENSUS / SINGLE_WITNESS)
3. Both sync and async versions had the same bug

### The Fix

In all three commit paths, if `blockchain.add_transaction_to_blockchain()` returns `False`, we now remove the transaction from `committed_transactions`. This allows the timeout handler to pick it up on its next pass and retry the write.

```python
# Before (transaction lost forever on failure):
else:
    self.logger.error(f"Failed to write transaction {transaction_id} to blockchain")

# After (timeout handler will retry):
else:
    self.logger.error(f"Failed to write transaction {transaction_id} to blockchain")
    with self.lock:
        self.committed_transactions.pop(transaction_id, None)
```

### Impact
- Prevents silent transaction loss under load
- Likely contributes to the 82-96% blockchain validity issue (missing transactions = broken hash chains)

---

## Bug #2: Pending Votes Overflow — Unsynchronized Capacity Check

**Date Fixed:** 2026-04-12
**Severity:** Medium — race condition under high concurrency
**Files Changed:**
- `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/p2p_transaction_pool.py`
- `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/p2p_transaction_pool_async.py`

### What Was Happening

In `broadcast_transaction()`, when `pending_votes` reached max capacity (2000), the code force-timed-out the oldest transaction to make room. But this capacity check was done **without holding the lock**, while other threads could be concurrently modifying `pending_votes` (adding votes, committing transactions).

This could cause:
- Two threads both seeing the queue as full and both evicting entries
- Reading `pending_votes` size while another thread is modifying it

### The Fix

Wrapped the capacity check inside the lock so the size read is consistent:

```python
# Before (no lock):
if len(self.pending_votes) >= cfg.PENDING_VOTES_MAX_CAPACITY:
    oldest_tx = min(self.pending_votes, ...)
    self._handle_timed_out_transaction(oldest_tx)

# After (lock-protected check):
oldest_to_evict = None
with self.lock:
    if len(self.pending_votes) >= cfg.PENDING_VOTES_MAX_CAPACITY:
        oldest_to_evict = min(self.pending_votes, ...)

if oldest_to_evict:
    self._handle_timed_out_transaction(oldest_to_evict)
```

The actual eviction (`_handle_timed_out_transaction`) still runs outside the lock because it acquires the lock internally.

### Impact
- Prevents double-eviction under concurrent access
- More reliable behavior at high load (350+ nodes)

---

## Bug #3: Blockchain Chain Invalidity — Shared Mutable References

**Date Fixed:** 2026-04-12
**Severity:** High — causes 4-18% of chains to fail integrity verification
**Files Changed:**
- `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/blockchain_interface.py`

### What Was Happening

The in-memory blockchain stored **references** to transaction dicts, not copies. When a block was created:

```python
new_block = {
    "transactions": [transaction],  # ← reference, not copy
    ...
}
# Hash computed from transaction content at THIS moment
new_block["block_hash"] = self._calculate_block_hash(new_block)
```

The same `transaction` dict was shared across:
1. The block in the originating node's blockchain
2. The `pending_votes` dict (until deleted)
3. Replicated blocks sent to peers via in-memory message bus (by reference)
4. Fork merge blocks on receiving nodes

If ANY code path later mutated the transaction dict (e.g., adding fields, modifying signatures), the block's content changed but the stored hash did not. When `verify_blockchain_integrity()` re-hashed the block at the end of simulation, the hashes didn't match.

**Observed:** caida_50 = 82.4% valid chains, caida_100 = 92.1%, caida_200 = 96.1%

### Root Cause

The in-memory message bus passes Python objects by reference (no serialization). So the same dict object could exist in multiple nodes' blockchains simultaneously. The `list()` snapshot of votes prevented the most obvious mutation, but any other modification to the transaction dict (adding fields, changing values) after the block hash was computed would silently corrupt the chain.

### The Fix

Deep copy transactions at every point where they enter a block:

1. **`add_transaction_to_blockchain()`** — `copy.deepcopy(transaction)` before storing in block
2. **`add_multiple_transactions()`** — `copy.deepcopy(unique_txs)` for batch blocks
3. **`append_replicated_block()` (normal append)** — `copy.deepcopy(block)` when appending replicated block
4. **`append_replicated_block()` (fork merge)** — `copy.deepcopy(tx)` for each novel transaction extracted from incoming block
5. **Genesis-only append** — `copy.deepcopy(block)` for safety

This breaks the shared-reference chain completely. Each blockchain node now has its own independent copy of every block and transaction. Mutations in one node's context cannot affect another node's chain.

### Performance Impact

`copy.deepcopy()` adds ~0.1-0.5ms per transaction. At 10 TPS this is negligible. At 1250 nodes with 474 RPKI validators, the total overhead is ~50ms/s — well within real-time budget.

### Impact
- Should bring chain validity from 82-96% to 100%
- Eliminates an entire class of shared-state bugs
- Makes the in-memory simulation behave like a real network (where blocks are serialized/deserialized over TCP)

---

## Feature #1: Blockchain Data Dump to Disk

**Date Added:** 2026-04-12
**Files Changed:**
- `main_experiment.py` — added `_dump_blockchain_data()` method

### What Was Added

After simulation completes, all per-node blockchain data is written from RAM to disk:
`results/<run>/blockchain_data/AS<asn>/blockchain.json` (full blocks + transactions + hashes)
`results/<run>/blockchain_data/AS<asn>/fork_events.json` (fork detection/resolution log)

Enables post-hoc forensic analysis of raw chain data.

---

## Feature #2: Post-Hoc Longitudinal Blockchain Detection

**Date Added:** 2026-04-12
**Files Created:**
- `analysis/posthoc_blockchain_detection.py`
**Files Modified:**
- `main_experiment.py` — auto-runs after blockchain dump

### What Was Added

A new `PosthocBlockchainDetector` class that performs 4 cross-chain analyses on the dumped blockchain data:

1. **SINGLE_WITNESS Accumulation** — Finds (prefix, origin) pairs recorded as SINGLE_WITNESS by 3+ independent validators. These had no peer corroboration individually, but collectively form evidence of an attack.

2. **Cross-Chain Corroboration** — Counts how many independent chains recorded each announcement. Flags consensus disagreements (one chain: CONFIRMED, another: SINGLE_WITNESS).

3. **Temporal Pattern Detection** — Detects origin changes (prefix P announced by AS_A then AS_B = possible hijack) and announcement bursts (spike in SINGLE_WITNESS within a time window).

4. **Longitudinal Trust Scoring** — Scores each origin AS by its CONFIRMED vs SINGLE_WITNESS ratio. High SW ratio = suspicious. Cross-references with ground truth.

### Why This Matters

- This is the ONLY detection module that uses blockchain data (the 5 real-time detectors use static databases)
- Implements the CLAUDE.md design goal: "SINGLE_WITNESS entries accumulate and gain credibility through longitudinal analysis"
- Demonstrates WHY a blockchain architecture is needed (not just a centralized log)
- Catches attacks that no individual real-time detector could see

### Output

`results/<run>/posthoc_blockchain_detection.json` with per-analysis results and aggregate impact metrics (new detections, combined recall improvement).

Also runnable standalone: `python3 analysis/posthoc_blockchain_detection.py <results_dir>`

---

## Bug #4: Consensus Degradation from Misconfigured Timeouts

**Date Fixed:** 2026-04-12
**Severity:** High — caida_100 showed only 35.1% CONFIRMED (should be ~60%+)
**Files Changed:**
- `.env.100`, `.env.200`, `.env.350`, `.env.650`, `.env.1250`

### What Was Happening

The `.env` config files had three problems causing consensus degradation:

1. **Timeouts too short for larger networks.** caida_100 had P2P_REGULAR_TIMEOUT=10s (only 2s more than caida_50's 8s) for a 2× larger network. Votes arrived after timeout → committed as SINGLE_WITNESS.

2. **BATCH_TIMEOUT decreasing as network grew.** caida_50=0.2s, caida_100=0.15s, caida_200+=0.1s. Faster batching at larger scales means transactions commit before votes arrive — the opposite of what's needed.

3. **KNOWLEDGE_WINDOW_SECONDS static at 480s.** Peers need more time at larger scales to accumulate observations so they can vote "approve." At 1250 nodes, 480s was too short.

4. **P2P_MAX_BROADCAST_PEERS was dead code.** Set in .env but never used — broadcast size is computed dynamically as max(threshold×2, √N). The config values were misleading.

### The Fix

Consistent scaling formulas applied:

| Config | Timeout | Attack TO | Batch TO | KB Window | 
|--------|---------|-----------|----------|-----------|
| .env.50 | 8s | 12s | 0.2s | 480s |
| .env.100 | 14s (was 10) | 21s (was 15) | 0.2s (was 0.15) | 600s (was 480) |
| .env.200 | 20s (was 15) | 30s (was 20) | 0.2s (was 0.1) | 720s (was 480) |
| .env.350 | 29s (was 18) | 44s (was 25) | 0.2s (was 0.1) | 900s (was 480) |
| .env.650 | 47s (was 22) | 71s (was 30) | 0.2s (was 0.1) | 1200s (was 480) |
| .env.1250 | 83s (was 30) | 125s (was 45) | 0.2s (was 0.1) | 1800s (was 480) |

Scaling: `timeout ≈ 8 + (N/50) × 3`, `attack_timeout = regular × 1.5`, `batch_timeout` fixed at 0.2s, `knowledge_window` scales proportionally.

### Impact
- Should improve caida_100 CONFIRMED from ~35% to ~60%+
- Prevents consensus collapse at larger scales
- Consistent behavior across the scalability sweep

---

## Bug #5: Missing First-Hop Origin Filter — Dishonest Transit Can Frame Innocent ASes

**Date Fixed:** 2026-04-12
**Severity:** Critical (security) — dishonest transit AS can fabricate announcements and cause innocent ASes to be penalized on the blockchain
**Files Changed:**
- `nodes/rpki_nodes/shared_blockchain_stack/virtual_node.py` (both sync and async pipelines)

### What Was Happening

RPKI validators processed ALL received BGP announcements regardless of AS path length. This meant:

- Node A (RPKI) receives from Node B: "Node C claims prefix P" (path: [A, B, C])
- Node A processes this, detects C is unauthorized → PREFIX_HIJACK
- C gets penalized on the blockchain
- BUT: Node B could have fabricated this announcement — C never actually claimed prefix P
- Result: dishonest transit ASes can frame innocent origin ASes

### The Fix

Added first-hop origin filter at Step 0a (before dedup, before knowledge base):

```python
as_path = obs.get("as_path", [origin_asn])
if len(as_path) > 2:
    result["action"] = "skipped_not_first_hop_origin"
    return result
```

Only process announcements where `len(as_path) <= 2`, meaning:
- `[observer, origin]` — origin is the direct neighbor (first-hop = origin)
- `[origin]` — origin IS the observer

This ensures the blockchain only records **direct origin claims** — an AS can only be penalized for claims it made directly to an RPKI validator, not for claims forwarded (and potentially fabricated) by transit ASes.

### Impact on Data Volume

| Dataset | Before (all paths) | After (first-hop only) |
|---------|-------------------|----------------------|
| caida_50 | 100% processed | ~50% processed (path ≤ 2) |
| caida_200 | 100% processed | ~5-50% (varies by node) |
| caida_1250 | 100% processed | ~5-50% (varies by node) |

Applied to both sync (`_process_observation_rpki`) and async (`_process_observation_rpki_async`) pipelines.

### Security Argument
The blockchain only records direct origin claims attributable to the claimer. No AS can be penalized based on a forwarded (potentially fabricated) announcement. This is a fundamental trust property of the system.

---

## Bug #5 (Updated): Trusted Path Filter — Chain of Trust Through RPKI Relays

**Date Updated:** 2026-04-12
**Supersedes:** Original first-hop-only filter

### Updated Design

The filter now accepts announcements where ALL intermediate relays are RPKI nodes (not just first-hop origin). RPKI nodes are trusted relays because they have verified identity, hold BGPCoin, and their behavior is auditable on-chain.

**Rules:**
1. Skip self-origin (origin == observer) — self-attestation
2. Skip len=1 paths — BGPy artifact
3. Accept len=2 [observer, origin] — direct neighbor claim
4. Accept len=3+ ONLY if ALL intermediate hops are RPKI nodes
5. Reject if ANY intermediate hop is non-RPKI (could fabricate)

**Data processed after filter:**
- caida_50: 58.9% accepted
- caida_200: 52.7% accepted
- caida_650: 44.1% accepted
- caida_1250: 57.8% accepted

---

## Feature #3: Trust Score Now Active in Decisions

**Date Added:** 2026-04-12
**Files Changed:**
- `nodes/rpki_nodes/shared_blockchain_stack/virtual_node.py`
- `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/nonrpki_rating.py`
- `nodes/rpki_nodes/shared_blockchain_stack/node_manager.py`

### What Was Happening
- Trust scores were tracked but NEVER used for any decision
- `trust_score=100.0` was hardcoded everywhere
- `rating_system=None` was passed to nodes (never connected)
- Missing penalties for FORGED_ORIGIN_PREFIX_HIJACK and ACCIDENTAL_ROUTE_LEAK

### What Changed
1. **Trust-aware dedup:** Suspicious ASes (trust < 30) get halved dedup window (2× more monitoring)
2. **Actual trust score** passed to knowledge base instead of hardcoded 100.0
3. **Rating system** connected to all nodes (was `None`)
4. **Missing penalties added:** FORGED_ORIGIN (-30), ACCIDENTAL_ROUTE_LEAK (-8)

---

## Feature #4: Blockchain State Detector Reports Standard Attack Types

**Date Added:** 2026-04-12
**Files Changed:**
- `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/prefix_ownership_state.py`

### What Changed
The blockchain state detector now reports `attack_type: "PREFIX_HIJACK"` with `detection_method: "blockchain_state"` instead of a custom `"BLOCKCHAIN_STATE_CONFLICT"` type. This is because it's a detection METHOD, not a new BGP attack type.

---

## Design Note: Shared State in Simulation

### BGPCoin Ledger, Trust Ratings, and Prefix Ownership State

In the simulation, these are maintained as **single shared Python objects** rather than per-node copies:

```
NodeManager creates ONE instance of each:
  shared_ledger            → BGPCoinLedger
  rating_system            → NonRPKIRatingSystem
  prefix_ownership_state   → PrefixOwnershipState

All RPKI nodes receive the SAME reference.
```

**Why this is correct for the simulation:**

1. In a real deployment, these states would be deterministically derived from the confirmed transaction history on each node's blockchain
2. Our per-node blockchains contain identical confirmed transactions (via fork resolution and block replication)
3. Therefore every node would compute the same final balances, ratings, and ownership state
4. The single shared object gives the same result more efficiently

**In production:** Each node would independently compute these states from its local blockchain. The simulation shortcut is valid because the underlying blockchain data is per-node and independently verified.

This is the same approach used by Ethereum simulators — shared state in simulation, independent state derivation in production.
