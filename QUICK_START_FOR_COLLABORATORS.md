# BGP-Sentry: Quick Start for Collaborators

**Welcome!** This is a condensed guide to get you started quickly. For comprehensive details, see `COLLABORATOR_GUIDE.md`.

---

## What is BGP-Sentry?

A **distributed blockchain system** that detects BGP attacks through consensus voting among RPKI-enabled nodes.

**Key Innovation:** Knowledge-based voting - nodes only vote on BGP announcements they've personally observed.

---

## Architecture in 30 Seconds

```
9 RPKI Nodes (AS01, AS03, ..., AS17)
    ↓
Each observes BGP announcements
    ↓
Broadcast transaction to peers
    ↓
Peers vote based on their observations
    ↓
3/9 consensus → Write to blockchain
    ↓
Earn BGPCOIN tokens for participation
```

---

## Quick Setup (5 minutes)

```bash
# 1. Clone and setup
git clone <repo-url>
cd BGP-Sentry
python3.10 -m venv venv310
source venv310/bin/activate
pip install -r requirements.txt

# 2. Generate BGP data (using BGPy)
cd bgp_feed
python3 bgpy_simulator.py --config attack_scenario_1.json
cd ..

# 3. Run experiment
python3 main_experiment.py

# 4. Analyze results
python3 analysis/post_experiment_analysis.py experiment_results/latest/
```

---

## Key Files to Understand

| File | What it does |
|------|-------------|
| `main_experiment.py` | Orchestrates entire experiment |
| `p2p_transaction_pool.py` | Consensus engine, voting logic |
| `bgpcoin_ledger.py` | Token rewards and economics |
| `attack_detector.py` | RPKI/IRR validation, attack detection |

**Location:** Most core logic in `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/`

---

## Important Design Decisions to Discuss

### 1. Consensus Threshold: 3/9 (33%)
- **Why?** BGP is globally observed but locally validated
- **Risk?** 4 colluding nodes can break system
- **Alternative?** Increase to 6/9 (traditional BFT 2/3)?

### 2. BGPCOIN Token Economics
- 10M total supply, 50% burn / 50% recycle
- **Risk?** Treasury might deplete or tokens become too concentrated
- **Alternative?** Proof-of-Stake with slashing?

### 3. Transaction Timeouts
- Regular: 60s, Attacks: 180s
- **Risk?** Legitimate votes delayed beyond timeout
- **Alternative?** Adaptive timeouts based on network load?

### 4. Sampling (1-hour window)
- Only record each (prefix, AS) pair once per hour
- **Risk?** Miss legitimate changes within 1 hour
- **Alternative?** Adaptive sampling per prefix stability?

---

## Data Pipeline (Important!)

```
BGPy Simulator (Offline)
    → Generates BGP announcements with attacks
    → Exports to logs (bgp_feed/mininet_logs/)
    ↓
BGP-Sentry (Online)
    → Reads pre-recorded logs
    → Processes through consensus
    → Writes to blockchain
```

**Key Advantage:** Reproducible experiments (same BGP data for multiple runs)

---

## Running Your First Experiment

**Scenario:** Detect prefix hijack attack

```bash
# 1. Generate BGP data with attack
cd bgp_feed
python3 bgpy_simulator.py \
    --duration 3600 \
    --attack-type prefix_hijack \
    --attack-start 1800 \
    --output mininet_logs/hijack_test.log

# 2. Configure experiment (edit config file)
nano simulation_helpers/shared_data/experiment_config.json
# Set max_duration: 3600 (1 hour)

# 3. Run BGP-Sentry
cd ..
python3 main_experiment.py

# 4. Monitor live (separate terminal)
python3 bgp_dashboard.py

# 5. Wait for completion, then analyze
python3 analysis/post_experiment_analysis.py experiment_results/latest/
```

**Expected Results:**
- ~80% consensus success rate
- >90% attack detection precision
- ~10 MB blockchain size per node
- Avg consensus latency <30 seconds

---

## Post-Hoc Analysis (10 Key Metrics)

After experiment completes, analyze:

1. **Consensus Performance** - Success rate, latency, throughput
2. **Attack Detection** - Precision, recall, F1-score
3. **Token Economics** - Distribution fairness (Gini coefficient)
4. **Blockchain Growth** - Size, sampling effectiveness
5. **Network Performance** - Consensus latency, bottlenecks
6. **Node Behavior** - Voting accuracy, participation rate
7. **Timeout/Sampling** - Effectiveness of recent features
8. **Attack Consensus** - Agreement on what's an attack
9. **Consistency** - Do all nodes have identical blockchains?
10. **System Health** - Uptime, errors, resource usage

**Script:** `analysis/post_experiment_analysis.py` (see COLLABORATOR_GUIDE.md for template)

---

## Critical Questions for Discussion

**Before we start collaborating, let's discuss:**

### Security
- How to handle 4+ colluding nodes?
- What attacks can we NOT detect?
- Timeout security implications?

### Performance
- Can this scale to 100+ nodes?
- What's the throughput limit?
- Blockchain growth sustainable for 10 years?

### Economics
- Is token distribution fair ("rich get richer")?
- Will treasury last? (rewards vs. spending)
- Should we use external tradable tokens?

### Validation
- How realistic is BGPy compared to real Internet?
- Should we validate against RouteViews/RIPE data?
- How to compare against BGPsec, ASPA, ROV?

---

## Research Questions (Pick One?)

These are **open research problems** we could investigate:

1. **Adaptive Thresholds** - Dynamic consensus based on announcement type?
2. **Collusion Detection** - Identify colluding nodes through voting patterns?
3. **Machine Learning** - Use ML for anomaly detection instead of RPKI?
4. **Scalability** - Re-architect for 100+ nodes (gossip protocol?)
5. **Economic Modeling** - Game theory analysis of token incentives?
6. **Real-world Validation** - Deploy on live BGP feed?
7. **Comparison Study** - Benchmark against existing BGP security solutions?

**Which one interests you most?**

---

## Collaboration Workflow

### Week 1: Baseline Experiments
- Run 3 experiments with different attack scenarios
- Analyze results (10 metrics)
- Identify issues or surprising findings

### Week 2: Deep Dive
- Investigate interesting findings
- Run additional experiments with variations
- Start drafting paper outline

### Week 3: Analysis & Visualization
- Complete all 10 analysis dimensions
- Create figures and tables for paper
- Write methods and results sections

### Week 4: Paper Writing
- Introduction and related work
- Discussion and future work
- Revisions and submission

---

## Next Steps

1. **Read full guide:** `COLLABORATOR_GUIDE.md` (20+ pages, comprehensive)
2. **Schedule meeting:** Discuss research goals and division of labor
3. **Run test experiment:** Verify your environment works
4. **Pick research focus:** Which open question excites you?

---

## Documentation Map

| File | Purpose |
|------|---------|
| `README.md` | Basic installation and quick start |
| `QUICK_START_FOR_COLLABORATORS.md` | **This file** - Fast onboarding |
| `COLLABORATOR_GUIDE.md` | Comprehensive guide (design, experiments, analysis) |
| `docs/BGPCOIN_COMPLETE_SYSTEM.md` | Token economics deep dive |
| `docs/IMPLEMENTATION_SUMMARY_TIMEOUT_SAMPLING.md` | Recent feature implementation |
| `HOW_TO_RUN_COMPLETE_TEST.md` | Detailed test instructions |
| `RESULT_ANALYSIS_GUIDE.md` | Existing analysis tools |

---

## Contact

**Questions?**
- Open GitHub issue
- Schedule meeting
- See full guide for detailed explanations

**Ready to start?** Let's schedule a kickoff meeting to discuss:
- Research objectives and hypotheses
- Experiment design and parameters
- Division of responsibilities
- Paper outline and authorship

---

**BGP-Sentry: Securing Internet Routing Through Distributed Consensus**

*Let's detect BGP attacks together!*
