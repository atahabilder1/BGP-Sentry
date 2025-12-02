# BGP-Sentry Collaborator Guide

**Welcome!** This guide helps new collaborators understand the BGP-Sentry system architecture, design decisions, and research methodology.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Key Design Decisions](#2-key-design-decisions)
3. [Critical Discussion Points](#3-critical-discussion-points)
4. [Experimental Protocol](#4-experimental-protocol)
5. [Post-Hoc Analysis Framework](#5-post-hoc-analysis-framework)
6. [Getting Started](#6-getting-started)
7. [Open Research Questions](#7-open-research-questions)

---

## 1. System Overview

### What is BGP-Sentry?

BGP-Sentry is a **distributed blockchain-based BGP security monitoring system** that uses consensus among RPKI-enabled autonomous systems to detect and prevent BGP attacks (prefix hijacks, route leaks, etc.).

### Core Innovation: Knowledge-Based Voting

Unlike traditional blockchain consensus (Proof-of-Work, Proof-of-Stake), BGP-Sentry uses **knowledge-based voting**:

- Nodes only vote on BGP announcements they've personally observed
- Votes are based on local knowledge bases (8-minute time window)
- Consensus threshold: 3/9 nodes (33%) must approve
- This mimics real-world BGP: operators only trust what they see

### Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                    BGP-Sentry Network                           │
│                                                                 │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐            │
│  │ AS01 │──│ AS03 │──│ AS05 │──│ AS07 │──│ AS09 │            │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘            │
│      │         │         │         │         │                 │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                      │
│  │ AS11 │──│ AS13 │──│ AS15 │──│ AS17 │                      │
│  └──────┘  └──────┘  └──────┘  └──────┘                      │
│                                                                 │
│  Each node:                                                     │
│  • Monitors BGP announcements                                   │
│  • Maintains local blockchain                                   │
│  • Holds BGPCOIN balance                                        │
│  • Communicates via P2P sockets                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | File Location |
|-----------|---------|---------------|
| **P2P Transaction Pool** | Consensus engine, voting, timeouts | `shared_blockchain_stack/blockchain_utils/p2p_transaction_pool.py` |
| **BGPCOIN Ledger** | Token economics, rewards | `shared_blockchain_stack/blockchain_utils/bgpcoin_ledger.py` |
| **Attack Detector** | RPKI/IRR validation, attack detection | `bgp_attack_detection/attack_detector.py` |
| **Governance System** | Decentralized decision-making | `shared_blockchain_stack/blockchain_utils/governance_system.py` |
| **Blockchain Interface** | Write/read blockchain data | `shared_blockchain_stack/blockchain_interface.py` |
| **Main Orchestrator** | Experiment coordination | `main_experiment.py` |

---

## 2. Key Design Decisions

### Decision 1: Simulated Distributed System vs. Real Blockchain

**Choice:** Build custom distributed system with P2P sockets instead of using Ethereum/Hyperledger.

**Rationale:**
- Full control over consensus mechanism (knowledge-based voting)
- No smart contract gas fees or performance constraints
- Easier to inject attacks and control timing
- Research flexibility (can modify any component)

**Trade-off:** Less realistic than production blockchain, but sufficient for academic research.

**Discussion Point:** Would deployment on a real blockchain framework provide additional insights?

---

### Decision 2: Consensus Threshold (3/9 = 33%)

**Choice:** Require only 3 out of 9 nodes to reach consensus (33% threshold).

**Rationale:**
- BGP is globally observed but locally validated
- Not all RPKI nodes will see every announcement (routing asymmetry)
- Too high threshold (e.g., 6/9) would reject legitimate announcements
- Byzantine fault tolerance: Can tolerate up to 2 malicious nodes

**Trade-off:** Lower threshold = higher liveness, but potentially more false positives.

**Discussion Point:**
- What if 4 nodes collude? System breaks.
- Should threshold be dynamic based on announcement type?
- Compare to traditional BFT (2f+1 out of 3f+1 nodes)?

---

### Decision 3: BGPCOIN Token Economics

**Choice:** Custom token with 50% burn / 50% recycle model.

**Parameters:**
- Total supply: 10,000,000 BGPCOIN
- Block commit reward: 10 BGPCOIN
- First-to-commit bonus: +5 BGPCOIN
- Vote reward: 1 BGPCOIN per correct vote
- Spending: 50% burned, 50% returned to treasury

**Rationale:**
- Incentivize honest participation and accurate voting
- Deflationary pressure prevents infinite supply
- Recycling ensures long-term sustainability
- Weighted voting prevents Sybil attacks

**Trade-off:**
- If nodes hoard tokens, voting power becomes concentrated
- If treasury depletes, rewards stop
- No external value (can't trade for real currency)

**Discussion Point:**
- Is the economic model sustainable for 10 years?
- Should there be a halving mechanism like Bitcoin?
- Alternative: Proof-of-Stake with slashing?

---

### Decision 4: Transaction Timeout Mechanism

**Choice:**
- Regular announcements: 60-second timeout
- Attack transactions: 180-second timeout

**Rationale:**
- Prevents buffer overflow (unbounded pending transactions)
- Ensures all observations eventually recorded
- Longer timeout for attacks (more analysis time)

**Consensus Status on Timeout:**
- `CONFIRMED`: 3+ approve votes (write normally)
- `INSUFFICIENT_CONSENSUS`: 1-2 approve votes (partial agreement)
- `SINGLE_WITNESS`: 0 approve votes (unique observation)

**Discussion Point:**
- What if legitimate votes arrive at 61 seconds due to network delay?
- Should timeouts be adaptive (longer during congestion)?
- How to distinguish network delay from genuine disagreement?

---

### Decision 5: Sampling Logic (1-hour window)

**Choice:** Record each (IP prefix, AS number) pair at most once per hour.

**Rationale:**
- BGP announcements are often repetitive (keepalives, redundant paths)
- Without sampling: 10,000+ blockchain entries per hour
- With sampling: ~200 unique prefix-AS pairs per hour
- 98% reduction in blockchain bloat

**Attack Bypass:** Attacks always recorded (bypass sampling).

**Discussion Point:**
- Is 1 hour too long? Too short?
- What if a legitimate change happens within 1 hour (prefix withdrawn then re-announced)?
- Should sampling be adaptive per prefix (stable prefixes = longer window)?

---

### Decision 6: Vote Deduplication (Security)

**Choice:** Each AS can vote once per transaction. Duplicates rejected.

**Security Rules:**
1. Track voters per transaction
2. Reject duplicate votes with warning (`REPLAY ATTACK DETECTED`)
3. Reject if vote count exceeds total nodes (overflow protection)

**Rationale:**
- Prevents malicious nodes from inflating vote counts
- Protects consensus integrity
- Simple but effective security measure

**Discussion Point:**
- What about vote suppression (node drops votes)?
- Should there be penalties for replay attempts?
- Byzantine agreement vs. practical Byzantine fault tolerance?

---

## 3. Critical Discussion Points

These are **open questions** that collaborators should discuss and potentially research.

### A. Security & Attack Resilience

#### Q1: Byzantine Fault Tolerance Limits

**Current State:** System can tolerate up to 2 malicious nodes (with 3/9 threshold).

**Problem:** If 3+ nodes collude, they can:
- Approve fake announcements (false positives)
- Reject legitimate announcements (false negatives)
- Manipulate attack detection

**Discussion:**
- Should we increase threshold to 6/9 (traditional BFT 2/3 majority)?
- Would this hurt liveness (too many rejections)?
- Can we detect collusion patterns in voting history?

---

#### Q2: Attack Detection Coverage

**Detectable Attacks:**
- Prefix hijacking (RPKI validation)
- Sub-prefix hijacking (more specific prefix)
- Route leaks (AS path validation)

**Non-Detectable Attacks:**
- AS path manipulation (if attacker controls valid path)
- BGP hijacking with valid ROAs (compromised AS)
- BGP session hijacking (TCP-level attacks)

**Discussion:**
- What's the false positive/negative rate for each attack type?
- Can we integrate additional validation (IRR, historical data)?
- Should we use machine learning for anomaly detection?

---

#### Q3: Timeout Security Implications

**Scenario:** Attacker floods network with fake announcements, causing:
- Legitimate votes delayed beyond 60s timeout
- Transactions committed with `INSUFFICIENT_CONSENSUS`
- False data in blockchain

**Discussion:**
- Should timeout be adaptive (extend during high load)?
- Should `SINGLE_WITNESS` transactions be treated differently in analysis?
- Can we retroactively upgrade transaction status?

---

### B. Performance & Scalability

#### Q4: Blockchain Growth Rate

**Current Parameters:**
- 1-hour sampling window
- ~200 unique announcements/hour (with sampling)
- Each transaction ~2KB (JSON)
- **Expected growth:** ~10 MB/day per node

**Projection:**
- 1 month: 300 MB
- 1 year: 3.6 GB
- 10 years: 36 GB

**Discussion:**
- Is this acceptable for a blockchain?
- Should we use database instead of JSON files?
- Archival vs. active blockchain (prune old data)?

---

#### Q5: Network Scalability

**Current Network Load:**
- 9 nodes × 8 peers = 72 P2P connections
- Each transaction triggers 16 messages (8 requests + 8 responses)
- 200 transactions/hour × 16 = 3,200 messages/hour

**What if 50 nodes?**
- 50 nodes × 49 peers = 2,450 connections
- 200 transactions/hour × 98 messages = 19,600 messages/hour

**Discussion:**
- Can socket-based P2P scale to 50+ nodes?
- Should we use pub/sub model (Redis, RabbitMQ)?
- Gossip protocol to reduce message overhead?

---

### C. Economic Model

#### Q6: Token Distribution Fairness

**Concern:** "Rich get richer" effect.
- Nodes with more BGPCOIN have higher voting weight
- Voting earns more BGPCOIN
- New nodes can never catch up

**Discussion:**
- Is weighted voting necessary? Or use 1-node-1-vote?
- Should there be BGPCOIN grants for new nodes?
- Decay mechanism for old tokens?

---

#### Q7: Treasury Sustainability

**Initial State:** 10M BGPCOIN in treasury

**Burn Rate:** If 1000 BGPCOIN spent/month:
- 500 BGPCOIN burned
- 500 BGPCOIN recycled
- Net loss: 500 BGPCOIN/month

**Projection:** Treasury depletes in 20,000 months (1,666 years)

But if rewards exceed spending:
- No spending = treasury depletes via rewards only
- 10 BGPCOIN/block × 200 blocks/hour × 24h × 30 days = 1.44M BGPCOIN/month
- **Treasury depletes in 7 months!**

**Discussion:**
- Is spending happening? (governance votes, services)
- Should block rewards decrease over time (halving)?
- Proof-of-Stake instead (stake tokens to earn)?

---

### D. Experimental Validation

#### Q8: Data Realism

**Current Setup:** BGP announcements generated using **BGPy** simulator, extracted offline

**Data Generation Process:**
1. BGPy simulates AS topology and routing policies
2. BGP announcements generated with controllable attack injection
3. Announcements exported to logs (offline extraction)
4. BGP-Sentry reads pre-recorded announcement logs

**Advantages:**
- Full control over attack scenarios (type, timing, intensity)
- Reproducible experiments (same data for multiple runs)
- No dependency on live BGP feeds or external data sources
- Can simulate rare attacks (prefix hijacks, route leaks, etc.)

**Concerns:**
- Simulated BGP may not capture real-world complexity
- AS relationships and policies may be oversimplified
- BGP convergence timing may differ from reality
- No reactive attackers (attacks are pre-scripted)

**Discussion:**
- How realistic is BGPy's AS topology compared to real Internet?
- Should we validate against RouteViews/RIPE RIS data?
- Can we replay historical BGP incidents (YouTube hijack 2008, Pakistan-YouTube 2008)?
- Trade-off: Controlled simulation vs. real-world messiness?

---

#### Q9: Evaluation Metrics

**What defines success?**

Option 1: **Detection Accuracy**
- Precision, recall, F1-score for attack detection
- Benchmark: >95% precision, >90% recall

Option 2: **Consensus Speed**
- Latency to reach consensus (target: <10 seconds)
- Throughput (transactions/second)

Option 3: **Economic Fairness**
- Gini coefficient for token distribution (target: <0.3)
- Honest nodes earn more than malicious nodes

**Discussion:**
- Which metric is most important?
- How to compare against existing BGP security solutions (ROV, ASPA, BGPsec)?
- Should we prioritize security vs. performance vs. fairness?

---

## 4. Experimental Protocol

### BGPy Data Generation

BGP-Sentry uses **BGPy** (BGP Python simulator) to generate BGP announcements offline before experiments.

**Why BGPy?**
- **Controllable attacks:** Inject specific attack types at precise times
- **Reproducible:** Same BGP data for multiple experiment runs
- **Scalable:** Generate months of BGP data in minutes
- **Realistic topology:** Simulates AS relationships and routing policies

**BGPy → BGP-Sentry Pipeline:**

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: BGPy Simulation (Offline)                      │
├─────────────────────────────────────────────────────────┤
│ • Define AS topology (customer-provider, peer-peer)    │
│ • Configure routing policies (BGP best path selection)  │
│ • Inject attacks (prefix hijack, route leak, etc.)     │
│ • Run simulation (BGP convergence)                      │
│ • Export announcements to log files                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼ (Offline extraction)
┌─────────────────────────────────────────────────────────┐
│ Step 2: BGP Log Files                                  │
├─────────────────────────────────────────────────────────┤
│ • bgp_feed/mininet_logs/*.log                          │
│ • Format: Timestamp, Prefix, AS Path, Announcement     │
│ • Contains both legitimate and attack announcements     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼ (Read by BGP-Sentry)
┌─────────────────────────────────────────────────────────┐
│ Step 3: BGP-Sentry Processing (Online)                │
├─────────────────────────────────────────────────────────┤
│ • Each RPKI node reads BGP logs                        │
│ • Nodes observe announcements and add to knowledge base│
│ • Consensus voting on observed announcements           │
│ • Attack detection and blockchain recording            │
└─────────────────────────────────────────────────────────┘
```

**Generating BGP Data with BGPy:**

```bash
# Example: Generate BGP data for experiment
cd bgp_feed
python3 bgpy_simulator.py \
    --topology caida_as_relationships.txt \
    --duration 3600 \
    --attack-type prefix_hijack \
    --attack-start 1800 \
    --attack-duration 600 \
    --output mininet_logs/experiment_001.log

# This produces:
# - 1 hour of BGP announcements
# - Prefix hijack attack starts at 30 minutes
# - Attack lasts for 10 minutes
# - Output saved to mininet_logs/experiment_001.log
```

**Attack Scenarios You Can Simulate:**

1. **Prefix Hijack:** Attacker announces victim's exact prefix
2. **Sub-prefix Hijack:** Attacker announces more specific prefix (e.g., /25 instead of /24)
3. **Route Leak:** AS announces routes it shouldn't (violates valley-free routing)
4. **BGP Hijacking with Valid ROA:** Attacker compromises legitimate AS with valid ROA
5. **Slow Poisoning:** Gradual AS path manipulation over time

**Key Advantage:** Since BGPy data is generated offline, you can:
- Run multiple BGP-Sentry experiments with identical BGP data (reproducibility)
- Compare different consensus thresholds with same attack scenarios
- Isolate BGP-Sentry behavior from BGPy simulation variability

**Discussion with Collaborators:**
- What BGPy attack scenarios should we test?
- How to validate that BGPy generates realistic BGP behavior?
- Should we compare BGPy-generated data with real RouteViews/RIPE data?

---

### Experiment Design

**Objective:** Evaluate BGP-Sentry's ability to detect BGP attacks through distributed consensus.

**Independent Variables:**
- Number of nodes (9, 15, 21)
- Consensus threshold (3/9, 5/9, 6/9)
- Attack injection rate (0%, 5%, 10%, 20%)
- Sampling window (30 min, 1 hour, 2 hours)

**Dependent Variables:**
- Attack detection rate (precision, recall)
- Consensus latency (time to commit)
- Blockchain size (MB)
- Token distribution (Gini coefficient)
- System throughput (transactions/hour)

**Control Variables:**
- BGP data source (same RouteViews logs for all runs)
- Python version (3.10)
- Hardware (same server)
- Network configuration (localhost P2P)

---

### Running an Experiment

**Step 1: Preparation**
```bash
# Activate virtual environment
source venv310/bin/activate

# Generate BGP announcements using BGPy (if needed)
# This step creates the BGP logs that BGP-Sentry will process
# Note: BGPy runs separately and exports announcements offline
cd bgp_feed
python3 bgpy_data_generator.py --config attack_scenario_1.json
cd ..

# Clean previous experiment data
rm -rf nodes/rpki_nodes/as*/blockchain_node/blockchain_data/chain/*
rm -rf nodes/rpki_nodes/as*/blockchain_node/blockchain_data/state/*
rm -rf experiment_results/*

# Verify prerequisites
cd tests
python3 pre_simulation_check.py
cd ..
```

**Step 2: Configure Experiment**

Edit `simulation_helpers/shared_data/experiment_config.json`:
```json
{
  "experiment_metadata": {
    "name": "BGP-Sentry Baseline Run",
    "description": "9 nodes, 3/9 threshold, 5% attack rate, 1-hour sampling"
  },
  "simulation_parameters": {
    "time_scale": 1.0,
    "max_duration": 3600,
    "expected_nodes": 9,
    "processing_interval": 5.0
  },
  "monitoring": {
    "health_check_interval": 10,
    "enable_dashboard": true,
    "alert_on_failures": true
  }
}
```

**Step 3: Run Experiment**
```bash
# Start experiment
python3 main_experiment.py

# In another terminal: Monitor live
python3 bgp_dashboard.py
```

**Step 4: Wait for Completion**

Experiment runs for configured duration (default 1 hour), then:
- Nodes automatically shutdown
- Blockchains saved to disk
- Results exported to `results/bgp_sentry_results_TIMESTAMP.json`

**Step 5: Backup Results**
```bash
# Create experiment archive
EXPERIMENT_ID=$(date +%Y%m%d_%H%M%S)
mkdir -p experiment_results/${EXPERIMENT_ID}

# Copy all node data
cp -r nodes/rpki_nodes/as*/blockchain_node/blockchain_data experiment_results/${EXPERIMENT_ID}/
cp results/bgp_sentry_results_*.json experiment_results/${EXPERIMENT_ID}/
cp main_experiment.log experiment_results/${EXPERIMENT_ID}/

# Archive
tar -czf experiment_results/${EXPERIMENT_ID}.tar.gz experiment_results/${EXPERIMENT_ID}/
```

---

### Experiment Checklist

Before starting an experiment:

- [ ] Virtual environment activated (Python 3.10)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] **BGP announcements generated using BGPy** (offline extraction complete)
- [ ] BGP data logs present in `bgp_feed/mininet_logs/` or configured location
- [ ] Ports 8001-8017 available (check with `netstat -tuln | grep 800`)
- [ ] Sufficient disk space (>10 GB free)
- [ ] Previous experiment data cleaned
- [ ] Experiment config file updated
- [ ] Monitoring dashboard ready

---

## 5. Post-Hoc Analysis Framework

After running an experiment, perform comprehensive analysis across 10 dimensions.

### Analysis Overview

```
experiment_results/20251202_143000/
├── as01/blockchain_data/
│   ├── chain/blockchain.json          ← Transaction data
│   ├── state/bgpcoin_ledger.json      ← Token balances
│   ├── state/knowledge_base.json      ← Observations
│   └── state/attack_detections.json   ← Detected attacks
├── as03/blockchain_data/
├── ...
├── bgp_sentry_results_20251202_143000.json  ← Summary
└── main_experiment.log                       ← System logs
```

---

### Analysis 1: Consensus Performance

**Goal:** Measure consensus success rate and latency.

**Metrics:**
```python
# Consensus success rate
total_transactions = len(blockchain)
confirmed = count(consensus_status == "CONFIRMED")
insufficient = count(consensus_status == "INSUFFICIENT_CONSENSUS")
single_witness = count(consensus_status == "SINGLE_WITNESS")

success_rate = confirmed / total_transactions
```

**Key Questions:**
- What % of transactions reached full consensus (3+ votes)?
- What % timed out with insufficient consensus?
- Did consensus rate improve over time?

**Visualization:**
- Line chart: Consensus rate over time
- Pie chart: Transaction status breakdown
- Histogram: Vote count distribution

**Expected Results:**
- Baseline: >80% confirmed, <15% insufficient, <5% single witness
- If success rate <80%: Network issues or misconfigured threshold

---

### Analysis 2: Attack Detection Accuracy

**Goal:** Evaluate precision and recall for attack detection.

**Metrics:**
```python
# Compare detected vs. injected attacks
ground_truth_attacks = load_injected_attacks()  # From attack logs
detected_attacks = load_detected_attacks()      # From blockchain

true_positives = detected_attacks ∩ ground_truth_attacks
false_positives = detected_attacks - ground_truth_attacks
false_negatives = ground_truth_attacks - detected_attacks

precision = TP / (TP + FP)
recall = TP / (TP + FN)
f1_score = 2 × (precision × recall) / (precision + recall)
```

**Key Questions:**
- What's the detection rate per attack type?
  - Prefix hijack: Expected >90%
  - Sub-prefix hijack: Expected >85%
  - Route leak: Expected >75%
- Are there false alarms (legitimate announcements flagged)?
- Which attacks are hardest to detect?

**Visualization:**
- Confusion matrix
- Precision-recall curve
- Timeline: Attack injection vs. detection time

**Expected Results:**
- Baseline: Precision >90%, Recall >85%, F1 >87%
- If precision <90%: Too sensitive (tune detection thresholds)
- If recall <85%: Missing attacks (improve validation logic)

---

### Analysis 3: Token Economics

**Goal:** Analyze BGPCOIN distribution and fairness.

**Metrics:**
```python
# Token distribution
balances = {as_num: ledger.get_balance(as_num) for as_num in [1,3,5,7,9,11,13,15,17]}
total_supply = sum(balances.values()) + treasury_balance + burned_amount

# Inequality measure (0 = perfect equality, 1 = perfect inequality)
gini_coefficient = calculate_gini(balances.values())

# Economic activity
for as_num in nodes:
    total_earned = sum(rewards for this AS)
    total_spent = sum(spending for this AS)
    net_gain = total_earned - total_spent
```

**Key Questions:**
- Is wealth concentrated in few nodes (Gini > 0.4)?
- Do honest nodes earn more than malicious nodes?
- Is the treasury sustainable (not depleting too fast)?
- Does the 50% burn rate create deflationary pressure?

**Visualization:**
- Line chart: Token balance over time per node
- Pie chart: Token distribution at end
- Bar chart: Total earned vs. spent per node

**Expected Results:**
- Baseline: Gini <0.3 (fairly distributed)
- Treasury depletion rate: <10% per month
- Honest nodes earn 2-5× more than malicious nodes

---

### Analysis 4: Blockchain Growth

**Goal:** Measure blockchain size and sampling effectiveness.

**Metrics:**
```python
# Without sampling (theoretical)
total_bgp_announcements = count(all BGP observations in logs)

# With sampling (actual)
blockchain_size_entries = len(blockchain)
blockchain_size_bytes = os.path.getsize("blockchain.json")

# Reduction effectiveness
reduction_rate = 1 - (blockchain_size_entries / total_bgp_announcements)
growth_rate_mb_per_hour = blockchain_size_bytes / experiment_duration_hours

# Extrapolation
projected_1_year = growth_rate_mb_per_hour × 24 × 365
```

**Key Questions:**
- Did 1-hour sampling reduce blockchain size by >90%?
- What's the growth rate (MB/hour)?
- Are there noisy prefixes creating bloat?
- At current rate, how long until 1GB? 10GB?

**Visualization:**
- Line chart: Blockchain size over time
- Histogram: Announcements per prefix (identify noisy prefixes)
- Comparison bar: With vs. without sampling

**Expected Results:**
- Baseline: >90% size reduction with sampling
- Growth rate: ~10 MB/day per node
- 1-year projection: <5 GB per node

---

### Analysis 5: Network Performance

**Goal:** Measure consensus latency and throughput.

**Metrics:**
```python
# Consensus latency
for tx in blockchain:
    created_at = tx.get("created_at")     # When entered pending
    committed_at = tx.get("timestamp")     # When written to blockchain

    if created_at and committed_at:
        latency = (committed_at - created_at).total_seconds()

avg_latency = mean(all_latencies)
p50_latency = percentile(all_latencies, 50)
p95_latency = percentile(all_latencies, 95)
p99_latency = percentile(all_latencies, 99)

# Throughput
throughput = blockchain_size_entries / experiment_duration_seconds
```

**Key Questions:**
- How long to reach consensus (average)?
- Are attack transactions slower (180s timeout)?
- Did any transactions take unusually long? Why?
- Is there a throughput bottleneck?

**Visualization:**
- CDF: Cumulative distribution of latency
- Box plot: Latency by transaction type (regular vs. attack)
- Line chart: Throughput over time

**Expected Results:**
- Baseline: Avg latency <30s, P95 <50s, P99 <60s
- Throughput: >200 transactions/hour
- Attack latency: 2-3× longer than regular

---

### Analysis 6: Node Behavior & Reputation

**Goal:** Analyze voting accuracy and participation.

**Metrics:**
```python
for as_number in nodes:
    # Voting statistics
    total_votes = count(votes cast by this AS)
    correct_votes = count(voted approve for confirmed txs)
    false_approvals = count(voted approve for rejected txs)
    false_rejections = count(voted reject for confirmed txs)

    # Accuracy metrics
    accuracy = correct_votes / total_votes
    precision = correct_votes / (correct_votes + false_approvals)
    participation_rate = total_votes / total_vote_requests

    # Reputation score
    reputation = accuracy × participation_rate × quality_multiplier
```

**Key Questions:**
- Which nodes are most accurate?
- Which nodes have low participation (lazy)?
- Are there malicious nodes (consistently wrong)?
- Do multipliers correlate with behavior?

**Visualization:**
- Heatmap: Vote agreement matrix (which nodes agree?)
- Line chart: Accuracy over time per node
- Scatter plot: Accuracy vs. participation vs. earnings

**Expected Results:**
- Baseline: Avg accuracy >85%, participation >90%
- Honest nodes: Accuracy >90%
- Malicious nodes: Accuracy <50%

---

### Analysis 7: Timeout & Sampling Features

**Goal:** Validate timeout mechanism and sampling effectiveness.

**Metrics:**
```python
# Timeout events
timed_out_txs = [tx for tx in blockchain if tx.get("timeout_commit") == True]
timeout_rate = len(timed_out_txs) / len(blockchain)

# Breakdown by status
confirmed_timeouts = count(status == "CONFIRMED")        # 3+ votes
insufficient_timeouts = count(status == "INSUFFICIENT")   # 1-2 votes
single_witness_timeouts = count(status == "SINGLE_WITNESS")  # 0 votes

# Sampling effectiveness
cache_hits = count(announcements skipped due to sampling)
cache_misses = count(announcements recorded)
hit_rate = cache_hits / (cache_hits + cache_misses)

# Verify no duplicates within 1 hour
for tx in blockchain:
    duplicates = find_transactions_within_1hour(tx["ip_prefix"], tx["sender_asn"])
```

**Key Questions:**
- What % of transactions timed out?
- Were timeouts due to network issues or disagreement?
- Did sampling prevent duplicates?
- What's the cache hit rate?

**Visualization:**
- Bar chart: Timeout breakdown by status
- Line chart: Cache hit rate over time
- Heatmap: Duplicate detection (should be empty)

**Expected Results:**
- Baseline: Timeout rate <10%
- Cache hit rate: 85-95% (indicates sampling working)
- Zero duplicates within 1-hour window

---

### Analysis 8: Attack Consensus System

**Goal:** Evaluate attack detection consensus.

**Metrics:**
```python
# Attack proposal statistics
total_attack_proposals = count(attack proposals)
approved_attacks = count(attack consensus reached)
rejected_attacks = count(attack consensus rejected)

attack_consensus_rate = approved_attacks / total_attack_proposals

# Agreement analysis
for attack_proposal in attack_proposals:
    votes_approve = count(nodes voted "attack")
    votes_reject = count(nodes voted "legitimate")
    split_ratio = votes_approve / (votes_approve + votes_reject)
```

**Key Questions:**
- Do nodes agree on what's an attack?
- Are there contentious proposals (50/50 split)?
- False alarms: Legitimate announcements flagged?

**Visualization:**
- Histogram: Vote split distribution
- Confusion matrix: Detected vs. actual attacks

**Expected Results:**
- Baseline: Attack consensus rate >80%
- Clear splits: >75% agreement on most proposals

---

### Analysis 9: Blockchain Consistency

**Goal:** Check if all 9 nodes have identical blockchains.

**Metrics:**
```python
# Load blockchains from all nodes
blockchains = {
    as_num: load_blockchain(f"as{as_num:02d}/blockchain_data/chain/blockchain.json")
    for as_num in [1, 3, 5, 7, 9, 11, 13, 15, 17]
}

# Compare block counts
block_counts = {as_num: len(chain) for as_num, chain in blockchains.items()}
max_blocks = max(block_counts.values())
min_blocks = min(block_counts.values())
block_divergence = max_blocks - min_blocks

# Compare transaction IDs at each height
for height in range(min_blocks):
    tx_ids = {as_num: chain[height]["transaction_id"] for as_num, chain in blockchains.items()}
    if len(set(tx_ids.values())) > 1:
        # Fork detected!
        fork_events.append(height)
```

**Key Questions:**
- Do all nodes have the same blockchain?
- Are there forks (divergent transaction histories)?
- Did any node miss transactions?

**Visualization:**
- Bar chart: Block count per node
- Timeline: Fork events (if any)
- Diff view: Mismatched transactions

**Expected Results:**
- Baseline: Zero forks, all nodes identical
- Block count variance: <1%
- If forks detected: Investigate consensus bug

---

### Analysis 10: System Health & Reliability

**Goal:** Measure uptime, errors, and system stability.

**Metrics:**
```python
# Uptime
for node in nodes:
    total_runtime = experiment_end - experiment_start
    downtime = sum(periods where node unresponsive)
    uptime_rate = (total_runtime - downtime) / total_runtime

# Error analysis (parse logs)
errors = {
    "network_errors": count("Failed to send vote"),
    "timeout_errors": count("Transaction timed out"),
    "validation_errors": count("Validation error"),
    "consensus_failures": count("CONSENSUS FAILED")
}

# Resource usage
peak_memory = max(memory usage over time)
avg_cpu = mean(CPU usage over time)
disk_io = total_disk_writes
```

**Key Questions:**
- What was the uptime rate (target >99%)?
- What caused downtime (crashes, network, resource exhaustion)?
- What types of errors occurred most?
- Were there resource bottlenecks (CPU, memory, disk)?

**Visualization:**
- Line chart: Uptime per node over time
- Bar chart: Error type frequency
- Line chart: Resource usage over time

**Expected Results:**
- Baseline: Uptime >99%, <10 errors per hour
- If uptime <95%: Investigate crashes/deadlocks
- If errors >100/hour: Debug and fix

---

### Analysis Script Template

Create `analysis/post_experiment_analysis.py`:

```python
#!/usr/bin/env python3
"""
BGP-Sentry Post-Experiment Analysis
Comprehensive analysis across 10 dimensions
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import numpy as np

class BGPSentryAnalyzer:
    """Analyze BGP-Sentry experiment results"""

    def __init__(self, experiment_dir: str):
        self.experiment_dir = Path(experiment_dir)
        self.blockchains = {}
        self.ledgers = {}
        self.logs = {}
        self.load_all_data()

    def load_all_data(self):
        """Load blockchains, ledgers, logs from all nodes"""
        print("Loading experiment data...")

        for as_num in [1, 3, 5, 7, 9, 11, 13, 15, 17]:
            as_dir = self.experiment_dir / f"as{as_num:02d}" / "blockchain_data"

            # Load blockchain
            blockchain_file = as_dir / "chain" / "blockchain.json"
            if blockchain_file.exists():
                with open(blockchain_file, 'r') as f:
                    self.blockchains[as_num] = json.load(f)

            # Load ledger
            ledger_file = as_dir / "state" / "bgpcoin_ledger.json"
            if ledger_file.exists():
                with open(ledger_file, 'r') as f:
                    self.ledgers[as_num] = json.load(f)

        print(f"Loaded data from {len(self.blockchains)} nodes")

    def analyze_consensus_performance(self):
        """Analysis 1: Consensus success rate"""
        print("\n=== ANALYSIS 1: Consensus Performance ===")

        all_transactions = []
        for as_num, blockchain in self.blockchains.items():
            all_transactions.extend(blockchain.get("transactions", []))

        total = len(all_transactions)
        confirmed = sum(1 for tx in all_transactions if tx.get("consensus_status") == "CONFIRMED")
        insufficient = sum(1 for tx in all_transactions if tx.get("consensus_status") == "INSUFFICIENT_CONSENSUS")
        single = sum(1 for tx in all_transactions if tx.get("consensus_status") == "SINGLE_WITNESS")

        print(f"Total Transactions: {total}")
        print(f"Confirmed: {confirmed} ({confirmed/total*100:.1f}%)")
        print(f"Insufficient: {insufficient} ({insufficient/total*100:.1f}%)")
        print(f"Single Witness: {single} ({single/total*100:.1f}%)")

        # TODO: Add visualization

    def analyze_attack_detection(self):
        """Analysis 2: Attack detection accuracy"""
        print("\n=== ANALYSIS 2: Attack Detection Accuracy ===")
        # TODO: Implement precision/recall calculation
        pass

    def analyze_token_economics(self):
        """Analysis 3: BGPCOIN distribution"""
        print("\n=== ANALYSIS 3: Token Economics ===")

        balances = {}
        for as_num, ledger in self.ledgers.items():
            balance = ledger.get("balances", {}).get(str(as_num), 0)
            balances[as_num] = balance

        print("Token Balances:")
        for as_num, balance in sorted(balances.items()):
            print(f"  AS{as_num:02d}: {balance:.2f} BGPCOIN")

        # Calculate Gini coefficient
        gini = self.calculate_gini(list(balances.values()))
        print(f"Gini Coefficient: {gini:.3f} (0=equal, 1=unequal)")

    def calculate_gini(self, values: List[float]) -> float:
        """Calculate Gini coefficient"""
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = np.cumsum(sorted_values)
        return (2 * sum((i+1) * val for i, val in enumerate(sorted_values))) / (n * sum(sorted_values)) - (n + 1) / n

    def analyze_blockchain_growth(self):
        """Analysis 4: Blockchain size and sampling"""
        print("\n=== ANALYSIS 4: Blockchain Growth ===")
        # TODO: Implement blockchain size analysis
        pass

    def analyze_network_performance(self):
        """Analysis 5: Consensus latency and throughput"""
        print("\n=== ANALYSIS 5: Network Performance ===")
        # TODO: Implement latency analysis
        pass

    def analyze_node_behavior(self):
        """Analysis 6: Voting accuracy and reputation"""
        print("\n=== ANALYSIS 6: Node Behavior ===")
        # TODO: Implement voting accuracy analysis
        pass

    def analyze_timeout_sampling(self):
        """Analysis 7: Timeout and sampling effectiveness"""
        print("\n=== ANALYSIS 7: Timeout & Sampling ===")
        # TODO: Implement timeout analysis
        pass

    def analyze_attack_consensus(self):
        """Analysis 8: Attack consensus system"""
        print("\n=== ANALYSIS 8: Attack Consensus ===")
        # TODO: Implement attack consensus analysis
        pass

    def analyze_consistency(self):
        """Analysis 9: Blockchain consistency across nodes"""
        print("\n=== ANALYSIS 9: Blockchain Consistency ===")

        block_counts = {as_num: len(chain.get("transactions", []))
                       for as_num, chain in self.blockchains.items()}

        print("Block Counts:")
        for as_num, count in sorted(block_counts.items()):
            print(f"  AS{as_num:02d}: {count} blocks")

        max_count = max(block_counts.values())
        min_count = min(block_counts.values())
        divergence = max_count - min_count

        print(f"Divergence: {divergence} blocks")
        if divergence == 0:
            print("✅ All nodes have identical blockchains")
        else:
            print("⚠️  Fork detected! Investigating...")

    def analyze_system_health(self):
        """Analysis 10: Uptime and errors"""
        print("\n=== ANALYSIS 10: System Health ===")
        # TODO: Implement health analysis from logs
        pass

    def generate_full_report(self, output_file: str):
        """Generate comprehensive analysis report"""
        print("\n" + "="*60)
        print("BGP-SENTRY POST-EXPERIMENT ANALYSIS REPORT")
        print("="*60)

        self.analyze_consensus_performance()
        self.analyze_attack_detection()
        self.analyze_token_economics()
        self.analyze_blockchain_growth()
        self.analyze_network_performance()
        self.analyze_node_behavior()
        self.analyze_timeout_sampling()
        self.analyze_attack_consensus()
        self.analyze_consistency()
        self.analyze_system_health()

        print("\n" + "="*60)
        print("Analysis Complete!")
        print(f"Full report saved to: {output_file}")
        print("="*60)

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 post_experiment_analysis.py <experiment_dir>")
        print("Example: python3 post_experiment_analysis.py experiment_results/20251202_143000/")
        sys.exit(1)

    experiment_dir = sys.argv[1]
    analyzer = BGPSentryAnalyzer(experiment_dir)
    analyzer.generate_full_report(f"{experiment_dir}/ANALYSIS_REPORT.txt")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
python3 analysis/post_experiment_analysis.py experiment_results/20251202_143000/
```

---

## 6. Getting Started

### For New Collaborators

**Step 1: Read Core Documentation**
- `README.md` - Quick start guide
- `docs/BGPCOIN_COMPLETE_SYSTEM.md` - Token economics
- `docs/IMPLEMENTATION_SUMMARY_TIMEOUT_SAMPLING.md` - Recent features
- This guide (COLLABORATOR_GUIDE.md)

**Step 2: Setup Development Environment**
```bash
# Clone repository
git clone <repo-url>
cd BGP-Sentry

# Create virtual environment
python3.10 -m venv venv310
source venv310/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
cd tests
python3 test_p2p_timeout_and_sampling.py
```

**Step 3: Run a Small Experiment**
```bash
# Modify config for quick test (5 minutes)
# Edit simulation_helpers/shared_data/experiment_config.json
# Set "max_duration": 300

# Run experiment
python3 main_experiment.py

# Analyze results
python3 analysis/post_experiment_analysis.py experiment_results/latest/
```

**Step 4: Explore the Codebase**

Key files to understand:
1. `main_experiment.py` - Entry point
2. `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/p2p_transaction_pool.py` - Consensus engine
3. `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/bgpcoin_ledger.py` - Token system
4. `nodes/rpki_nodes/bgp_attack_detection/attack_detector.py` - Attack detection

**Step 5: Schedule Discussion Meeting**

Topics to cover:
- Research objectives and hypotheses
- Design decision rationale
- Experiment plan and evaluation metrics
- Division of labor (who works on what?)
- Paper authorship and acknowledgments

---

## 7. Open Research Questions

These are **unresolved questions** that require research and discussion.

### Category: Security

1. **Byzantine Resilience:** Can we tolerate >2 malicious nodes with adaptive thresholds?
2. **Attack Detection:** What's the theoretical limit on detection accuracy given BGP's lack of cryptographic authentication?
3. **Collusion Detection:** Can we identify colluding nodes through voting pattern analysis?

### Category: Performance

4. **Scalability:** Can the system scale to 100+ nodes without re-architecture?
5. **Latency:** Can we achieve <5 second consensus without sacrificing security?
6. **Throughput:** What's the maximum BGP announcements/second the system can handle?

### Category: Economics

7. **Token Value:** Would external value (tradable token) improve or harm behavior?
8. **Incentive Alignment:** Are current rewards sufficient to prevent lazy nodes?
9. **Long-term Sustainability:** Will the system still function after 10 years?

### Category: Validation

10. **Real-world Deployment:** How would this perform on live BGP feed vs. pre-recorded?
11. **Comparison:** How does BGP-Sentry compare to BGPsec, ASPA, ROV?
12. **Attack Sophistication:** Can it detect advanced attacks (slow poisoning, sophisticated hijacks)?

---

## Next Steps

### For Research Collaboration

1. **Schedule kickoff meeting** to discuss:
   - Research goals and success criteria
   - Experiment design and parameters
   - Analysis methodology
   - Paper outline and authorship

2. **Divide responsibilities:**
   - Experiment execution
   - Data analysis
   - Visualization and figures
   - Writing (intro, methods, results, discussion)

3. **Set milestones:**
   - Week 1: Run baseline experiments
   - Week 2: Analyze results, identify issues
   - Week 3: Run additional experiments with variations
   - Week 4: Complete analysis and draft paper

### For Code Contributors

1. **Identify improvement areas:**
   - Performance optimization
   - Additional attack detection algorithms
   - Enhanced visualization dashboard
   - Machine learning integration

2. **Create feature branches:**
   - `feature/adaptive-timeout`
   - `feature/ml-attack-detection`
   - `feature/dynamic-sampling`

3. **Submit pull requests** with:
   - Clear description of changes
   - Unit tests
   - Performance benchmarks
   - Documentation updates

---

## Contact & Support

**Project Lead:** [Your Name]
**Email:** [Your Email]
**Repository:** [GitHub URL]
**Documentation:** See `docs/` directory for detailed technical docs

**Questions?** Open an issue on GitHub or schedule a meeting.

---

**BGP-Sentry: Securing Internet Routing Through Distributed Consensus**

*Last Updated: December 2, 2025*
