# BGPCOIN - Complete Incentive System Documentation

## 🪙 Overview

**BGPCOIN** is the protocol-level incentive token for the BGP-Sentry blockchain network. It maintains RPKI observer honesty and participation quality through a sustainable circular economy.

**Token Specifications:**
- **Name**: BGPCOIN
- **Symbol**: BGPC
- **Total Supply**: 10,000,000 BGPCOIN (limited)
- **Initial Distribution**: All coins start in Protocol Treasury
- **Distribution Model**: Earn through participation and accuracy
- **Economic Model**: 50% burn / 50% recycle on spending

---

## 💰 Reward System

### **1. Immediate Rewards (Per-Block)**

Awarded instantly when a node successfully commits a transaction to the blockchain:

| Action | Reward | Notes |
|--------|--------|-------|
| **Block Commit** | 10 BGPCOIN | Base reward for node that commits block |
| **First-to-Commit Bonus** | +5 BGPCOIN | Extra reward if first to reach consensus |
| **Vote (Approve)** | 1 BGPCOIN | Each node that voted approve correctly |

**Reward Formula:**
```
C_earned = C_base × A_accuracy × P_participation × Q_quality
```

Where:
- **C_base**: Base reward amount (10, 15, or 1 BGPCOIN)
- **A_accuracy**: Historical accuracy multiplier (0.5 - 1.5)
- **P_participation**: Participation consistency (0.8 - 1.2)
- **Q_quality**: Evidence quality (0.9 - 1.3)

**Example:**
```
Node AS01 commits a block:
- Base reward: 10 BGPCOIN
- First-to-commit: +5 BGPCOIN
- Accuracy multiplier: 1.2 (good history)
- Participation multiplier: 1.1 (consistent)
- Quality multiplier: 1.0 (average)

Total: (10 + 5) × 1.2 × 1.1 × 1.0 = 19.8 BGPCOIN

Voters (AS03, AS05, AS07):
Each gets: 1 × 1.2 × 1.1 × 1.0 = 1.32 BGPCOIN
```

---

### **2. Monthly Behavioral Rewards (Long-term)**

Awarded based on consensus-approved monthly analysis:

| Performance | Bonus/Penalty | Threshold |
|-------------|--------------|-----------|
| **Top Performer** | +500 BGPCOIN | Highest overall score |
| **High Accuracy** | +200 BGPCOIN | >95% voting accuracy |
| **Perfect Participation** | +100 BGPCOIN | 100% participation rate |
| **Consistent Quality** | +150 BGPCOIN | Quality multiplier >1.2 |
| **Low Accuracy** | -100 BGPCOIN | <50% accuracy |
| **Poor Participation** | -50 BGPCOIN | <30% participation |
| **Suspected Malicious** | -500 BGPCOIN | False votes > correct votes |

**Multiplier Adjustments:**

After monthly analysis, multipliers are updated:

```
Accuracy Multiplier (0.5 - 1.5):
  >95% accuracy → 1.5
  >80% accuracy → 1.2
  >60% accuracy → 1.0
  >40% accuracy → 0.7
  <40% accuracy → 0.5

Participation Multiplier (0.8 - 1.2):
  >90% participation → 1.2
  >70% participation → 1.1
  >50% participation → 1.0
  >30% participation → 0.9
  <30% participation → 0.8

Quality Multiplier (0.9 - 1.3):
  Set by behavioral analysis
```

---

## 🔄 Circular Economy

### **Flow Diagram:**

```
┌─────────────────────────────────────────────────────────┐
│  PROTOCOL TREASURY                                      │
│  Initial: 10,000,000 BGPCOIN                           │
│  Current: Decreases as rewards distributed              │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼ (Rewards for participation)
┌─────────────────────────────────────────────────────────┐
│  RPKI OBSERVERS                                         │
│  - Earn BGPCOIN for committing blocks                  │
│  - Earn BGPCOIN for voting correctly                   │
│  - Earn monthly bonuses for good behavior              │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼ (Spend on governance/services)
┌─────────────────────────────────────────────────────────┐
│  NETWORK SERVICES                                       │
│  - Governance voting (costs BGPCOIN)                   │
│  - Premium analytics (future)                           │
│  - Technical support (future)                           │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼ (50% burn / 50% recycle)
┌─────────────────────────────────────────────────────────┐
│  COIN PROCESSING                                        │
│  - 50% permanently BURNED (deflationary pressure)      │
│  - 50% RECYCLED to treasury (sustainability)           │
└──────────────┬──────────────────────────────────────────┘
               │
               └──► Back to Protocol Treasury
```

### **Spending Mechanism:**

```python
# When node spends 100 BGPCOIN:
spend_amount = 100

burned = 100 × 0.5 = 50 BGPCOIN   # Permanently removed
recycled = 100 × 0.5 = 50 BGPCOIN # Returns to treasury

# Effects:
total_burned += 50        # Reduces total supply
treasury_balance += 50    # Replenishes treasury
node_balance -= 100       # Deducted from spender
```

---

## 📜 Governance System

### **Decentralized Decision Making**

All major network operations require consensus through BGPCOIN-weighted voting:

### **Governance Vote Types:**

| Vote Type | Purpose | Consensus Required |
|-----------|---------|-------------------|
| **Monthly Analysis** | Run behavioral analysis | 66% |
| **Trust Modification** | Change trust scoring | 75% |
| **Reward Adjustment** | Modify BGPCOIN rewards | 66% |
| **Threat Detection** | Add new attack detection | 60% |
| **Protocol Upgrade** | Major system changes | 75% |

### **Voting Process:**

```
STEP 1: Proposal
───────────────
Any node can propose:
  AS01: "Run monthly analysis for November 2025"

STEP 2: Broadcast
──────────────────
Proposal sent to all 8 other nodes via P2P network

STEP 3: Voting
──────────────
Each node votes (approve/reject):
  AS01: APPROVE (1,250 BGPCOIN)
  AS03: APPROVE (980 BGPCOIN)
  AS05: APPROVE (1,100 BGPCOIN)
  AS07: APPROVE (750 BGPCOIN)
  AS09: APPROVE (890 BGPCOIN)
  AS11: REJECT  (650 BGPCOIN)
  AS13: REJECT  (420 BGPCOIN)
  AS15: APPROVE (1,050 BGPCOIN)
  AS17: APPROVE (810 BGPCOIN)

STEP 4: Consensus Check
────────────────────────
Simple Majority: 7/9 nodes (77.8%) ✅
Weighted Vote: 7,830/8,900 BGPCOIN (87.9%) ✅
Required Threshold: 66% ✅

STEP 5: Execution
─────────────────
✅ Consensus reached → Execute on ALL nodes
✅ Monthly analysis runs automatically
✅ Results recorded on blockchain
```

---

## 📊 Economics & Sustainability

### **Supply Dynamics:**

```
Initial State:
  Total Supply: 10,000,000 BGPCOIN
  Treasury: 10,000,000 BGPCOIN
  Circulating: 0 BGPCOIN

After 1 Year (Example):
  Total Supply: 9,500,000 BGPCOIN (500k burned)
  Treasury: 6,000,000 BGPCOIN (distributed 4M, recycled 2M)
  Circulating: 3,500,000 BGPCOIN (held by nodes)
  Burned: 500,000 BGPCOIN (from 1M spent)
  Recycled: 500,000 BGPCOIN (back to treasury)

After 10 Years:
  Total Supply: ~7,000,000 BGPCOIN (3M burned)
  Treasury: ~2,000,000 BGPCOIN
  Circulating: ~5,000,000 BGPCOIN
  System reaches equilibrium
```

### **Deflationary Pressure:**

Every spending event **permanently removes** 50% of spent coins:

```
Burn Rate = 0.5 × Spending Rate

If 1000 BGPCOIN spent per day:
  Daily Burn: 500 BGPCOIN
  Yearly Burn: 182,500 BGPCOIN (~1.8% of total supply)

This creates scarcity and value appreciation over time.
```

### **Sybil Attack Prevention:**

BGPCOIN holdings prevent Sybil attacks:

```
Attacker creates 100 fake nodes:
  - Each has 0 BGPCOIN (no voting power)
  - Weighted vote: 0/total_supply = 0%
  - Cannot influence governance

Honest node with 100,000 BGPCOIN:
  - Weighted vote: 100,000/total_supply = 1%
  - Significant influence based on earned reputation
```

---

## 🔒 Security Model

### **Incentive Alignment:**

| Behavior | Economic Outcome |
|----------|-----------------|
| **Honest Voting** | Earn 1 BGPCOIN per vote + multiplier bonuses |
| **False Approval** | Risk -5 BGPCOIN penalty if detected |
| **False Rejection** | Lose -2 BGPCOIN + reduced accuracy multiplier |
| **Commit Blocks** | Earn 10-15 BGPCOIN + future multiplier benefits |
| **Poor Participation** | -50 BGPCOIN monthly + reduced multipliers |
| **Malicious Behavior** | -500 BGPCOIN + 0.5 multiplier (severe penalty) |

### **Game Theory:**

**Nash Equilibrium:** Honest participation

```
Honest Strategy Payoff:
  Monthly blocks: 10 × 10 = 100 BGPCOIN
  Monthly votes: 300 × 1 = 300 BGPCOIN
  Monthly bonus: +200 BGPCOIN (high accuracy)
  Total: 600 BGPCOIN/month

Malicious Strategy Payoff:
  Attempt to approve fake tx: +10 BGPCOIN (if successful)
  Detected as malicious: -500 BGPCOIN
  Multiplier reduced to 0.5: Future earnings halved
  Expected value: NEGATIVE

Conclusion: Honesty is economically optimal strategy
```

---

## 🛠️ Implementation

### **File Structure:**

```
blockchain_utils/
├── bgpcoin_ledger.py          # Token ledger and balance management
├── behavioral_analysis.py     # Monthly analysis system
├── governance_system.py       # Decentralized voting
└── p2p_transaction_pool.py    # Integrated reward distribution

blockchain_data/state/
├── bgpcoin_ledger.json        # Current balances and stats
├── bgpcoin_transactions.jsonl # Transaction history
├── behavioral_analysis.json   # Latest analysis results
├── analysis_history.jsonl     # Historical analysis
├── governance_proposals.json  # Active governance votes
└── governance_votes.jsonl     # Vote history
```

### **Key Classes:**

**1. BGPCoinLedger**
```python
ledger = BGPCoinLedger("blockchain_data/state")

# Award rewards
ledger.award_block_commit_reward(
    committer_as=1,
    voter_as_list=[3, 5, 7],
    is_first=True
)

# Spend coins (50% burn / 50% recycle)
ledger.spend_coins(
    as_number=1,
    amount=100,
    purpose="governance_vote"
)

# Check balance
balance = ledger.get_balance(1)
```

**2. BehavioralAnalyzer**
```python
analyzer = BehavioralAnalyzer(blockchain, ledger)

# Run monthly analysis
result = analyzer.run_monthly_analysis(days=30)
```

**3. GovernanceSystem**
```python
governance = GovernanceSystem(as_number=1, ledger=ledger, p2p_pool=pool)

# Propose monthly analysis
proposal_id = governance.propose_monthly_analysis("November 2025")

# Vote on proposal
governance.vote_on_proposal(proposal_id, "approve")
```

---

## 📈 Metrics & Monitoring

### **Node Statistics:**

```json
{
  "as_number": 1,
  "balance": 1250.50,
  "stats": {
    "accuracy": 1.2,
    "participation": 1.1,
    "quality": 1.0,
    "blocks_committed": 15,
    "votes_cast": 250,
    "correct_votes": 245,
    "false_votes": 5,
    "total_earned": 3500.00,
    "total_spent": 2250.00
  }
}
```

### **Treasury Monitoring:**

```json
{
  "total_supply": 10000000,
  "treasury_balance": 6500000,
  "circulating_supply": 3200000,
  "total_distributed": 4000000,
  "total_burned": 200000,
  "total_recycled": 500000
}
```

---

## 🎯 Example Scenarios

### **Scenario 1: Honest Node Operation (1 Month)**

```
Node AS01 Performance:
  - Committed 15 blocks (first-to-commit: 5 times)
  - Cast 300 votes (all correct)
  - 100% participation
  - 100% accuracy

Earnings:
  Block rewards: 15 × (10 + 1.2 multiplier) = 180 BGPCOIN
  First bonuses: 5 × 5 = 25 BGPCOIN
  Vote rewards: 300 × (1 × 1.2) = 360 BGPCOIN
  Monthly bonuses: 200 (accuracy) + 100 (participation) = 300 BGPCOIN

  Total: 865 BGPCOIN in 1 month

Balance: 865 BGPCOIN (no spending)
```

### **Scenario 2: Malicious Node (Detected)**

```
Node AS17 Behavior:
  - Attempted to approve fake transaction (knowledge-based voting rejected it)
  - Cast 50 false votes
  - Low participation (20%)

Penalties:
  Monthly penalty: -500 BGPCOIN (malicious detection)
  Low participation: -50 BGPCOIN
  Accuracy multiplier reduced: 0.5 (future earnings halved)
  Participation multiplier: 0.8

Balance: -550 BGPCOIN (if had balance, reduced to 0)
Future earnings: Halved due to multipliers
```

### **Scenario 3: Governance Vote Execution**

```
Proposal: Run Monthly Analysis

Voting:
  7/9 nodes approve
  Weighted: 87.9% of BGPCOIN voting power
  Threshold: 66% required

Result: ✅ CONSENSUS REACHED

Execution:
  All 9 nodes automatically run behavioral analysis
  Results saved to blockchain
  Rewards/penalties distributed
  Multipliers updated for next month
```

---

## 🚀 Future Enhancements

### **Potential Additions:**

1. **Staking Mechanism**
   - Lock BGPCOIN for enhanced rewards
   - Slashing for misbehavior

2. **External Value**
   - Future tradability on exchanges
   - Real economic value increases participation motivation

3. **Advanced Governance**
   - Quadratic voting (prevent whale control)
   - Time-locked proposals
   - Veto mechanisms

4. **Dynamic Rewards**
   - Adjust based on network needs
   - Increase rewards during attacks
   - Seasonal variations

---

## 📚 References

- **Implementation**: `blockchain_utils/bgpcoin_ledger.py`
- **Behavioral Analysis**: `blockchain_utils/behavioral_analysis.py`
- **Governance**: `blockchain_utils/governance_system.py`
- **Integration**: `blockchain_utils/p2p_transaction_pool.py`
- **Proposal**: Original BGP-Sentry research paper

---

**BGPCOIN: Sustainable Blockchain Economics for Internet Security**

