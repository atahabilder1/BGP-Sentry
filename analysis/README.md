# Post-Hoc Analysis Tools

This directory contains post-hoc analysis tools for BGP-Sentry experiments, focusing on targeted attacks, unconfirmed transactions, and chronological misbehavior detection.

## Overview

After running a BGP-Sentry experiment, these tools help you analyze:

1. **Targeted Attacks** - SINGLE_WITNESS transactions (0 votes)
2. **Unconfirmed Transactions** - INSUFFICIENT_CONSENSUS transactions (1-2 votes)
3. **Chronological Misbehavior** - Timing patterns, repeated attempts, escalations
4. **Cross-Node Correlation** - Blockchain consistency validation
5. **Upgrade Candidates** - Transactions deserving manual review

---

## Tools

### 1. Targeted Attack Analyzer

**File:** `targeted_attack_analyzer.py`

**Purpose:** Deep analysis of low-consensus and zero-consensus transactions to identify targeted attacks and potential system issues.

**Usage:**
```bash
cd analysis
python3 targeted_attack_analyzer.py <experiment_results_dir>
```

**Example:**
```bash
python3 targeted_attack_analyzer.py ../experiment_results/run_2025_12_02_14_30/
```

**What it analyzes:**

#### A. SINGLE_WITNESS Transactions (0 votes)
- **What:** Transactions that only the observer node recorded (no other node agreed)
- **Why it matters:** Could indicate targeted attacks, network partition, or node isolation
- **Metrics:**
  - Total count and percentage
  - Breakdown by attack status (marked vs unmarked)
  - Distribution by observer node (which nodes see unique events?)
  - Distribution by IP prefix (which prefixes are controversial?)
  - Temporal distribution (when do single-witness events occur?)

**RED FLAG:** Legitimate announcements with 0 votes suggest:
- Network partition (node isolated from peers)
- Timing issues (votes arrived after timeout)
- Node malfunction (observers didn't broadcast)
- Truly unique observation (only one node witnessed it)

#### B. INSUFFICIENT_CONSENSUS Transactions (1-2 votes)
- **What:** Transactions with partial agreement but below consensus threshold (3/9)
- **Why it matters:** These are "close calls" - one more vote would confirm them
- **Metrics:**
  - Total count by vote count (1 vs 2 votes)
  - Breakdown by attack status
  - Average votes for attacks vs legitimate
  - Upgrade candidates (2-vote transactions close to consensus)

**UPGRADE CANDIDATES:** Transactions with 2 votes are ONE VOTE AWAY from full consensus. Consider manual review to upgrade to CONFIRMED status.

#### C. Chronological Misbehavior Patterns

**Pattern 1: Repeated Attempts**
- Detects (prefix, ASN) pairs announced >5 times
- Could indicate:
  - Route flapping (legitimate but unstable BGP)
  - Attack retry attempts (malicious)
  - Network instability

**Pattern 2: Temporal Bursts**
- Detects bursts of ≥10 transactions in 60-second windows
- Could indicate:
  - BGP storm (legitimate mass updates)
  - DDoS attack (malicious flooding)
  - Simulation artifact

**Pattern 3: Consensus Escalation**
- Detects same prefix/ASN getting increasing consensus over time
- Example: 0 votes → 1 vote → 2 votes → 3 votes (CONFIRMED)
- Could indicate:
  - Network stabilization (nodes gradually agreeing)
  - Attack evolution (attacker refining technique)

#### D. Cross-Node Correlation
- Verifies all nodes have identical SINGLE_WITNESS records
- **Expected:** All nodes should agree (deterministic blockchain)
- **If different:** Blockchain fork detected (consensus failure)

#### E. Upgrade Recommendations
- Identifies high-confidence INSUFFICIENT_CONSENSUS transactions
- **Criteria:**
  - 2 approve votes (one away from consensus)
  - Marked as legitimate (not attack)
  - High trust score
- **Action:** Manual review for potential upgrade to CONFIRMED

---

## Output Example

```
================================================================================
TARGETED ATTACK & UNCONFIRMED TRANSACTION ANALYZER
================================================================================
Experiment Directory: ../experiment_results/run_2025_12_02_14_30/
Analysis Time: 2025-12-02 14:45:23

[+] Loaded 1523 blocks from as01
[+] Loaded 1523 blocks from as03
[+] Loaded 1523 blocks from as05
...

================================================================================
EXTRACTING TRANSACTIONS BY CONSENSUS STATUS
================================================================================

[+] Transaction Distribution:
    - CONFIRMED (3+ votes):              2847
    - INSUFFICIENT_CONSENSUS (1-2 votes): 312
    - SINGLE_WITNESS (0 votes):           45
    - TOTAL:                              3204

================================================================================
ANALYZING SINGLE_WITNESS TRANSACTIONS (0 Votes)
================================================================================

[!] Found 45 SINGLE_WITNESS transactions
[!] These are potential targeted attacks or node-specific observations

Breakdown by Attack Status:
    - Marked as ATTACK:     38
    - Marked as LEGITIMATE: 7

[!] RED FLAG: 7 legitimate announcements with 0 votes!
    Possible reasons:
    1. Network partition (node isolated)
    2. Timing issue (votes arrived after timeout)
    3. Node malfunction (observers didn't broadcast)
    4. Truly unique observation (only one node saw it)

SINGLE_WITNESS by Observer Node:
    - AS1: 12 transactions
    - AS3: 8 transactions
    - AS5: 7 transactions
    ...

================================================================================
ANALYZING INSUFFICIENT_CONSENSUS TRANSACTIONS (1-2 Votes)
================================================================================

[*] Found 312 INSUFFICIENT_CONSENSUS transactions
[*] These represent partial agreement (not enough for full consensus)

Breakdown by Vote Count:
    - 1 approve vote:  189
    - 2 approve votes: 123

[*] UPGRADE CANDIDATES: 123 transactions with 2 votes
    These are ONE VOTE AWAY from full consensus (3/9)
    Consider manual review for potential upgrade to CONFIRMED

================================================================================
ANALYZING CHRONOLOGICAL MISBEHAVIOR PATTERNS
================================================================================

[!] REPEATED ATTEMPTS DETECTED:
    Found 23 (prefix, ASN) pairs with >5 announcements
    This could indicate:
    1. Route flapping (legitimate but unstable)
    2. Attack retry attempts (malicious)
    3. BGP instability (network issues)

    - 192.168.1.0/24 from AS666: 15 attempts (12 marked as attacks)
    - 10.0.0.0/8 from AS777: 8 attempts (8 marked as attacks)
    ...

[*] TEMPORAL BURST ANALYSIS:
    [!] Detected 5 temporal bursts (>=10 txs in 60s)
        - Time 1800s: 23 transactions
        - Time 1862s: 15 transactions
        ...

[*] CONSENSUS ESCALATION ANALYSIS:
    [*] Found 12 escalation patterns (increasing consensus over time)
        - 192.168.1.0/24 from AS666: votes over time [0, 1, 2, 3]
        - 10.0.0.0/8 from AS777: votes over time [1, 2, 3]
        ...

================================================================================
CROSS-NODE CORRELATION ANALYSIS
================================================================================

[*] Checking SINGLE_WITNESS consistency across 9 nodes:
    [+] as01: CONSISTENT
    [+] as03: CONSISTENT
    [+] as05: CONSISTENT
    ...

[+] All nodes have identical SINGLE_WITNESS records (blockchain consensus working)

================================================================================
UPGRADE RECOMMENDATIONS
================================================================================

[*] Found 87 upgrade candidates (2 votes, legitimate, high trust)
    These transactions are ONE VOTE away from consensus
    Consider manual review and potential upgrade to CONFIRMED status

    1. 192.168.100.0/24 from AS100 (observed by AS1)
       Trust Score: 0.95 | Time: 2400s
    2. 10.50.0.0/16 from AS200 (observed by AS3)
       Trust Score: 0.92 | Time: 2456s
    ...

================================================================================
EXECUTIVE SUMMARY
================================================================================

📊 CONSENSUS BREAKDOWN:
    - Total Transactions:        3204
    - CONFIRMED (3+ votes):      2847 (88.86%)
    - INSUFFICIENT (1-2 votes):   312 ( 9.74%)
    - SINGLE_WITNESS (0 votes):    45 ( 1.40%)

🎯 CONSENSUS QUALITY:
    ✅ EXCELLENT: 88.9% consensus rate

🚨 TARGETED ATTACK ANALYSIS:
    - SINGLE_WITNESS transactions: 45
    - Marked as attacks: 38
    - Potential targeted attacks: 7

💡 RECOMMENDATIONS:
    ✅ System performing well - no immediate action needed

================================================================================
ANALYSIS COMPLETE
================================================================================
```

---

## Interpretation Guide

### Consensus Rate Thresholds

| Consensus Rate | Quality | Action Needed |
|----------------|---------|---------------|
| ≥90% | ✅ Excellent | None - system working well |
| 70-89% | ⚠️ Good | Monitor for trends |
| 50-69% | ⚠️ Moderate | Investigate causes |
| <50% | ❌ Poor | Urgent investigation required |

### SINGLE_WITNESS Rate Thresholds

| Rate | Status | Interpretation |
|------|--------|----------------|
| 0-2% | ✅ Normal | Expected level of unique observations |
| 2-5% | ⚠️ Elevated | Check for timing issues or network delays |
| 5-10% | ⚠️ High | Possible network partition or node isolation |
| >10% | ❌ Critical | System malfunction or attack in progress |

### INSUFFICIENT_CONSENSUS Rate Thresholds

| Rate | Status | Interpretation |
|------|--------|----------------|
| 0-10% | ✅ Normal | Expected level of partial agreement |
| 10-20% | ⚠️ Elevated | Consider lowering consensus threshold |
| 20-30% | ⚠️ High | Investigate vote deduplication or timeout settings |
| >30% | ❌ Critical | Consensus mechanism not working properly |

---

## Common Scenarios

### Scenario 1: High SINGLE_WITNESS Rate (>10%)

**Symptoms:**
- Many transactions with 0 votes
- Legitimate announcements with no support

**Possible Causes:**
1. **Network Partition:** Nodes can't communicate with peers
2. **Timeout Too Short:** Votes arrive after 60s timeout expires
3. **Sampling Issue:** 1-hour window too aggressive

**Investigation Steps:**
```bash
# Check network logs for communication failures
grep "Connection refused" experiment_results/*/logs/*.log

# Check timeout statistics
grep "TIMEOUT" experiment_results/*/logs/*.log | wc -l

# Check sampling cache effectiveness
grep "Skipped due to sampling" experiment_results/*/logs/*.log | wc -l
```

**Solutions:**
- Increase timeout values (currently 60s regular, 180s attacks)
- Check network configuration for firewall/routing issues
- Adjust sampling window (currently 3600s = 1 hour)

### Scenario 2: Many UPGRADE CANDIDATES (>100 with 2 votes)

**Symptoms:**
- Lots of transactions with 2 votes (one away from consensus)
- High INSUFFICIENT_CONSENSUS rate

**Possible Causes:**
1. **Consensus Threshold Too High:** 3/9 (33%) may be too strict
2. **Network Delays:** Third vote arrives after timeout
3. **Byzantine Behavior:** Some nodes not voting reliably

**Investigation Steps:**
```bash
# Analyze vote distribution
grep "approve_count.*2" experiment_results/*/blockchain_data/blockchain.json | wc -l

# Check for late votes (arrived after timeout)
grep "Vote received after timeout" experiment_results/*/logs/*.log
```

**Solutions:**
- Consider lowering consensus threshold to 2/9 (22%)
- Increase timeout for regular transactions (currently 60s)
- Implement reputation weighting (2 votes from high-trust nodes = consensus)

### Scenario 3: Blockchain Fork Detected

**Symptoms:**
- Cross-node correlation shows inconsistent SINGLE_WITNESS records
- Different nodes have different blockchains

**Possible Causes:**
1. **Network Partition:** Nodes split into isolated groups
2. **Race Condition:** Concurrent block commits with different transactions
3. **Bug in Consensus:** Implementation error in vote collection

**Investigation Steps:**
```bash
# Compare blockchain sizes
for node in as01 as03 as05 as07 as09 as11 as13 as15 as17; do
    echo "$node: $(cat experiment_results/run_*/nodes/$node/blockchain_node/blockchain_data/blockchain.json | jq '. | length')"
done

# Check for fork resolution attempts
grep "Fork detected" experiment_results/*/logs/*.log
```

**Solutions:**
- Implement fork resolution (currently only partially implemented)
- Add uncle chain transaction rescue
- Investigate and fix race conditions

### Scenario 4: Repeated Attack Attempts

**Symptoms:**
- Same (prefix, ASN) pair appears >5 times
- Many marked as attacks

**Interpretation:**
- **If attack rate > 80%:** Likely real attack with retry attempts
- **If attack rate < 20%:** Likely route flapping (legitimate BGP instability)
- **If escalating votes:** Attack evolving to gain consensus

**Investigation:**
```bash
# Find most repeated prefix/ASN pairs
python3 targeted_attack_analyzer.py <experiment_dir> | grep "attempts" | sort -t: -k2 -nr | head -10
```

**Action:**
- Review RPKI/IRR validation for these prefixes
- Check if attacker is learning and adapting strategy
- Consider blacklisting persistently malicious ASNs

---

## Integration with Other Analysis Tools

This tool complements existing BGP-Sentry analysis scripts:

### Existing Tools (in `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/`)

1. **`analyze_experiment.py`**
   - **Focus:** Attack detection accuracy, rating changes, classification
   - **Metrics:** Precision, recall, F1-score, confusion matrix
   - **Use after:** Targeted attack analyzer (to validate attack labels)

2. **`behavioral_analysis.py`**
   - **Focus:** Monthly node behavior, BGPCOIN rewards/penalties
   - **Metrics:** Vote accuracy, participation rate, malicious behavior
   - **Use after:** Targeted attack analyzer (to penalize low-consensus nodes)

### Recommended Analysis Pipeline

```bash
# Step 1: Run experiment
python3 main_experiment.py

# Step 2: Targeted attack analysis (THIS TOOL)
cd analysis
python3 targeted_attack_analyzer.py ../experiment_results/latest/

# Step 3: Attack detection analysis
cd ../nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 analyze_experiment.py ../../../../experiment_results/latest/

# Step 4: Behavioral analysis (monthly)
python3 behavioral_analysis.py ../../../../experiment_results/latest/
```

---

## Customization

### Adjusting Thresholds

Edit `targeted_attack_analyzer.py` to customize detection thresholds:

```python
# Line ~375: Repeated attempts threshold
REPEATED_THRESHOLD = 5  # Change to 10 for less sensitive detection

# Line ~430: Temporal burst settings
BURST_WINDOW = 60        # Change to 120 for 2-minute window
BURST_THRESHOLD = 10     # Change to 20 for higher threshold
```

### Adding Custom Metrics

To add new analysis dimensions:

1. Add method to `TargetedAttackAnalyzer` class
2. Call from `run_full_analysis()` method
3. Update summary report with new findings

Example:
```python
def analyze_trust_score_correlation(self):
    """Analyze if trust scores correlate with consensus success"""
    # Your analysis logic here
    pass

# In run_full_analysis():
self.analyze_trust_score_correlation()  # Add this line
```

---

## Troubleshooting

### Error: "Directory not found"

**Cause:** Invalid experiment results path

**Solution:**
```bash
# Verify path exists
ls -la experiment_results/

# Use correct path format
python3 targeted_attack_analyzer.py ../experiment_results/run_2025_12_02_14_30/
```

### Error: "No blockchain data found"

**Cause:** Experiment didn't run to completion or blockchain files missing

**Solution:**
```bash
# Check if blockchain.json exists for each node
ls experiment_results/*/nodes/*/blockchain_node/blockchain_data/blockchain.json

# If missing, experiment may have crashed - check logs
tail -100 experiment_results/*/logs/*.log
```

### Warning: "INCONSISTENT" cross-node correlation

**Cause:** Blockchain fork (nodes have different blockchains)

**Solution:**
- This is a CRITICAL issue indicating consensus failure
- Investigate logs for network partition or race conditions
- Implement fork resolution (see `ARCHITECTURE_DETAILS.md` Section 9)

---

## Future Enhancements

Planned improvements for this tool:

1. **Machine Learning Integration**
   - Train classifier on SINGLE_WITNESS patterns
   - Auto-detect targeted attacks vs legitimate observations
   - Predict upgrade candidates with confidence scores

2. **Real-Time Monitoring**
   - Live analysis during experiment (not just post-hoc)
   - Alert on high SINGLE_WITNESS rate in real-time
   - Dashboard visualization of consensus trends

3. **Comparative Analysis**
   - Compare multiple experiment runs
   - Track consensus improvements over time
   - A/B testing for parameter tuning (timeout, threshold, sampling)

4. **Automated Upgrade**
   - Auto-upgrade high-confidence INSUFFICIENT_CONSENSUS transactions
   - Machine learning model to predict upgrade candidates
   - Integration with monthly behavioral analysis

---

## Questions or Issues?

- **Documentation:** See `COLLABORATOR_GUIDE.md` for comprehensive guide
- **Architecture:** See `ARCHITECTURE_DETAILS.md` for implementation details
- **GitHub:** Open an issue for bugs or feature requests

---

**Last Updated:** 2025-12-02
**Author:** BGP-Sentry Development Team
**Version:** 1.0
