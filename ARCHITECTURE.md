# BGP-Sentry: Permissioned Block-Lattice Architecture

## Branch: `permissioned-block-lattice`

This branch contains the **Permissioned Block-Lattice with Merge-Based Fork Resolution** implementation of BGP-Sentry. This is the complete, tested version of the system with full experiment results.

---

## Blockchain Architecture Type

**Permissioned Block-Lattice** — each RPKI validator maintains its own independent blockchain. Cross-chain coordination is achieved through P2P voting, not global block consensus.

### Classification

| Property | Value |
|---|---|
| Architecture | Per-node independent chains (Block-Lattice) |
| Permission Model | Permissioned (RPKI validators only) |
| Consensus Mechanism | Peer voting (approve/reject per transaction) |
| Fork Resolution | Merge-based (no data loss) |
| Cryptography | SHA-256 (block hashing) + Ed25519 (digital signatures) |
| Block Structure | block_number, previous_hash, transactions, block_hash, merkle_root |
| Finality | Seconds (vote collection window) |
| TPS Scaling | Linear with node count (each node = independent chain) |

### Comparison with Other Blockchain Types

| Aspect | Bitcoin/Ethereum | Nano (Block-Lattice) | **BGP-Sentry (This Branch)** |
|---|---|---|---|
| Chain count | 1 shared | 1 per account | 1 per RPKI validator |
| Consensus | PoW / PoS | ORV (on conflicts only) | Peer voting (on every TX) |
| Fork resolution | Longest chain wins (data lost) | Voting picks one (data lost) | **Merge block (no data lost)** |
| Permission | Permissionless | Permissionless | **Permissioned** |
| Purpose | Currency | Currency | **BGP security monitoring** |
| Scalability | Fixed TPS | Fixed TPS | **Linear TPS scaling** |

### What Makes This Design Novel

1. **Merge-based fork resolution**: Unlike Bitcoin (longest chain wins) or Nano (voting picks one), forks are resolved by creating merge blocks that incorporate novel transactions from both branches. No BGP observation is ever lost.
2. **Universal consensus voting**: Every transaction is voted on by peers (not just conflicts). This provides corroboration levels (CONFIRMED / INSUFFICIENT_CONSENSUS / SINGLE_WITNESS).
3. **Permissioned validator set**: Only RPKI-participating ASes can write to the blockchain, derived from real-world RPKI deployment.
4. **Domain-specific consensus**: Peers vote based on "did I also observe this BGP event?" — not computational work or stake.

---

## System Architecture

### Data Flow

```
BGP Announcement (CAIDA dataset)
    │
    ▼
RPKI Validator Node (AS174, AS701, etc.)
    │
    ├── 1. RPKI Validation (VRP/ROA check)
    ├── 2. Attack Detection (6 detectors)
    │       ├── BOGON_INJECTION
    │       ├── PREFIX_HIJACK
    │       ├── SUBPREFIX_HIJACK
    │       ├── FORGED_ORIGIN_PREFIX_HIJACK
    │       ├── ROUTE_FLAPPING
    │       └── ACCIDENTAL_ROUTE_LEAK
    ├── 3. Create Transaction
    ├── 4. Broadcast to Peers (P2P)
    │       └── Adaptive: peers_asked = max(threshold×2, √N)
    ├── 5. Peers Vote (APPROVE / REJECT)
    ├── 6. Determine Consensus Level
    │       ├── CONFIRMED (3+ approvals)
    │       ├── INSUFFICIENT_CONSENSUS (1-2 approvals)
    │       └── SINGLE_WITNESS (0 approvals)
    └── 7. Write to Node's Own Blockchain
            └── Fork detection + merge if needed
```

### Per-Node Blockchain Structure

```
AS174's Blockchain:
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Genesis  │───▶│ Block 1  │───▶│ Block 2  │───▶│ Block 3  │───▶ ...
│ prev: 0  │    │ prev: h0 │    │ prev: h1 │    │ prev: h2 │
│ hash: h0 │    │ hash: h1 │    │ hash: h2 │    │ hash: h3 │
│ txs: []  │    │ txs: [t1]│    │ txs: [t2]│    │ merge    │
│          │    │ votes: 3 │    │ votes: 5 │    │ txs:[t3] │
└──────────┘    └──────────┘    └──────────┘    └──────────┘

AS701's Blockchain (independent):
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Genesis  │───▶│ Block 1  │───▶│ Block 2  │───▶ ...
│ prev: 0  │    │ prev: h0 │    │ prev: h1 │
│ hash: h0 │    │ hash: h1 │    │ hash: h2 │
└──────────┘    └──────────┘    └──────────┘
```

### Key Implementation Files

| File | Purpose |
|---|---|
| `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/blockchain_interface.py` | Core blockchain: block creation, hashing (SHA-256), Merkle roots, chain validation, fork detection/resolution |
| `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/signature_utils.py` | Ed25519 key generation, signing, verification |
| `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/attack_detector.py` | 6 attack type detectors |
| `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/p2p_transaction_pool.py` | P2P broadcast, vote collection, consensus determination |
| `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/attack_consensus.py` | Attack-specific voting and verdict generation |
| `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/prefix_ownership_state.py` | Blockchain-derived prefix ownership (dynamic ROA) |
| `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/config.py` | All tunable parameters |
| `nodes/rpki_nodes/shared_blockchain_stack/virtual_node.py` | RPKI validator node: observation pipeline |
| `main_experiment.py` | Experiment orchestrator |

### Consensus Levels

All three levels are written to the blockchain. Nothing is discarded.

- **CONFIRMED** (3+ approve votes): Full consensus — highest trust weight
- **INSUFFICIENT_CONSENSUS** (1-2 approve votes): Partial corroboration — medium trust weight
- **SINGLE_WITNESS** (0 approve votes): Only the proposer observed it — lowest trust weight

Over time, multiple SINGLE_WITNESS entries from different proposers for the same (prefix, origin) accumulate credibility through longitudinal analysis.

### Peer Selection for Voting

Adaptive broadcast: `peers_asked = max(threshold × 2, √N)` — scales sublinearly with network size.

Priority order:
1. Relevant neighbors first (topology-aware from CAIDA AS relationships)
2. Random peers to fill remaining slots

---

## Experiment Results Summary (April 13, 2026)

### Scalability Performance

| Metric | caida_50 (48 nodes) | caida_100 (104 nodes) | caida_200 (210 nodes) | caida_350 (347 nodes) | caida_650 (645 nodes) |
|---|---:|---:|---:|---:|---:|
| RPKI Validators | 26 | 67 | 132 | 207 | 375 |
| Total Observations | 22,329 | 81,877 | 282,009 | 514,585 | 1,253,482 |
| Runtime | 11.6 min | 12.4 min | 16.4 min | 21.2 min | 73.9 min |

### Blockchain Integrity

| Metric | caida_50 | caida_100 | caida_200 | caida_350 | caida_650 |
|---|---:|---:|---:|---:|---:|
| Valid Chains | 26/26 | 67/67 | 132/132 | 207/207 | 375/375 |
| Chain Validity | **100%** | **100%** | **100%** | **100%** | **100%** |
| Mean Blocks/Node | 573 | 488 | 804 | 857 | 486 |
| Mean TX/Node | 954 | 1,325 | 1,246 | 1,306 | 6,323 |

### Fork Resolution

| Metric | caida_50 | caida_100 | caida_200 | caida_350 | caida_650 |
|---|---:|---:|---:|---:|---:|
| Forks Detected | 12,357 | 23,558 | 49,806 | 102,707 | 18,134 |
| Forks Resolved | 12,357 | 23,558 | 49,806 | 102,707 | 18,134 |
| **Resolution Rate** | **100%** | **100%** | **100%** | **100%** | **100%** |

### P2P Message Delivery

| Metric | caida_50 | caida_100 | caida_200 | caida_350 | caida_650 |
|---|---:|---:|---:|---:|---:|
| Messages Sent | 58,450 | 355,920 | 2,219,855 | 4,576,846 | 40,119,331 |
| Messages Delivered | 58,450 | 355,920 | 2,219,855 | 4,576,846 | 40,119,331 |
| Messages Dropped | 0 | 0 | 0 | 0 | 0 |
| **Delivery Rate** | **100%** | **100%** | **100%** | **100%** | **100%** |

### Throughput (TPS)

| Metric | caida_50 | caida_100 | caida_200 | caida_350 | caida_650 |
|---|---:|---:|---:|---:|---:|
| Per-Node TPS | 1.37 | 1.79 | 1.63 | 1.71 | 7.88 |
| Network-Wide TPS | 35.7 | 119.7 | 215.0 | 353.0 | 2,956.5 |
| Per-Node Blocks/s | 0.82 | 0.66 | 1.05 | 1.12 | 0.61 |

Network-wide TPS scales linearly with node count because each node writes to its own independent chain.

### Dataset Time vs Simulation Runtime

| Scale | Dataset Span | Simulation Runtime | Ratio |
|---|---:|---:|---:|
| caida_50 | 11.6 min | 11.6 min | 1.00x (real-time) |
| caida_100 | 12.4 min | 12.4 min | 0.99x (real-time) |
| caida_200 | 12.8 min | 16.4 min | 0.78x |
| caida_350 | 12.8 min | 21.2 min | 0.60x |
| caida_650 | 13.4 min | 73.9 min | 0.18x |

### Attack Detection Performance (Per Attack Type, caida_650)

| Attack Type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| BOGON_INJECTION | 2,407 | 0 | 797 | 1.000 | 0.751 | 0.858 |
| PREFIX_HIJACK | 2,118 | 17,274 | 50 | 0.109 | 0.977 | 0.196 |
| SUBPREFIX_HIJACK | 1,878 | 0 | 2,603 | 1.000 | 0.419 | 0.591 |
| FORGED_ORIGIN_PREFIX_HIJACK | 586 | 0 | 695 | 1.000 | 0.457 | 0.628 |
| ROUTE_FLAPPING | 2,944 | 0 | 76 | 1.000 | 0.975 | 0.987 |
| ACCIDENTAL_ROUTE_LEAK | 2 | 0 | 2 | 1.000 | 0.500 | 0.667 |
| **OVERALL** | **9,935** | **17,274** | **4,223** | **0.365** | **0.702** | **0.480** |

**Note**: All false positives originate from PREFIX_HIJACK due to missing MOAS (Multi-Origin AS) handling in the PrefixOwnershipState detector. Excluding PREFIX_HIJACK, the system achieves **100% precision** across all other attack types at all scales.

### Attack Detection Across Scales (Excluding PREFIX_HIJACK)

| Scale | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| caida_50 | 252 | 0 | 54 | **1.000** | 0.824 | 0.903 |
| caida_100 | 438 | 0 | 267 | **1.000** | 0.621 | 0.766 |
| caida_200 | 948 | 0 | 271 | **1.000** | 0.778 | 0.875 |
| caida_350 | 2,894 | 0 | 1,036 | **1.000** | 0.736 | 0.848 |
| caida_650 | 7,817 | 0 | 4,173 | **1.000** | 0.652 | 0.789 |

---

## Configuration Parameters

Key parameters from `.env` / `config.py`:

| Parameter | Value | Purpose |
|---|---|---|
| CONSENSUS_THRESHOLD | 3 | Minimum approve votes for CONFIRMED |
| RPKI_DEDUP_WINDOW | 30s | Skip repeated (prefix, origin) within window |
| FLAP_WINDOW_SECONDS | 60 | Route flapping detection window |
| FLAP_THRESHOLD | 5 | Min announcements to flag flapping |
| FLAP_DEDUP_SECONDS | 30 | Dedup window for flap counting |
| WARM_UP_SECONDS | 120 | Initial observation period before consensus |

---

## How to Run Experiments

```bash
# Single scale
python main_experiment.py --dataset caida_50

# All scales (sequential)
for scale in caida_50 caida_100 caida_200 caida_350 caida_650; do
    python main_experiment.py --dataset $scale
done
```

Results are saved to `results/<dataset_name>/<timestamp>/`.
