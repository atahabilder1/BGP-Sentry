# Consensus Escalation - Detecting Learning Attackers

## What is Consensus Escalation?

**Consensus Escalation** is a pattern where the **same attacker** (same IP prefix + sender ASN) announces the **same route multiple times**, and each attempt gets **progressively more votes**.

This indicates the attacker is **learning** and **improving their attack** to gain more trust from the network.

---

## The Attack Pattern

### Normal Attacker (No Learning)
```
Time 0s:   AS99 announces 192.168.1.0/24 → 0 votes (SINGLE_WITNESS)
Time 60s:  AS99 announces 192.168.1.0/24 → 0 votes (SINGLE_WITNESS)
Time 120s: AS99 announces 192.168.1.0/24 → 0 votes (SINGLE_WITNESS)

Pattern: [0, 0, 0] ← No escalation (static attack)
```

### Learning Attacker (Escalation Detected!)
```
Time 0s:   AS99 announces 192.168.1.0/24 → 0 votes (SINGLE_WITNESS)
Time 60s:  AS99 announces 192.168.1.0/24 → 1 vote (INSUFFICIENT_CONSENSUS)
Time 120s: AS99 announces 192.168.1.0/24 → 2 votes (INSUFFICIENT_CONSENSUS)

Pattern: [0, 1, 2] ← ESCALATION! Attacker is learning!
```

**Why is this dangerous?**
- First attempt: Completely rejected (0 votes)
- Second attempt: Attacker improved forgery, gained 1 vote
- Third attempt: Attacker improved again, gained 2 votes
- **Next attempt might get 3 votes → CONFIRMED!** (attack succeeds!)

---

## How the Detection Works

### Code Location: `analysis/targeted_attack_analyzer.py:307-337`

```python
def _detect_escalation_patterns(self):
    """Detect patterns where same prefix/ASN gets increasing consensus over time"""
    escalations = []

    # For each unique (prefix, ASN) pair
    for (prefix, asn), txs in self.prefix_patterns.items():
        if len(txs) < 2:
            continue  # Need at least 2 attempts to detect escalation

        # Sort by timestamp (chronological order)
        txs_sorted = sorted(txs, key=lambda x: x.get("timestamp", 0))

        # Check for escalation (increasing approve_count over time)
        prev_count = txs_sorted[0].get("approve_count", 0)
        escalated = False

        for tx in txs_sorted[1:]:
            curr_count = tx.get("approve_count", 0)
            if curr_count > prev_count:  # Vote count increased!
                escalated = True
            prev_count = curr_count

        if escalated:
            escalations.append((prefix, asn, txs_sorted))

    # Report findings
    if escalations:
        print(f"    [*] Found {len(escalations)} escalation patterns")
        for prefix, asn, txs in escalations[:5]:
            counts = [tx.get("approve_count", 0) for tx in txs]
            print(f"        - {prefix} from AS{asn}: votes over time {counts}")
```

---

## Step-by-Step Example

### Scenario: Attacker AS99 Learns Over Time

**Attack Timeline:**

1. **First Attempt (Time 0s):**
   ```json
   {
     "ip_prefix": "192.168.1.0/24",
     "sender_asn": 99,
     "timestamp": 0,
     "approve_count": 0,
     "consensus_status": "SINGLE_WITNESS"
   }
   ```
   - Attacker sends completely fake BGP announcement
   - All RPKI nodes reject it (trust score too low)
   - **Result: 0 votes**

2. **Second Attempt (Time 60s):**
   ```json
   {
     "ip_prefix": "192.168.1.0/24",
     "sender_asn": 99,
     "timestamp": 60,
     "approve_count": 1,
     "consensus_status": "INSUFFICIENT_CONSENSUS"
   }
   ```
   - Attacker **improved** the forgery:
     - Used more realistic AS path
     - Better timing (looks less suspicious)
     - Forged BGP attributes more carefully
   - **One RPKI node (AS3) is fooled** → approves
   - **Result: 1 vote**

3. **Third Attempt (Time 120s):**
   ```json
   {
     "ip_prefix": "192.168.1.0/24",
     "sender_asn": 99,
     "timestamp": 120,
     "approve_count": 2,
     "consensus_status": "INSUFFICIENT_CONSENSUS"
   }
   ```
   - Attacker **improved further**:
     - Used even more realistic BGP path
     - Timed announcement to match legitimate traffic patterns
     - Maybe spoofed trust score calculation inputs
   - **Two RPKI nodes (AS3, AS5) are fooled** → approve
   - **Result: 2 votes**

4. **Fourth Attempt (Time 180s) - DANGER ZONE:**
   ```json
   {
     "ip_prefix": "192.168.1.0/24",
     "sender_asn": 99,
     "timestamp": 180,
     "approve_count": 3,  ← REACHED CONSENSUS!
     "consensus_status": "CONFIRMED"  ← ATTACK SUCCEEDED!
   }
   ```
   - Attacker's refinement **crosses threshold**
   - **Three RPKI nodes approve** → consensus reached!
   - **Attack is now written to blockchain as CONFIRMED**
   - **ATTACK SUCCEEDED!**

---

## What the Analyzer Shows

**Output:**
```
CONSENSUS ESCALATION ANALYSIS:
    [*] Found 1 escalation patterns (increasing consensus over time)
        - 192.168.1.0/24 from AS99: votes over time [0, 1, 2]
                                                      ↑  ↑  ↑
                                                      │  │  └─ 3rd attempt: 2 votes
                                                      │  └──── 2nd attempt: 1 vote
                                                      └─────── 1st attempt: 0 votes
```

**Interpretation:**
- `[0, 1, 2]` shows **clear escalation**
- Each attempt is getting **more votes**
- **Attacker is learning** and improving their attack
- **Next attempt might reach 3 votes** → consensus → attack succeeds!

---

## Why This Matters

### Without Escalation Detection:
```
System log:
- Transaction 1: SINGLE_WITNESS (0 votes)
- Transaction 2: INSUFFICIENT_CONSENSUS (1 vote)
- Transaction 3: INSUFFICIENT_CONSENSUS (2 votes)

Human analysis: "These look like random failed transactions"
```

### With Escalation Detection:
```
System log:
- Transaction 1: SINGLE_WITNESS (0 votes)
- Transaction 2: INSUFFICIENT_CONSENSUS (1 vote)  } Same attacker
- Transaction 3: INSUFFICIENT_CONSENSUS (2 votes) } Same prefix
                                                   } Increasing votes!

Escalation Analysis: [0, 1, 2]

Human analysis: "🚨 ALERT! Attacker is learning and improving!
                 Next attempt might succeed!"
```

---

## Real-World Attack Examples

### Example 1: BGP Hijacking Practice
```
Time 0s:   Attacker tests basic hijack → 0 votes
Time 60s:  Attacker adds fake AS-PATH → 1 vote
Time 120s: Attacker forges ROA validation → 2 votes
Time 180s: Attacker perfects timing → 3 votes → CONFIRMED!
```

**Escalation Pattern:** `[0, 1, 2, 3]` ← Successfully learned how to bypass detection

### Example 2: Route Origin Forgery
```
Time 0s:   Attacker claims ownership of 1.2.3.0/24 → 0 votes
Time 30s:  Attacker improves trust score calculation → 1 vote
Time 60s:  Attacker matches legitimate announcement pattern → 2 votes
```

**Escalation Pattern:** `[0, 1, 2]` ← Learning in progress, HIGH RISK

### Example 3: Prefix Hijacking Refinement
```
Time 0s:   Announce 10.0.0.0/8 (too broad, rejected) → 0 votes
Time 60s:  Announce 10.1.0.0/16 (more specific) → 1 vote
Time 120s: Announce 10.1.2.0/24 (very specific) → 2 votes
```

**Escalation Pattern:** `[0, 1, 2]` ← Attacker refining prefix specificity

---

## How Attacker Learns (Technical)

### Possible Learning Methods:

1. **Trial and Error:**
   - Send announcement → see if it gets accepted
   - Adjust parameters → send again
   - Repeat until successful

2. **Feedback Analysis:**
   - Analyze which nodes approved (from blockchain)
   - Identify what made those nodes approve
   - Tailor next attempt to those criteria

3. **Trust Score Reverse Engineering:**
   - Observe correlation between trust scores and votes
   - Forge inputs to increase trust score
   - Example: If high trust score → more votes, fake the trust score calculation

4. **Timing Optimization:**
   - First attempt: Random timing → rejected
   - Second attempt: During BGP update window → 1 vote
   - Third attempt: Exactly when legitimate updates occur → 2 votes

5. **AS Path Manipulation:**
   - Attempt 1: Simple direct path → 0 votes
   - Attempt 2: Add intermediate ASes → 1 vote
   - Attempt 3: Use realistic path matching network topology → 2 votes

---

## Detection Thresholds

**What counts as escalation?**

✅ **ESCALATION DETECTED:**
```python
# Any increase in vote count
[0, 1]        # 0 → 1 (escalation)
[1, 2]        # 1 → 2 (escalation)
[0, 1, 2]     # 0 → 1 → 2 (escalation)
[0, 0, 1]     # 0 → 0 → 1 (escalation on 3rd attempt)
```

❌ **NO ESCALATION:**
```python
[0, 0, 0]     # Static (no learning)
[1, 1, 1]     # Static (no improvement)
[2, 1, 0]     # Degradation (attacker getting worse)
[2, 2, 2]     # Stuck at 2 votes (not escalating)
```

**Code:**
```python
# Line 322-326
for tx in txs_sorted[1:]:
    curr_count = tx.get("approve_count", 0)
    if curr_count > prev_count:  # ANY increase = escalation
        escalated = True
    prev_count = curr_count
```

---

## Mitigation Strategies

### 1. **Blacklist Escalating Attackers**
```python
# If escalation detected for (prefix, ASN):
if escalation_detected:
    blacklist.add((prefix, asn))
    # Reject all future announcements from this (prefix, ASN)
```

### 2. **Increase Scrutiny**
```python
# If vote count increasing, require HIGHER threshold
if vote_count_increasing:
    consensus_threshold = 5  # Instead of 3
```

### 3. **Rate Limiting**
```python
# Limit attempts per (prefix, ASN) pair
if attempts[(prefix, asn)] > 3:
    reject_for_cooldown_period(prefix, asn, cooldown=3600)  # 1 hour
```

### 4. **Manual Review**
```python
# Flag escalating patterns for human review
if escalation_pattern == [0, 1, 2]:
    alert_security_team(prefix, asn, "Possible learning attacker")
```

---

## Comparison with Other Patterns

| Pattern | Votes Over Time | Meaning | Threat Level |
|---------|----------------|---------|--------------|
| **Static Attack** | `[0, 0, 0, 0]` | Attacker not learning | Low (easily blocked) |
| **Random Noise** | `[1, 0, 2, 1]` | Random variation | Low (inconsistent) |
| **Escalation** | `[0, 1, 2]` | Attacker learning | **HIGH** (improving) |
| **Threshold Breach** | `[0, 1, 2, 3]` | Attack succeeded | **CRITICAL** (already compromised) |
| **Degradation** | `[2, 1, 0]` | Defenses improving | Good (attack failing) |

---

## Example Output from Real Experiment

```
ANALYZING CHRONOLOGICAL MISBEHAVIOR PATTERNS
================================================================================

[*] TEMPORAL BURST ANALYSIS:
    [+] No temporal bursts detected (threshold: 10 txs in 60s)

[*] CONSENSUS ESCALATION ANALYSIS:
    [*] Found 2 escalation patterns (increasing consensus over time)
        - 192.168.1.0/24 from AS99: votes over time [0, 1, 2]
        - 10.0.0.0/8 from AS77: votes over time [0, 0, 1, 2]
```

**Interpretation:**
- **AS99** is learning rapidly: `[0, 1, 2]` (3 attempts, steady increase)
- **AS77** is learning slower: `[0, 0, 1, 2]` (4 attempts, stuck at 0 initially)
- **Both are HIGH RISK** - next attempt might reach consensus (3 votes)

---

## Why "Learning" is Dangerous

### Without Learning (Easy to Defend):
```
Attacker always sends same bad data → 0 votes → never succeeds
Defense: Simple static rules work fine
```

### With Learning (Hard to Defend):
```
Attempt 1: Send bad data → 0 votes
Attacker analyzes: "Why rejected? Trust score too low"

Attempt 2: Improve trust score → 1 vote
Attacker analyzes: "Why only 1 vote? AS path looks fake"

Attempt 3: Fix AS path → 2 votes
Attacker analyzes: "Why only 2 votes? Timing is off"

Attempt 4: Perfect timing → 3 votes → ATTACK SUCCEEDS!
```

**Defense:** Need adaptive, dynamic detection (like escalation analysis)

---

## False Positives

**When might escalation be legitimate?**

### Case 1: Route Stabilization
```
Time 0s:   Legitimate AS announces new prefix → 0 votes (nobody knows it yet)
Time 60s:  AS announces again → 1 vote (one node verified)
Time 120s: AS announces again → 3 votes (all nodes verified)

Pattern: [0, 1, 3] ← Looks like escalation, but legitimate!
```

**How to distinguish:**
- Check `is_attack` flag in transaction
- Escalation + `is_attack=false` = likely legitimate stabilization
- Escalation + `is_attack=true` = learning attacker!

### Case 2: Network Partition Healing
```
Time 0s:   Announcement during network partition → 0 votes (nodes isolated)
Time 60s:  Partition healing → 1 vote (one node reconnected)
Time 120s: Partition healed → 3 votes (all nodes reconnected)

Pattern: [0, 1, 3] ← Network issue, not attack
```

**How to distinguish:**
- Check network connectivity logs
- If many transactions show same pattern → network issue
- If only one (prefix, ASN) shows pattern → likely attack

---

## Summary

**Consensus Escalation Detection:**

✅ **Identifies learning attackers** who improve their attacks over time
✅ **Detects pattern:** Same (prefix, ASN) getting progressively more votes
✅ **Shows vote progression:** `[0, 1, 2]` = attacker learning
✅ **Early warning:** Detects BEFORE attack succeeds (at 2 votes, before 3)
✅ **Actionable:** Allows blacklisting, rate limiting, or manual review

**Key Insight:**
- Static attacks are easy to block
- **Learning attacks are dangerous** because they adapt
- Escalation detection catches them **before they succeed**

**Real-World Analogy:**
- Like detecting a burglar who tries your locks repeatedly
- First attempt: Breaks lock badly → alarm sounds
- Second attempt: Better tools → alarm delayed
- Third attempt: Perfect tools → alarm almost bypassed
- **Escalation detection:** "Hey, this burglar is getting better each time! ALERT!"

---

## Code Reference

**File:** `analysis/targeted_attack_analyzer.py`

| Line | Function |
|------|----------|
| 307-337 | `_detect_escalation_patterns()` - Main detection logic |
| 311-313 | Loop through each (prefix, ASN) pair |
| 316 | Sort transactions chronologically |
| 318-326 | Check if vote count increases over time |
| 332-335 | Report escalation patterns found |

**Data Structure:**
```python
self.prefix_patterns = {
    ("192.168.1.0/24", 99): [tx1, tx2, tx3],  # AS99's attempts
    ("10.0.0.0/8", 77): [tx4, tx5, tx6, tx7]  # AS77's attempts
}
```

**Analysis Flow:**
```
Load all transactions
    ↓
Group by (prefix, ASN)
    ↓
Sort each group by timestamp
    ↓
Check if approve_count increases
    ↓
Report escalations
```

---

## Conclusion

**Consensus Escalation** is a critical security feature that detects **adaptive attackers** who learn from their failures and improve their attacks over time.

Without this detection, attackers could quietly refine their techniques until they successfully compromise the system. With escalation detection, you get **early warning** when an attacker is making progress, allowing you to take action **before** the attack succeeds.
