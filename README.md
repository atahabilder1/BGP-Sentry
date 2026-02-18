# BGP-Sentry (TrustChain)

A blockchain-based distributed BGP security framework that detects BGP hijack attacks using RPKI-validated consensus among autonomous systems. Uses real CAIDA AS-level Internet topology and rov-collector RPKI classification data.

## Overview

BGP-Sentry simulates a distributed blockchain network where **RPKI-enabled ASes** act as blockchain validators (voters, block committers) and **non-RPKI ASes** are monitored subjects whose routing behavior is tracked and rated. RPKI validators process BGP announcements from their vantage points, participate in Proof of Population (PoP) consensus voting, and collectively build trust ratings for non-RPKI ASes that lack cryptographic route authorization.

### Architecture

```
Dataset (CAIDA)  -->  DatasetLoader  -->  RPKINodeRegistry
                           |                  |
                           v                  v
                      NodeManager        RPKI-verified onboarding
                      (shared infrastructure)  (RIR certificates + ROAs)
                           |
            +--------------+--------------+
            |                             |
   RPKI VirtualNode              Non-RPKI VirtualNode
   (blockchain validator)        (monitored subject)
            |                             |
   +--------+--------+           +-------+-------+
   |        |        |           |       |       |
  P2P    RPKI     Attack      Attack  Rating  Detection
  Pool  Validator Detector   Detector System   Log
   |                |
   v                v
InMemoryMessageBus  AttackConsensus
(replaces TCP)      (majority voting)
   |                |
   v                v
BlockchainInterface  BGPCoinLedger
(write blocks)       (token rewards)
   |
   v
Results (13 output files)  -->  PosthocAnalyzer / BlockchainExplorer
```

### How It Works

1. **Dataset observations** are loaded per-AS and assigned to VirtualNodes
2. **RPKI nodes** (validators): receive an observation, validate it via StayRTR VRP, add to knowledge base, create a blockchain transaction, broadcast to peers via the in-memory message bus, peers vote approve/no_knowledge/reject (three-way), on Proof of Population (PoP) consensus the block is written to the blockchain, attack detection runs on committed transactions, attack verdicts are stored on-chain as immutable blocks, BGPCoin rewards are distributed
3. **Non-RPKI nodes** (monitored subjects): their routing behavior is observed and rated by RPKI validators. Non-RPKI ASes do not participate in blockchain consensus or voting — they are the subjects being monitored. Trust ratings (0-100) are assigned based on observed behavior: penalties for attacks, rewards for legitimate routing
4. **All P2P messaging** uses `InMemoryMessageBus` (replaces TCP sockets) so the system scales to 1000+ nodes without OS socket overhead
5. **Real-time monitoring** via Flask dashboard at `http://localhost:5555` — shows per-node TPS, BGP timestamp progress, lag detection, and attack stats live during runs

### Key Components

- **RPKINodeRegistry** - Data-driven registry loaded from `as_classification.json` (no hardcoded AS lists)
- **DatasetLoader** - Reads CAIDA datasets (observations, ground truth, classification)
- **NodeManager** - Creates shared blockchain infrastructure and wires it into each VirtualNode
- **VirtualNode** - Per-AS processing unit: RPKI nodes do full consensus + voting, non-RPKI nodes are monitored subjects with trust ratings
- **InMemoryMessageBus** - Singleton message router replacing TCP sockets for P2P communication
- **P2PTransactionPool** - Per-RPKI-node transaction pool with knowledge-based voting
- **AttackDetector** - Detects 4 attack types: PREFIX_HIJACK, SUBPREFIX_HIJACK, BOGON_INJECTION, ROUTE_FLAPPING
- **AttackConsensus** - Majority voting system for confirming detected attacks
- **BlockchainInterface** - File-based blockchain with SHA-256 hashing, Merkle roots, and integrity verification
- **BGPCoinLedger** - Token economy with rewards for block commits, voting, and attack detection
- **NonRPKIRatingSystem** - Trust scores for non-RPKI ASes (0-100, longitudinal tracking)
- **StayRTR Client** - RPKI route validation using VRP (Validated ROA Payload) data
- **Consensus** - Proof of Population (PoP): `max(3, N/3 + 1)` where N = number of RPKI validators. One node = one vote; RPKI onboarding prevents Sybil attacks
- **PosthocAnalyzer** - Post-experiment analysis: accuracy by attack type, consensus efficiency, BGPCoin distribution, blockchain growth

## Quick Start

**Requirements:** Python 3.10+

```bash
# 1. Setup virtual environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Run experiment with a dataset
python3 main_experiment.py --dataset caida_100

# 3. Run with longer duration
python3 main_experiment.py --dataset caida_100 --duration 600

# 4. Run with larger dataset
python3 main_experiment.py --dataset caida_1000 --duration 600
```

Results are written to `results/<dataset_name>/<YYYYMMDD_HHMMSS>/`.

## Real-Time Monitoring Dashboard

When an experiment is running, a live dashboard is available at `http://localhost:5555` showing per-node TPS, BGP timestamp progress, buffer usage, and attack detection stats.

### How It Works

The dashboard runs **on the server** as part of the experiment process. When you connect via SSH with port forwarding, the server's port 5555 is tunneled to your local PC so you can open it in your local browser.

**Workflow:**

```
Your PC (browser)  ---SSH tunnel--->  Remote Server (experiment + dashboard)
http://localhost:5555                  Flask dashboard on port 5555
```

**Step-by-step:**

```bash
# Step 1: Connect to the server with port forwarding
ssh -L 5555:localhost:5555 user@your-server-ip

# Step 2: On the server, run the experiment (dashboard starts automatically)
cd ~/code/BGP-Sentry
python3 main_experiment.py --dataset caida_100 --duration 600

# Step 3: On your local PC, open your browser
#         Go to http://localhost:5555
#         The live dashboard appears -- updates every 2 seconds
```

The dashboard starts automatically when the experiment starts and stops when the experiment ends. No extra setup needed on the server side.

### SSH Variations

```bash
# With SSH key
ssh -i ~/.ssh/mykey -L 5555:localhost:5555 user@server

# Custom SSH port
ssh -p 2222 -L 5555:localhost:5555 user@server

# Tunnel only (no interactive shell, useful as a second terminal)
ssh -N -L 5555:localhost:5555 user@server
```

**VS Code Remote SSH** auto-detects forwarded ports -- check the "Ports" tab or add port 5555 manually.

### Automatic Port Forwarding (No Extra Flags)

To avoid typing `-L 5555:localhost:5555` every time, add this to `~/.ssh/config` **on your local PC**:

```
Host bgp-sentry-server
    HostName your-server-ip
    User your-username
    IdentityFile ~/.ssh/mykey
    LocalForward 5555 localhost:5555
```

Then just connect normally -- the dashboard port forwards automatically:

```bash
ssh bgp-sentry-server
# Port 5555 is already forwarded, open http://localhost:5555 in your browser
```

## Commands Reference

### Running Experiments

```bash
# Single dataset
python3 main_experiment.py --dataset caida_100
python3 main_experiment.py --dataset caida_200 --duration 300
python3 main_experiment.py --dataset caida_500 --duration 600
python3 main_experiment.py --dataset caida_1000 --duration 600

# Run all datasets sequentially
for ds in caida_100 caida_200 caida_500 caida_1000; do
    python3 main_experiment.py --dataset $ds --duration 600
done
```

### VRP Generation (StayRTR)

```bash
# Generate VRP from dataset (done automatically by main_experiment.py)
python3 scripts/generate_vrp.py dataset/caida_100 stayrtr/vrp_generated.json

# (Optional) Install StayRTR daemon
bash scripts/setup_stayrtr.sh

# (Optional) Run StayRTR daemon for real-time RTR queries
stayrtr -bind :8282 -json.path stayrtr/vrp_generated.json
```

### Cleanup Between Runs

```bash
# Remove generated VRP
rm -f stayrtr/vrp_generated.json

# Remove all results
rm -rf results/
```

## Datasets

Located in `dataset/`. Each dataset is a BFS subgraph of the real CAIDA AS-level Internet topology with real RPKI classification from rov-collector.

| Dataset | ASes | RPKI Validators | Non-RPKI ASes | Announcements | Attack % |
|---------|------|----------------|--------------------|---------------|----------|
| caida_100 | 100 | 58 | 42 | ~7,000 | ~4.7% |
| caida_200 | 200 | 101 | 99 | ~15,000 | ~3.2% |
| caida_500 | 500 | 206 | 294 | ~38,500 | ~6.1% |
| caida_1000 | 1000 | 366 | 634 | ~80,600 | ~4.6% |

Each dataset contains:
- `as_classification.json` - RPKI/non-RPKI classification and blockchain roles
- `observations/AS<N>.json` - Per-AS BGP observations (64 scenarios: 60 legitimate + 4 attack types)
- `ground_truth/ground_truth.json` - Attack labels for evaluation

Attack types: PREFIX_HIJACK, SUBPREFIX_HIJACK, BOGON_INJECTION, ROUTE_FLAPPING

See `dataset/DATASET_METHODOLOGY.md` for full methodology.

## Results

Each run produces 13 structured output files in `results/<dataset>/<timestamp>/`:

| File | Contents |
|------|----------|
| `detection_results.json` | Per-observation detection decisions from all nodes |
| `trust_scores.json` | Per-AS trust scores, observation counts, and stats |
| `performance_metrics.json` | Precision, recall, F1 vs ground truth |
| `summary.json` | Aggregate dataset + node + performance summary |
| `run_config.json` | Configuration, system info (CPU, RAM for benchmarking) |
| `blockchain_stats.json` | Blocks written, total transactions, integrity check |
| `bgpcoin_economy.json` | Treasury balance, distributed, burned, per-node balances |
| `nonrpki_ratings.json` | Rating for each non-RPKI AS + history over time |
| `consensus_log.json` | Consensus decisions: committed, pending, transaction counts |
| `attack_verdicts.json` | Attack proposals, votes, verdicts, confidence scores |
| `dedup_stats.json` | Observations deduplicated/throttled (RPKI + non-RPKI) |
| `message_bus_stats.json` | P2P message bus: sent, delivered, dropped counts |
| `README.md` | Human-readable summary with throughput (TPS), detection accuracy, blockchain stats, and all metrics |

The `run_config.json` includes system hardware information (CPU model, core count, RAM) so you can compare performance across different machines and report whether better hardware configurations yield better results.

## Experimental Results

Tested on three CAIDA-derived datasets with 300-second simulation duration.

**Hardware:** Intel i7-13700 (24 cores), 62.5 GB RAM, Linux 6.17, Python 3.10

### Dataset Characteristics

| Metric | caida_100 | caida_200 | caida_500 |
|--------|-----------|-----------|-----------|
| Total ASes | 100 | 200 | 500 |
| RPKI Validators | 58 | 101 | 206 |
| Non-RPKI ASes | 42 | 99 | 294 |
| Total Observations | 7,069 | 15,038 | 38,499 |
| Attack Observations | 333 (4.7%) | 476 (3.2%) | 2,364 (6.1%) |
| Unique Attack Patterns | 4 | 4 | 4 |

### Blockchain Performance

| Metric | caida_100 | caida_200 | caida_500 |
|--------|-----------|-----------|-----------|
| Blocks Written | 4,581 | 5,164 | 5,474 |
| Blockchain Integrity | Valid | Valid | Valid |
| Transactions Created | 2,864 | 5,545 | 8,799 |
| Consensus Committed | 2,481 | 2,623 | 2,906 |
| Consensus Commit Rate | 86.6% | 47.3% | 33.0% |
| Consensus Threshold | 5 signatures | 5 signatures | 5 signatures |

### Attack Detection Accuracy

| Metric | caida_100 | caida_200 | caida_500 |
|--------|-----------|-----------|-----------|
| Ground Truth Attacks (unique) | 4 | 4 | 4 |
| True Positives | 3 | 4 | 4 |
| False Positives | 41 | 38 | 53 |
| False Negatives | 1 | 0 | 0 |
| **Precision** | **0.068** | **0.095** | **0.070** |
| **Recall** | **0.750** | **1.000** | **1.000** |
| **F1 Score** | **0.125** | **0.174** | **0.131** |

### Token Economy

| Metric | caida_100 | caida_200 | caida_500 |
|--------|-----------|-----------|-----------|
| Total BGPCOIN Supply | 10,000,000 | 10,000,000 | 10,000,000 |
| BGPCOIN Distributed | 38,721 | 20,217 | 29,434 |
| Circulating Supply | 33,821 | 18,317 | 23,694 |
| Participating RPKI Nodes | 58 | 101 | 206 |

### Non-RPKI Trust Ratings

| Metric | caida_100 | caida_200 | caida_500 |
|--------|-----------|-----------|-----------|
| ASes Rated | 41 | 31 | 17 |
| Average Trust Score | 42.20 | 40.81 | 41.47 |
| Neutral (50+) | 9 | 4 | 4 |
| Suspicious (30-49) | 32 | 26 | 12 |
| Malicious (<30) | 0 | 1 | 1 |

### P2P Network

| Metric | caida_100 | caida_200 | caida_500 |
|--------|-----------|-----------|-----------|
| Messages Sent | 979,084 | 1,575,910 | 12,349,312 |
| Messages Delivered | 979,084 | 1,575,908 | 12,349,048 |
| Messages Dropped | 0 | 0 | 0 |
| Delivery Rate | 100% | ~100% | ~100% |

### Throughput Benchmark (caida_100, 100 nodes)

Tested by increasing the `SIMULATION_SPEED_MULTIPLIER` to push BGP data through the blockchain consensus pipeline faster than real-time. This measures the maximum throughput the network can sustain before nodes fall behind the clock.

The system maintains **perfect detection accuracy (Precision 1.0, Recall 1.0, F1 1.0) at all tested speeds** from 1x to 10x real-time.

| Speed | Wall Time | Network TPS | Precision | Recall | F1 |
|-------|-----------|-------------|-----------|--------|------|
| 1x (real-time) | ~1,700s | 4.2 | 1.000 | 1.000 | 1.000 |
| 2x | 869s | 8.1 | 1.000 | 1.000 | 1.000 |
| 3x | 580s | 12.2 | 1.000 | 1.000 | 1.000 |
| 4x | 439s | 16.1 | 1.000 | 1.000 | 1.000 |
| 5x | 350s | 20.2 | 1.000 | 1.000 | 1.000 |
| 6x | 298s | 23.7 | 1.000 | 1.000 | 1.000 |
| 7x | 254s | 27.8 | 1.000 | 1.000 | 1.000 |
| 8x | 228s | 31.0 | 1.000 | 1.000 | 1.000 |
| 9x | 199s | 35.5 | 1.000 | 1.000 | 1.000 |
| **10x** | **192s** | **36.8** | **1.000** | **1.000** | **1.000** |

**Peak throughput: 36.8 transactions per second** (network-wide) at 10x speed with 100 nodes (58 RPKI validators).

**Interpretation:**
- At 1x speed, the system processes 28 minutes of BGP activity in real-time with zero lag
- At 10x speed, the same data completes in ~3.2 minutes with no accuracy loss
- Network TPS scales linearly with speed multiplier up to ~6x, then diminishes as consensus round-trip overhead becomes the bottleneck
- Detection accuracy remains perfect (F1 = 1.0) at all speeds — the deduplication and consensus mechanisms do not drop attack observations regardless of throughput pressure

**What limits throughput beyond 10x:** Each BGP announcement triggers a separate consensus round: broadcast vote request to 5 peers, each peer performs knowledge base lookup + Ed25519 signing + vote response, merger collects 3+ signatures, then commits the block. At high speeds, the 16-thread P2P message bus saturates as 58 RPKI nodes simultaneously broadcast. Transaction batching (grouping multiple announcements per consensus round) would push this limit higher.

To reproduce: `python3 scripts/benchmark_throughput.py --dataset caida_100`

### Key Observations

1. **High recall (75-100%):** The system successfully detects all injected attack patterns. With 200+ nodes, recall reaches 100%.
2. **Low precision (~7-10%):** The route flapping detector generates false positives on legitimate prefixes announced frequently. Tunable via `FLAP_THRESHOLD` in `.env`.
3. **Consensus scales with expected trade-offs:** Commit rate decreases with network size (86.6% at 100 nodes to 33.0% at 500 nodes) due to PoP consensus contention. Tunable via `CONSENSUS_CAP_SIGNATURES` and `P2P_REGULAR_TIMEOUT`.
4. **Zero message loss:** The in-memory message bus achieves 100% delivery across all experiments.
5. **Blockchain integrity verified:** SHA-256 hash chains and Merkle roots pass full verification for every block in every run.
6. **Trust ratings reflect behavior:** Non-RPKI ASes originating attacks see scores drop from 50 (neutral) to suspicious (30-49), while clean ASes maintain neutral or higher.
7. **Token economy functions correctly:** BGPCOIN rewards are distributed proportionally to participation.
8. **Real-time processing achieved:** With 9 optimizations (see `docs/OPTIMIZATIONS.md`), the system processes BGP announcements in real-time with zero lag. Peak throughput: 36.8 network TPS at 10x speed on commodity hardware.

## Project Structure

```
BGP-Sentry/
  README.md                           # This file
  LICENSE                             # MIT License
  .env                                # Tunable hyperparameters (see below)
  .gitignore
  main_experiment.py                  # Main entry point: --dataset caida_100
  requirements.txt                    # Python dependencies

  scripts/
    generate_vrp.py                   # Generate VRP table from dataset
    generate_analysis_notebook.py     # Jupyter notebook generator for results
    setup_stayrtr.sh                  # StayRTR installation helper

  dataset/                            # CAIDA datasets (version controlled)
    DATASET_METHODOLOGY.md
    caida_100/
    caida_200/
    caida_500/
    caida_1000/

  analysis/                           # Post-experiment analysis (standalone CLI tools)
    posthoc_analysis.py               # Accuracy, economy, blockchain growth analysis
    blockchain_forensics.py           # Forensic queries against blockchain records
    targeted_attack_analyzer.py       # Targeted attack & unconfirmed tx analysis
    blockchain_explorer.py            # Interactive CLI for browsing blocks and verifying chain

  nodes/rpki_nodes/
    shared_blockchain_stack/          # Core blockchain infrastructure
      blockchain_utils/
        config.py                     # Central config loader (reads .env)
        message_bus.py                # In-memory P2P message bus (replaces TCP)
        rpki_node_registry.py         # Data-driven RPKI node registry from dataset
        stayrtr_client.py             # RPKI route validation via StayRTR VRP
        p2p_transaction_pool.py       # Per-node tx pool + PoP consensus voting
        attack_consensus.py           # Majority voting for confirming attacks
        attack_detector.py            # Detects 4 attack types
        blockchain_interface.py       # File-based blockchain: blocks, Merkle roots
        bgpcoin_ledger.py             # Token economy: rewards, burn, treasury
        nonrpki_rating.py             # Trust scores for non-RPKI ASes (0-100)
        signature_utils.py            # Ed25519 signing for transactions
        integrated_trust_manager.py   # Trust scoring engine
        governance_system.py          # On-chain governance proposals
        behavioral_analysis.py        # Behavioral pattern analysis for governance
      network_stack/
        relevant_neighbor_cache.py    # AS-path neighbor cache for optimized voting
      services/
        rpki_observer_service/
          bgp_monitor.py              # BGP monitor (file + memory mode)
          transaction_creator.py      # Creates blockchain transactions from BGP events
        consensus_service/
          consensus_main.py           # Consensus service (dynamic threshold)
          blockchain_writer.py        # Writes committed blocks to chain
          transaction_validator.py    # Validates incoming transactions
      data_loader.py                  # Reads CAIDA datasets (observations, ground truth)
      virtual_node.py                 # Full blockchain participant per AS
      node_manager.py                 # Creates shared infra + manages all nodes

    bgp_attack_detection/             # Attack detection subsystem
      detectors/
        prefix_hijack_detector.py     # Prefix hijack detection
        subprefix_detector.py         # Subprefix hijack detection
        route_leak_detector.py        # Route leak detection
      validators/
        rpki_validator.py             # RPKI validation using StayRTR VRP data
        irr_validator.py              # IRR database validation
      attack_detector.py              # Unified detector (routes to specific detectors)
    rpki_verification_interface/
      verifier.py                     # RPKI certificate verification interface

  simulation_helpers/                 # Timing + orchestration
    coordination/
      orchestrator.py                 # SimulationOrchestrator (starts/stops nodes)
      health_monitor.py               # Runtime health checks
    timing/
      shared_clock.py                 # Shared simulation clock

  monitoring/                          # Real-time simulation dashboard
    dashboard_server.py               # Flask app with JSON API + stat collector
    templates/dashboard.html          # Self-contained HTML dashboard (Chart.js)

  docs/                               # Complete technical documentation
    BGP_Sentry_Detailed_Documentation.md  # Full reference book (14 chapters, clickable TOC)
    BGP_Sentry_Detailed_Documentation.pdf # PDF version of the above
  stayrtr/                            # StayRTR runtime (gitignored)
  results/                            # Experiment results (gitignored, 15 files per run)
```

## Hyperparameters (`.env`)

All tunable parameters are centralized in the `.env` file at the project root. Edit this file to fine-tune the simulation without changing source code. The config loader (`config.py`) reads `.env` at startup and exposes values to every module.

### Consensus

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CONSENSUS_MIN_SIGNATURES` | 3 | PoP minimum signatures to commit a block |
| `CONSENSUS_CAP_SIGNATURES` | 5 | Upper cap on required signatures (keeps large networks practical) |

Formula: `max(MIN, min(N/3+1, CAP))` where N = RPKI node count.

### P2P Network

| Parameter | Default | Description |
|-----------|---------|-------------|
| `P2P_REGULAR_TIMEOUT` | 3s | Timeout waiting for consensus votes on regular BGP updates |
| `P2P_ATTACK_TIMEOUT` | 5s | Timeout for attack-related transactions (higher priority) |
| `P2P_MAX_BROADCAST_PEERS` | 5 | Max peers to broadcast to (caps O(N^2) message volume) |
| `P2P_BASE_PORT` | 8000 | Base port for TCP sockets (only when `use_memory_bus=False`) |

### Deduplication & Skip Windows

| Parameter | Default | Description |
|-----------|---------|-------------|
| `RPKI_DEDUP_WINDOW` | 300s (5 min) | RPKI nodes skip same (prefix, origin) within this window. Attacks always bypass. |
| `NONRPKI_DEDUP_WINDOW` | 120s (2 min) | Non-RPKI nodes skip same (prefix, origin) within this window. Attacks always bypass. |
| `SAMPLING_WINDOW_SECONDS` | 300s (5 min) | P2P pool sampling window (matches `RPKI_DEDUP_WINDOW`) |

### Knowledge Base

| Parameter | Default | Description |
|-----------|---------|-------------|
| `KNOWLEDGE_WINDOW_SECONDS` | 480s | How long each node remembers BGP observations (for voting) |
| `KNOWLEDGE_CLEANUP_INTERVAL` | 60s | Garbage-collection interval for old observations |

### Buffer Capacity Limits

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PENDING_VOTES_MAX_CAPACITY` | 5000 | Max pending transactions before oldest are force-timed-out |
| `COMMITTED_TX_MAX_SIZE` | 50000 | Max committed tx IDs tracked before oldest are evicted |
| `COMMITTED_TX_CLEANUP_INTERVAL` | 300s | How often to garbage-collect old committed tx IDs |
| `KNOWLEDGE_BASE_MAX_SIZE` | 50000 | Max observations in knowledge base before oldest trimmed |
| `LAST_SEEN_CACHE_MAX_SIZE` | 100000 | Max entries in last-seen sampling cache before eviction |

### Attack Detection — Route Flapping

| Parameter | Default | Description |
|-----------|---------|-------------|
| `FLAP_WINDOW_SECONDS` | 60s | Sliding window for counting state changes |
| `FLAP_THRESHOLD` | 5 | Unique state changes above this = ROUTE_FLAPPING |
| `FLAP_DEDUP_SECONDS` | 2s | Observations within this interval count as same event |

### BGPCOIN Token Economy

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BGPCOIN_TOTAL_SUPPLY` | 10,000,000 | Total token supply (treasury starts with this) |
| `BGPCOIN_REWARD_BLOCK_COMMIT` | 10 | Reward for committing a block |
| `BGPCOIN_REWARD_VOTE_APPROVE` | 1 | Reward for voting approve on a transaction |
| `BGPCOIN_REWARD_FIRST_COMMIT_BONUS` | 5 | Bonus for being first node to commit |
| `BGPCOIN_REWARD_ATTACK_DETECTION` | 100 | Large reward for detecting an attack |
| `BGPCOIN_REWARD_DAILY_MONITORING` | 10 | Daily reward for active monitoring |
| `BGPCOIN_PENALTY_FALSE_REJECT` | 2 | Penalty for incorrect rejection vote |
| `BGPCOIN_PENALTY_FALSE_APPROVE` | 5 | Penalty for approving a fake announcement |
| `BGPCOIN_PENALTY_MISSED_PARTICIPATION` | 1 | Penalty for not participating in voting |

Multiplier ranges (applied to base rewards based on node history):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BGPCOIN_MULTIPLIER_ACCURACY_MIN/MAX` | 0.5 / 1.5 | Historical correctness multiplier |
| `BGPCOIN_MULTIPLIER_PARTICIPATION_MIN/MAX` | 0.8 / 1.2 | Participation consistency multiplier |
| `BGPCOIN_MULTIPLIER_QUALITY_MIN/MAX` | 0.9 / 1.3 | Evidence quality multiplier |

### Non-RPKI Trust Rating

| Parameter | Default | Description |
|-----------|---------|-------------|
| `RATING_INITIAL_SCORE` | 50 | Starting score (neutral) |
| `RATING_MIN_SCORE` / `RATING_MAX_SCORE` | 0 / 100 | Score bounds |
| `RATING_PENALTY_PREFIX_HIJACK` | -20 | Penalty for IP prefix hijacking |
| `RATING_PENALTY_SUBPREFIX_HIJACK` | -18 | Penalty for sub-prefix hijacking |
| `RATING_PENALTY_BOGON_INJECTION` | -25 | Penalty for bogon prefix injection |
| `RATING_PENALTY_ROUTE_FLAPPING` | -10 | Penalty for route flapping |
| `RATING_PENALTY_ROUTE_LEAK` | -15 | Penalty for route leak |
| `RATING_PENALTY_REPEATED_ATTACK` | -30 | Additional penalty (attack within 30 days) |
| `RATING_PENALTY_PERSISTENT_ATTACKER` | -50 | Penalty for 3+ total attacks |
| `RATING_REWARD_MONTHLY_GOOD_BEHAVIOR` | +5 | Monthly bonus for no attacks |
| `RATING_REWARD_FALSE_ACCUSATION_CLEARED` | +2 | Cleared false accusation reward |
| `RATING_REWARD_PER_100_LEGITIMATE` | +1 | Reward per 100 legitimate announcements |
| `RATING_REWARD_HIGHLY_TRUSTED_BONUS` | +10 | Bonus for 90+ score for 3 months |
| `RATING_THRESHOLD_HIGHLY_TRUSTED` | 90 | Score to be classified "Highly Trusted" |
| `RATING_THRESHOLD_TRUSTED` | 70 | Score to be classified "Trusted" |
| `RATING_THRESHOLD_NEUTRAL` | 50 | Score to be classified "Neutral" |
| `RATING_THRESHOLD_SUSPICIOUS` | 30 | Score to be classified "Suspicious" |

### Attack Consensus

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ATTACK_CONSENSUS_MIN_VOTES` | 3 | Minimum votes to finalize an attack verdict |
| `ATTACK_CONSENSUS_REWARD_DETECTION` | 10 | BGPCOIN reward for detecting attack |
| `ATTACK_CONSENSUS_REWARD_CORRECT_VOTE` | 2 | BGPCOIN reward for correct vote |
| `ATTACK_CONSENSUS_PENALTY_FALSE_ACCUSATION` | -20 | BGPCOIN penalty for false detection |

### Transaction Batching

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BATCH_SIZE` | 1 | Transactions per batch block (1 = no batching, 10 = 3-5x TPS) |
| `BATCH_TIMEOUT` | 0.5s | Max wait before flushing a partial batch |

## Documentation

Detailed technical documentation is in the `docs/` directory:

- **[docs/BGP_Sentry_Detailed_Documentation.md](docs/BGP_Sentry_Detailed_Documentation.md)** — Complete technical reference book (14 chapters): architecture, PoP consensus, attack detection, consensus escalation, optimizations, throughput analysis, experimental results, configuration, and more
- **[docs/BGP_Sentry_Detailed_Documentation.pdf](docs/BGP_Sentry_Detailed_Documentation.pdf)** — PDF version (print-ready)

## StayRTR Integration

BGP-Sentry uses [StayRTR](https://github.com/bgp/stayrtr) for RPKI route validation. The VRP (Validated ROA Payload) table is generated from dataset observations:

1. `scripts/generate_vrp.py` extracts legitimate (prefix, origin_asn) pairs
2. Outputs StayRTR-compatible JSON with ROA entries
3. `StayRTRClient` validates routes against this VRP table
4. Results: "valid" (ROA matches), "invalid" (wrong origin), "not_found" (no ROA)

## Blockchain Explorer

An interactive CLI tool for browsing blockchain blocks, inspecting attack verdicts, and verifying chain integrity.

```bash
# Interactive mode
python3 analysis/blockchain_explorer.py results/caida_100/*/blockchain.json

# Verify chain integrity
python3 analysis/blockchain_explorer.py results/caida_100/*/blockchain.json --verify

# List all attack verdicts
python3 analysis/blockchain_explorer.py results/caida_100/*/blockchain.json --verdicts

# Search by prefix or AS
python3 analysis/blockchain_explorer.py results/caida_100/*/blockchain.json --search-prefix "8.8.8.0/24"
python3 analysis/blockchain_explorer.py results/caida_100/*/blockchain.json --search-as 15169
```

**Interactive commands:** `list`, `block <N>`, `verdicts`, `verdict <ID>`, `search prefix <P>`, `search as <ASN>`, `types`, `verify`, `export <file>`.

## Post-Hoc Forensic Analysis

Three standalone analysis modules query the blockchain offline for security intelligence:

1. **Blockchain Forensics** (`analysis/blockchain_forensics.py`) — Attacker profiling, prefix ownership history, observer cross-reference, audit trail generation
2. **Targeted Attack Analyzer** (`analysis/targeted_attack_analyzer.py`) — Single-witness patterns, consensus escalation detection, temporal clustering
3. **Longitudinal Behavior Analysis** (`analysis/posthoc_analysis.py`) — Trust score trajectories, rating drift, repeat offenders, BGPCoin economy health

All outputs are reproducible from blockchain data alone. Any party with a chain replica can independently verify every conclusion.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Author

Anik Tahabilder
