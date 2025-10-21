# Consensus Threshold Configuration

## ✅ Current Settings

Both consensus systems use **minimum 3 votes** required for decision:

```python
# Transaction Consensus
self.consensus_threshold = 3  # 3/9 = 33% consensus

# Attack Detection Consensus
self.min_votes = 3  # Same as transaction consensus
```

---

## 📊 How It Works

### 1. Transaction Consensus (Knowledge-Based Voting)

**File:** `p2p_transaction_pool.py`

**Logic:**
```python
if approve_votes >= self.consensus_threshold:  # >= 3
    # Consensus reached - commit to blockchain
    self._commit_to_blockchain(tx_id)
```

**Example:**
```
Vote Results:
- AS1: APPROVE
- AS3: APPROVE
- AS5: APPROVE
- AS7: REJECT
- AS9: (no vote yet)

Result: 3 APPROVE votes → ✅ CONSENSUS REACHED
Action: Commit transaction to blockchain
```

**Characteristics:**
- ✅ Simple threshold-based
- ✅ Fast (only need 3 votes)
- ✅ Based on knowledge: "Did I observe this announcement?"

---

### 2. Attack Detection Consensus (Majority Voting)

**File:** `attack_consensus.py`

**Logic:**
```python
# Step 1: Check minimum votes
if tracking["total_votes"] < self.min_votes:  # < 3
    return  # Not enough votes yet

# Step 2: Majority voting
if yes_votes > no_votes:
    verdict = "ATTACK_CONFIRMED"
    confidence = yes_votes / total
elif no_votes > yes_votes:
    verdict = "NOT_ATTACK"
    confidence = no_votes / total
else:
    verdict = "DISPUTED"  # Tie
    confidence = 0.5
```

**Example 1: Attack Confirmed**
```
Vote Results (6 total):
- YES: AS1, AS3, AS5, AS7 (4 votes)
- NO: AS9, AS11 (2 votes)

Result: 4 > 2 → ✅ ATTACK_CONFIRMED
Confidence: 4/6 = 0.67 (67%)
Action: Apply rating penalty, distribute BGPCOIN
```

**Example 2: Attack Rejected**
```
Vote Results (5 total):
- YES: AS1, AS3 (2 votes)
- NO: AS5, AS7, AS9 (3 votes)

Result: 2 < 3 → ❌ NOT_ATTACK
Confidence: 3/5 = 0.60 (60%)
Action: Penalize false accuser, reward correct NO voters
```

**Example 3: Disputed**
```
Vote Results (6 total):
- YES: AS1, AS3, AS5 (3 votes)
- NO: AS7, AS9, AS11 (3 votes)

Result: 3 == 3 → ⚖️ DISPUTED
Confidence: 0.50 (50%)
Action: No penalties/rewards (no clear consensus)
```

**Characteristics:**
- ✅ Requires minimum 3 votes
- ✅ Then uses majority to decide verdict
- ✅ Confidence score preserved (0-1 scale)
- ✅ Based on analysis: "Is this an attack?"

---

## 🔍 Key Differences

| Aspect | Transaction Voting | Attack Voting |
|--------|-------------------|---------------|
| **Minimum votes** | 3 votes | 3 votes |
| **Decision logic** | Threshold (≥3 approvals) | Majority (YES > NO) |
| **Question** | "Did you observe it?" | "Is it an attack?" |
| **Success criteria** | 3+ approvals | Majority agreement |
| **Tie handling** | N/A (just needs 3) | DISPUTED verdict |
| **Confidence** | Not tracked | 0-1 score |

---

## 📈 Voting Scenarios

### Transaction Voting Scenarios

| Approve | Reject | Total | Result |
|---------|--------|-------|--------|
| 3 | 5 | 8 | ✅ CONSENSUS (≥3) |
| 5 | 3 | 8 | ✅ CONSENSUS (≥3) |
| 2 | 6 | 8 | ❌ NO CONSENSUS (<3) |
| 8 | 0 | 8 | ✅ CONSENSUS (≥3) |

### Attack Voting Scenarios

| YES | NO | Total | Min Met? | Verdict | Confidence |
|-----|----|----|----------|---------|------------|
| 6 | 3 | 9 | ✅ | ATTACK_CONFIRMED | 0.67 |
| 3 | 6 | 9 | ✅ | NOT_ATTACK | 0.67 |
| 5 | 4 | 9 | ✅ | ATTACK_CONFIRMED | 0.56 |
| 4 | 5 | 9 | ✅ | NOT_ATTACK | 0.56 |
| 4 | 4 | 8 | ✅ | DISPUTED | 0.50 |
| 2 | 1 | 3 | ✅ | ATTACK_CONFIRMED | 0.67 |
| 1 | 2 | 3 | ✅ | NOT_ATTACK | 0.67 |
| 2 | 0 | 2 | ❌ | (waiting...) | - |

---

## 🎯 Why Minimum 3 Votes?

### Design Rationale

**1. Quick Consensus**
- 3/9 nodes = 33% participation
- Faster than majority (5/9 = 56%)
- Good for high-throughput BGP announcements

**2. Reasonable Security**
- Single malicious node cannot approve alone
- Requires at least 3 independent confirmations
- Balance between speed and security

**3. Scalability**
- With optimized voting (relevant neighbor cache)
- Typical AS has 2-3 RPKI neighbors
- Can often reach consensus with just neighbors

**4. Byzantine Tolerance**
- Can tolerate up to 2 Byzantine failures
- 3 honest nodes out of 9 sufficient
- Practical for distributed consensus

---

## 🔧 Configuration

### Change Transaction Threshold

**File:** `p2p_transaction_pool.py`

```python
def __init__(self, as_number, base_port=8000):
    # ...
    self.consensus_threshold = 3  # Change this value
    # ...
```

**Options:**
- `3` = 33% (current, fast)
- `5` = 56% (majority, more secure)
- `6` = 67% (supermajority, very secure)

### Change Attack Threshold

**File:** `attack_consensus.py`

```python
def __init__(self, as_number, attack_detector, ...):
    # ...
    self.min_votes = 3  # Change this value
    # ...
```

**Note:** Attack voting always uses majority after minimum is met!

---

## 💡 Recommendations

### Current Settings (3 votes minimum)

**Good for:**
- ✅ High-throughput BGP networks
- ✅ Fast consensus needed
- ✅ Optimized voting with neighbor cache
- ✅ Testing and development

**Consider increasing if:**
- ⚠️ Higher security requirements
- ⚠️ Lower trust in network participants
- ⚠️ Critical production deployment

### Alternative Configurations

**Conservative (5 votes = majority):**
```python
self.consensus_threshold = 5  # Transactions
self.min_votes = 5            # Attacks
```

**Very Secure (6 votes = supermajority):**
```python
self.consensus_threshold = 6  # Transactions
self.min_votes = 6            # Attacks
```

---

## 📊 Example Workflows

### Complete Transaction Flow

```
1. AS1 observes BGP announcement from AS100
2. AS1 creates transaction and broadcasts to relevant neighbors
3. Voting:
   - AS1: APPROVE (observed it)
   - AS3: APPROVE (observed it)
   - AS5: APPROVE (observed it)
   - AS7: (cache miss, not queried)

4. ✅ 3/3 APPROVE → CONSENSUS REACHED
5. AS1 commits to blockchain
6. BGPCOIN rewards distributed
7. Attack detection triggered
```

### Complete Attack Detection Flow

```
1. Transaction committed to blockchain
2. Attack detection runs on all nodes
3. AS1 detects IP hijacking by AS666
4. AS1 broadcasts attack proposal
5. Voting:
   - AS1: YES (detected hijacking via ROA)
   - AS3: YES (confirmed via ROA)
   - AS5: YES (confirmed via ROA)
   - AS7: NO (thinks legitimate)
   - AS9: YES (confirmed via ROA)
   - AS11: YES (confirmed via ROA)

6. ✅ 5 YES > 1 NO → ATTACK_CONFIRMED (confidence: 0.83)
7. AS666 rating: 50 → 30 (-20 penalty)
8. BGPCOIN distributed:
   - AS1 (detector): +10 BGPCOIN
   - AS3,5,9,11 (correct YES voters): +2 BGPCOIN each
9. Verdict saved to blockchain
```

---

## 🔍 Monitoring Consensus

### View Transaction Consensus Logs

```bash
# Check consensus messages
grep "CONSENSUS REACHED" observer_main.log

# Check signature collection
grep "Signatures collected" observer_main.log
```

**Example output:**
```
Signatures collected: 3/3 for tx_20251021_123456
🎉 CONSENSUS REACHED (3/9) - Writing to blockchain!
```

### View Attack Consensus Logs

```bash
# Check attack voting
grep "Attack Consensus Check" observer_main.log

# Check verdicts
grep "Attack verdict executed" observer_main.log
```

**Example output:**
```
📊 Attack Consensus Check:
   Votes: 6 YES, 3 NO (9 total)
   Verdict: ATTACK_CONFIRMED
   Confidence: 0.67
✅ Attack verdict executed: ATTACK_CONFIRMED (confidence: 0.67)
```

---

## ✅ Summary

**Current Configuration:**
- ✅ Transaction consensus: 3 votes minimum (simple threshold)
- ✅ Attack consensus: 3 votes minimum + majority voting
- ✅ Both use same minimum (3/9 = 33%)
- ✅ Optimized voting reduces network overhead
- ✅ Fast and efficient for BGP-Sentry deployment

**Key Points:**
1. **Minimum 3 votes** required for both systems
2. **Transaction voting**: 3+ approvals → commit
3. **Attack voting**: 3+ votes → then majority decides
4. **Confidence tracking**: Attack voting preserves vote distribution
5. **Fallback safe**: Unknown ASes query all nodes
6. **Configurable**: Can increase threshold if needed

**Status:** ✅ Working as designed, ready for production!
