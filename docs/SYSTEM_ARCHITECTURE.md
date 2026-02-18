# BGP-Sentry System Architecture

## Overview

BGP-Sentry is a fully functional distributed blockchain simulation where each autonomous system (AS) operates as an independent blockchain participant with real consensus voting, token economics, and longitudinal trust scoring.

Every BGP announcement is processed through the full blockchain pipeline: validation, transaction creation, peer-to-peer broadcast, BFT consensus, block commitment, attack detection, and reward distribution.

The system is fully data-driven and works with any CAIDA dataset (100 to 1000+ nodes) without code changes.

## Data Flow

```
1. Dataset Selection (caida_100, caida_200, caida_500, caida_1000)
       |
2. RPKINodeRegistry.initialize(dataset_path)
   - Reads as_classification.json
   - Populates RPKI_NODES, NON_RPKI_NODES, VALIDATORS, OBSERVERS
   - Sets dynamic consensus threshold: max(MIN, min(N/3+1, CAP))
       |
3. DatasetLoader(dataset_path)
   - Loads all AS observation files
   - Loads ground truth for evaluation
   - Extracts legitimate prefixes for VRP generation
       |
4. VRP Generation (scripts/generate_vrp.py)
   - Extracts legitimate (prefix, origin_asn) pairs
   - Produces StayRTR-format JSON for RPKI validation
       |
5. NodeManager(data_loader)
   - Creates shared blockchain infrastructure (single instance)
   - Creates VirtualNode for each AS
   - RPKI ASes -> blockchain_validator role
   - Non-RPKI ASes -> observer role
   - Wires shared infrastructure into every node
       |
6. Orchestrator starts all nodes (in-process threads)
   - Each node processes its observations sequentially
   - RPKI validators: full blockchain pipeline (see below)
   - Non-RPKI observers: attack detection + rating (see below)
       |
7. Results Collection (13 structured output files per run)
```

## RPKI Validator Pipeline

Each RPKI node processes a BGP announcement through these steps:

1. Validate BGP announcement via StayRTR (ROA check)
2. Add observation to per-node knowledge base
3. Early-skip deduplication (Step 0: if same prefix+origin seen within 5 min, skip — attacks always bypass)
4. Create blockchain transaction and broadcast to peers via InMemoryMessageBus
5. Peers vote approve/reject based on their own knowledge base
6. On BFT consensus (threshold signatures reached): write block to blockchain
7. On timeout: commit with "insufficient consensus" or "single witness" status
8. Run attack detection (4 types) on committed transaction
9. If attack detected: propose attack vote, majority decides
10. Award BGPCOIN to committer and voters

## Non-RPKI Observer Pipeline

Each non-RPKI node processes a BGP announcement through these steps:

1. Run attack detection (4 types) on each observation
2. If attack detected: record to blockchain immediately, apply trust rating penalty
3. If legitimate: throttle duplicates (2-minute dedup window), record to blockchain
4. Trust rating tracked longitudinally (start at 50/100)

## Key Classes

### RPKINodeRegistry (blockchain_utils/rpki_node_registry.py)

Singleton-style class that holds the authoritative RPKI classification.

- `initialize(dataset_path)` - Load from as_classification.json
- `is_rpki_node(asn)` - Check if AS is RPKI
- `get_consensus_threshold()` - Dynamic: `max(MIN, min(N/3+1, CAP))`
- `get_peer_nodes(asn)` - Get all other RPKI nodes
- Falls back to legacy {1,3,5,...,17} if not initialized

### DatasetLoader (shared_blockchain_stack/data_loader.py)

Reads the full CAIDA dataset into memory.

- `get_all_asns()` - All AS numbers
- `get_observations_for_asn(asn)` - Per-AS observation list
- `get_ground_truth_attacks()` - Attack labels
- `get_legitimate_prefixes()` - For VRP generation

### VirtualNode (shared_blockchain_stack/virtual_node.py)

Represents one AS running in a thread. Full blockchain participant.

- RPKI nodes: validate, create transactions, broadcast, vote, commit blocks, detect attacks, earn BGPCOIN
- Non-RPKI nodes: detect attacks, record observations, track trust ratings
- Collects detection results and trust scores

### NodeManager (shared_blockchain_stack/node_manager.py)

Creates shared blockchain infrastructure and manages all VirtualNodes.

- `start_all()` - Start all node threads
- `wait_for_completion(timeout)` - Block until done
- `get_all_detection_results()` - Collect from all nodes

### InMemoryMessageBus (blockchain_utils/message_bus.py)

Singleton message router replacing TCP sockets for P2P communication. Scales to 1000+ nodes without OS socket overhead.

- Per-node handler registration
- Routes transaction broadcasts, consensus votes, attack proposals
- Tracks stats: messages sent, delivered, dropped

### P2PTransactionPool (blockchain_utils/p2p_transaction_pool.py)

Per-RPKI-node transaction pool with knowledge-based voting.

- Broadcasts new transactions to up to MAX_BROADCAST_PEERS randomly selected peers
- Peers vote approve/reject based on their own knowledge base
- Collects votes until consensus threshold or timeout
- Supports both memory bus and TCP socket modes

### AttackDetector (blockchain_utils/attack_detector.py)

Detects 4 attack types on every BGP announcement:

| Attack Type | Detection Method | Severity |
|------------|-----------------|----------|
| PREFIX_HIJACK | ROA database check — announcing AS does not match authorized origin | HIGH |
| SUBPREFIX_HIJACK | Announced prefix is a more-specific subnet of an existing ROA entry with a different origin AS | HIGH |
| BOGON_INJECTION | Announced prefix falls within RFC 1918 / RFC 5737 / RFC 6598 reserved ranges | CRITICAL |
| ROUTE_FLAPPING | Same (prefix, origin_asn) announced more than threshold times within a sliding window | MEDIUM |

### AttackConsensus (blockchain_utils/attack_consensus.py)

Majority voting system for confirming detected attacks. When an attack is detected, the detecting node proposes a vote. Other nodes vote based on their own observations.

### BlockchainInterface (blockchain_utils/blockchain_interface.py)

File-based blockchain with:
- SHA-256 block hashing
- Merkle root computation for transaction integrity
- Hash chain linking (each block references previous block's hash)
- Full integrity verification (hash chain + Merkle roots)
- Thread-safe writes with file locking

### BGPCoinLedger (blockchain_utils/bgpcoin_ledger.py)

Token economy with rewards for block commits, voting, and attack detection. Total supply: 10,000,000 BGPCOIN. Treasury starts with full supply; rewards drain it over time.

### NonRPKIRatingSystem (blockchain_utils/nonrpki_rating.py)

Trust scores for non-RPKI ASes (0-100 scale, longitudinal tracking). Classification: Highly Trusted (90+), Trusted (70+), Neutral (50+), Suspicious (30+), Malicious (<30).

### StayRTRClient (blockchain_utils/stayrtr_client.py)

RPKI route validation using VRP data.

- `load()` - Read VRP JSON file
- `validate_route(prefix, origin_asn)` -> "valid"/"invalid"/"not_found"

### BGPMonitor (services/rpki_observer_service/bgp_monitor.py)

Dual-mode BGP monitor:
- **File mode** (legacy): reads bgpd.json from disk
- **Memory mode** (new): reads from DatasetLoader observations

## Consensus Model

BFT-style threshold consensus with configurable parameters:

- Formula: `max(CONSENSUS_MIN, min(N/3 + 1, CONSENSUS_CAP))` where N = number of RPKI validators
- Default: MIN=3, CAP=5
- Effective threshold: 5 signatures for all tested network sizes (58-206 RPKI nodes)
- Transaction types: regular (3s timeout), attack (5s timeout)
- On timeout: transaction committed with "insufficient consensus" or "single witness" status

## Results Format

```
results/<dataset_name>/<YYYYMMDD_HHMMSS>/
  detection_results.json     # Per-observation detection decisions
  trust_scores.json          # Per-AS trust scores + stats
  performance_metrics.json   # Precision, recall, F1 vs ground truth
  summary.json               # Aggregate dataset + node + performance summary
  run_config.json            # System hardware info + configuration
  blockchain_stats.json      # Blocks, transactions, integrity verification
  bgpcoin_economy.json       # Treasury balance, distributed, circulating supply
  nonrpki_ratings.json       # Trust rating per non-RPKI AS + distribution
  consensus_log.json         # Committed vs pending transaction counts
  attack_verdicts.json       # Attack proposals, votes, verdicts, confidence
  dedup_stats.json           # Observations deduplicated/throttled
  message_bus_stats.json     # P2P messages: sent, delivered, dropped
  README.md                  # Human-readable summary with all metrics in tables
```

## Configuration

All 40+ tunable hyperparameters are centralized in the `.env` file at the project root. The config loader (`config.py`) reads `.env` at startup and exposes values to every module. Parameters can be adjusted without modifying source code.

Categories: Consensus, P2P Network, Deduplication, Knowledge Base, Attack Detection, BGPCOIN Economy, Trust Rating, Attack Consensus.

See the main README for the full parameter reference.
