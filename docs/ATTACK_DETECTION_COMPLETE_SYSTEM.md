# BGP Attack Detection & Consensus System - Complete Documentation

## 🎯 Overview

The BGP-Sentry attack detection system provides **decentralized, consensus-based identification** of malicious BGP announcements, including:

1. **IP Prefix Hijacking** - AS announces prefix it doesn't own
2. **Route Leak** - AS violates valley-free routing policies

The system uses **majority voting** among RPKI observer nodes to determine if an announcement is malicious, with:
- Instant non-RPKI AS rating updates
- BGPCOIN rewards for accurate detection
- Attack verdicts recorded on blockchain
- Monthly post-hoc analysis for long-term behavior

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  BGP ANNOUNCEMENT FLOW                                          │
└─────────────────────────────────────────────────────────────────┘

1. BGP Announcement Observed
   ↓
2. Knowledge-Based Voting (3/9 consensus)
   ↓
3. Transaction Written to Blockchain
   ↓
4. PARALLEL ATTACK DETECTION
   ├─ Each node runs AttackDetector
   ├─ Checks ROA database (IP hijacking)
   ├─ Checks AS relationships (route leak)
   └─ Broadcasts attack proposal if detected
   ↓
5. ATTACK CONSENSUS VOTING
   ├─ Majority voting (minimum 3 votes)
   ├─ Confidence score calculated (0-1)
   └─ Verdict: ATTACK_CONFIRMED / NOT_ATTACK / DISPUTED
   ↓
6. ACTIONS BASED ON VERDICT
   ├─ CONFIRMED → Update non-RPKI rating
   ├─ CONFIRMED → Award BGPCOIN to detector & voters
   ├─ NOT_ATTACK → Penalize false accuser
   └─ DISPUTED → No action, preserve voter info
   ↓
7. Attack Verdict Written to Blockchain
   (blockchain_data/chain/attack_verdicts.jsonl)
```

---

## 📂 File Structure

### **Core Implementation Files**

```
blockchain_utils/
├── attack_detector.py          # Detects IP hijacking & route leaks
├── nonrpki_rating.py           # Non-RPKI AS trust scoring (0-100)
├── attack_consensus.py         # Majority voting for attack verification
├── p2p_transaction_pool.py     # Integrated P2P communication
├── bgpcoin_ledger.py           # Token rewards & penalties
├── behavioral_analysis.py      # Monthly post-hoc analysis
└── governance_system.py        # Decentralized governance

blockchain_data/
├── chain/
│   ├── blockchain.json         # Transaction records
│   └── attack_verdicts.jsonl   # Attack verdict history
└── state/
    ├── roa_database.json       # IP prefix → Authorized AS
    ├── as_relationships.json   # AS customer/provider/peer relationships
    ├── nonrpki_ratings.json    # Non-RPKI AS trust scores
    ├── rating_history.jsonl    # Rating change history
    ├── knowledge_base.json     # Time-windowed BGP observations
    └── bgpcoin_ledger.json     # Token balances & stats
```

---

## 🔍 Attack Detection Methods

### **1. IP Prefix Hijacking Detection**

**Location**: `attack_detector.py:177` (`detect_ip_prefix_hijacking()`)

**Method**: ROA Database Checking

```python
# ROA Database Format (roa_database.json)
{
  "8.8.8.0/24": {
    "authorized_as": 15169,      # Google's AS
    "max_length": 24,
    "description": "Google DNS"
  }
}

# Detection Logic
if announcement["sender_asn"] != roa_entry["authorized_as"]:
    # HIJACKING DETECTED!
    return {
        "attack_type": "ip_prefix_hijacking",
        "severity": "HIGH",
        "attacker_as": sender_asn,
        "legitimate_owner": authorized_as
    }
```

**Example Attack**:
```
AS666 announces: 8.8.8.0/24
ROA shows: AS15169 (Google) is authorized
Result: IP PREFIX HIJACKING DETECTED
```

### **2. Route Leak Detection**

**Location**: `attack_detector.py:239` (`detect_route_leak()`)

**Method**: Valley-Free Routing Validation

**Valley-Free Principle**:
- Provider → Customer → Any (OK)
- Peer → Customer → Any (OK)
- Customer → Provider/Peer → **Customer ONLY**

```python
# AS Relationship Database (as_relationships.json)
{
  "5": {
    "customers": [8],      # AS5's customers
    "providers": [7],      # AS5 buys transit from AS7
    "peers": [1, 3]        # AS5 peers with AS1, AS3
  }
}

# Detection Logic
for each hop in AS path:
    if received_from provider/peer AND leaked_to provider/peer:
        # ROUTE LEAK DETECTED!
        return {
            "attack_type": "route_leak",
            "severity": "MEDIUM",
            "leaker_as": current_as
        }
```

**Example Attack**:
```
AS Path: [5, 7, 5, 3, 1]
         │  │  │
         │  │  └─ AS5 leaked to peer AS5 (VIOLATION!)
         │  └─ Received from provider AS7
         └─ AS5

Result: ROUTE LEAK DETECTED
```

---

## 🗳️ Attack Consensus Voting

### **Voting Process**

**Location**: `attack_consensus.py`

```
STEP 1: Detection
─────────────────
AS01 detects potential IP hijacking:
  - Prefix: 8.8.8.0/24
  - Announced by: AS666
  - ROA shows: AS15169 (Google)

STEP 2: Broadcast Proposal
───────────────────────────
AS01 creates attack_proposal:
  {
    "proposal_id": "attack_20251021_143522",
    "proposer_as": 1,
    "attack_details": {
      "attack_type": "ip_prefix_hijacking",
      "attacker_as": 666,
      "victim_prefix": "8.8.8.0/24",
      "legitimate_owner": 15169
    }
  }

Broadcasts to all 8 peer nodes

STEP 3: Voting
──────────────
Each node runs their own AttackDetector:

  AS01: YES (detected hijacking)      ✅
  AS03: YES (confirmed via ROA)       ✅
  AS05: YES (confirmed)               ✅
  AS07: NO  (thinks legitimate)       ❌
  AS09: YES (confirmed)               ✅
  AS11: YES (confirmed)               ✅
  AS13: NO  (disagrees)               ❌
  AS15: YES (confirmed)               ✅
  AS17: NO  (disagrees)               ❌

STEP 4: Consensus Check
────────────────────────
Total votes: 9
YES votes: 6
NO votes: 3
Minimum required: 3 votes

Verdict: ATTACK_CONFIRMED (majority YES)
Confidence: 6/9 = 0.67 (67% agreement)

STEP 5: Execute Verdict
────────────────────────
1. Update AS666 rating: 50 → 30 (-20 penalty)
2. Award BGPCOIN:
   - AS01 (detector): +10 BGPCOIN
   - Correct voters (6 nodes): +2 BGPCOIN each
3. Save verdict to blockchain/attack_verdicts.jsonl
```

### **Consensus Thresholds**

```python
# From attack_consensus.py
self.min_votes = 3  # Same as transaction consensus

# Majority voting logic
if yes_votes > no_votes:
    verdict = "ATTACK_CONFIRMED"
    confidence = yes_votes / total_votes
elif no_votes > yes_votes:
    verdict = "NOT_ATTACK"
    confidence = no_votes / total_votes
else:
    verdict = "DISPUTED"
    confidence = 0.5
```

---

## 📊 Non-RPKI Rating System

**Location**: `nonrpki_rating.py`

### **Rating Scale**

```
Score Range    Level              Description
──────────────────────────────────────────────────────────
90-100         Highly Trusted     Nearly RPKI-level, consider adding ROA
70-89          Trusted            Good track record
50-69          Neutral            New or mixed history
30-49          Suspicious         Some attacks detected
0-29           Malicious          Confirmed attacker, block/filter
```

### **Initial Score**: 50 (Neutral)

### **Score Changes**

**PENALTIES (Instant)**:
```python
penalties = {
    "ip_prefix_hijacking": -20,
    "route_leak": -15,
    "repeated_attack": -30,      # Additional if within 30 days
    "persistent_attacker": -50   # 3+ total attacks
}
```

**REWARDS (Over Time)**:
```python
rewards = {
    "monthly_good_behavior": +5,
    "false_accusation_cleared": +2,
    "legitimate_announcements_100": +1,  # Per 100 announcements
    "highly_trusted_bonus": +10  # 90+ score for 3 months
}
```

### **Example Rating Changes**

```
AS666 Initial Score: 50 (Neutral)

Event 1: IP Prefix Hijacking detected
  Score: 50 → 30 (-20)
  Level: Neutral → Suspicious

Event 2: Second attack within 30 days
  Score: 30 → 0 (-20 base, -30 repeated = -50 total, capped at 0)
  Level: Suspicious → Malicious

Event 3: 3rd attack (persistent attacker)
  Score: Already at 0, remains 0
  Level: Malicious (permanent block recommended)
```

---

## 💰 BGPCOIN Rewards for Attack Detection

**Location**: `attack_consensus.py:331` (`_handle_confirmed_attack()`)

### **Reward Structure**

```python
rewards = {
    "attack_detection": 10,    # Detector gets 10 BGPCOIN
    "correct_vote": 2,         # Each correct voter gets 2 BGPCOIN
    "false_accusation": -20    # Penalty for false detection
}
```

### **Reward Distribution Examples**

**Scenario 1: Confirmed Attack**
```
AS01 detects IP hijacking
Vote result: 6 YES, 3 NO (CONFIRMED)

Rewards:
  AS01 (detector):         +10 BGPCOIN
  AS03 (correct YES vote): +2 BGPCOIN
  AS05 (correct YES vote): +2 BGPCOIN
  AS09 (correct YES vote): +2 BGPCOIN
  AS11 (correct YES vote): +2 BGPCOIN
  AS15 (correct YES vote): +2 BGPCOIN
  AS07 (incorrect NO vote): 0 BGPCOIN
  AS13 (incorrect NO vote): 0 BGPCOIN
  AS17 (incorrect NO vote): 0 BGPCOIN

Total distributed: 10 + (5 × 2) = 20 BGPCOIN
```

**Scenario 2: False Accusation**
```
AS17 falsely claims AS123 is attacking
Vote result: 2 YES, 7 NO (NOT_ATTACK)

Penalties & Rewards:
  AS17 (false accuser):    -20 BGPCOIN (penalty)
  AS01 (correct NO vote):  +2 BGPCOIN
  AS03 (correct NO vote):  +2 BGPCOIN
  AS05 (correct NO vote):  +2 BGPCOIN
  AS07 (correct NO vote):  +2 BGPCOIN
  AS09 (correct NO vote):  +2 BGPCOIN
  AS11 (correct NO vote):  +2 BGPCOIN
  AS13 (correct NO vote):  +2 BGPCOIN

Total: -20 + (7 × 2) = -6 BGPCOIN (net cost to system)
```

**Scenario 3: Disputed**
```
Vote result: 4 YES, 5 NO (TIE, DISPUTED)

Rewards:
  No rewards or penalties
  Verdict saved with confidence = 0.5
  Voter details preserved for transparency
```

---

## 📝 Attack Verdict Records

**Location**: `blockchain_data/chain/attack_verdicts.jsonl`

**Format**: JSON Lines (one verdict per line)

```json
{
  "verdict_id": "verdict_20251021_143530_123456",
  "proposal_id": "attack_20251021_143522",
  "transaction_id": "tx_20251021_143520",
  "timestamp": "2025-10-21T14:35:30.123456",
  "verdict": "ATTACK_CONFIRMED",
  "confidence": 0.67,
  "attack_type": "ip_prefix_hijacking",
  "attacker_as": 666,
  "votes": {
    "yes_count": 6,
    "no_count": 3,
    "total": 9,
    "voters": {
      "1": {"vote": "YES", "timestamp": "...", "confidence": 1.0},
      "3": {"vote": "YES", "timestamp": "...", "confidence": 1.0},
      "5": {"vote": "YES", "timestamp": "...", "confidence": 1.0},
      "7": {"vote": "NO",  "timestamp": "...", "confidence": 1.0},
      "9": {"vote": "YES", "timestamp": "...", "confidence": 1.0},
      "11": {"vote": "YES", "timestamp": "...", "confidence": 1.0},
      "13": {"vote": "NO",  "timestamp": "...", "confidence": 1.0},
      "15": {"vote": "YES", "timestamp": "...", "confidence": 1.0},
      "17": {"vote": "NO",  "timestamp": "...", "confidence": 1.0}
    }
  },
  "attack_details": {
    "attack_type": "ip_prefix_hijacking",
    "severity": "HIGH",
    "attacker_as": 666,
    "victim_prefix": "8.8.8.0/24",
    "legitimate_owner": 15169,
    "evidence": {
      "roa_authorized_as": 15169,
      "announcing_as": 666,
      "mismatch": true
    },
    "description": "AS666 claiming 8.8.8.0/24 but ROA shows AS15169",
    "detected_at": "2025-10-21T14:35:22.000000"
  }
}
```

---

## 🔄 Integration with Existing Systems

### **1. Transaction Flow Integration**

**Location**: `p2p_transaction_pool.py:456`

```python
def _commit_to_blockchain(self, transaction_id):
    """Commit approved transaction to blockchain"""

    # 1. Write transaction to blockchain
    success = self.blockchain.add_transaction_to_blockchain(transaction)

    if success:
        # 2. Award BGPCOIN for block commit (existing)
        self._award_bgpcoin_rewards(transaction_id, vote_data)

        # 3. Trigger attack detection (NEW)
        self._trigger_attack_detection(transaction, transaction_id)
```

### **2. P2P Message Handling**

**Location**: `p2p_transaction_pool.py:180`

```python
def _handle_client(self, client_socket):
    """Handle incoming P2P messages"""

    if message["type"] == "vote_request":
        self._handle_vote_request(message)
    elif message["type"] == "vote_response":
        self._handle_vote_response(message)
    elif message["type"] == "governance_proposal":
        self.governance.handle_proposal_message(message)
    elif message["type"] == "governance_vote":
        self.governance.handle_vote_message(message)
    elif message["type"] == "attack_proposal":      # NEW
        self.attack_consensus.handle_attack_proposal(message)
    elif message["type"] == "attack_vote":          # NEW
        self.attack_consensus.handle_attack_vote(message)
```

### **3. System Initialization**

**Location**: `p2p_transaction_pool.py:114`

```python
def start_p2p_server(self):
    """Start P2P server and initialize subsystems"""

    # 1. Initialize governance (existing)
    self.governance = GovernanceSystem(...)

    # 2. Initialize attack detection (NEW)
    attack_detector = AttackDetector(...)
    rating_system = NonRPKIRatingSystem(...)

    self.attack_consensus = AttackConsensus(
        as_number=self.as_number,
        attack_detector=attack_detector,
        rating_system=rating_system,
        bgpcoin_ledger=self.bgpcoin_ledger,
        p2p_pool=self,
        blockchain_dir=self.blockchain.blockchain_dir
    )
```

---

## 🎮 Usage Examples

### **Example 1: Legitimate Announcement**

```python
# BGP Announcement
announcement = {
    "sender_asn": 15169,           # Google
    "ip_prefix": "8.8.8.0/24",     # Google DNS
    "as_path": [15169, 1234, 5678]
}

# Attack Detection
attacks = attack_detector.detect_attacks(announcement)
# Result: [] (no attacks detected)

# Verdict: No attack proposal created
# Action: Normal transaction processing only
```

### **Example 2: IP Prefix Hijacking (Confirmed)**

```python
# BGP Announcement
announcement = {
    "sender_asn": 666,              # Malicious AS
    "ip_prefix": "8.8.8.0/24",      # Google's prefix
    "as_path": [666, 1234, 5678]
}

# Attack Detection
attacks = attack_detector.detect_attacks(announcement)
# Result: [{"attack_type": "ip_prefix_hijacking", ...}]

# Attack Consensus Voting
# Vote result: 6 YES, 3 NO (CONFIRMED)

# Actions:
# 1. AS666 rating: 50 → 30
# 2. Detector: +10 BGPCOIN
# 3. Correct voters: +2 BGPCOIN each
# 4. Verdict saved to attack_verdicts.jsonl
```

### **Example 3: Route Leak (Confirmed)**

```python
# BGP Announcement
announcement = {
    "sender_asn": 5,
    "ip_prefix": "203.0.113.0/24",
    "as_path": [5, 7, 5, 3, 1]  # AS5 leaked route from provider to peer
}

# Attack Detection
attacks = attack_detector.detect_attacks(announcement)
# Result: [{"attack_type": "route_leak", "leaker_as": 5, ...}]

# Attack Consensus Voting
# Vote result: 7 YES, 2 NO (CONFIRMED)

# Actions:
# 1. AS5 rating: 50 → 35 (-15)
# 2. Detector: +10 BGPCOIN
# 3. Correct voters: +2 BGPCOIN each
# 4. Verdict saved to attack_verdicts.jsonl
```

### **Example 4: False Accusation**

```python
# BGP Announcement (actually legitimate)
announcement = {
    "sender_asn": 123,
    "ip_prefix": "192.0.2.0/24",
    "as_path": [123, 456, 789]
}

# Node AS17 falsely detects attack (misconfigured ROA)
# Vote result: 2 YES, 7 NO (NOT_ATTACK)

# Actions:
# 1. AS17 (accuser): -20 BGPCOIN penalty
# 2. Correct NO voters: +2 BGPCOIN each
# 3. Verdict: NOT_ATTACK saved to blockchain
```

---

## 📈 Monthly Post-Hoc Analysis

**Location**: `behavioral_analysis.py`

**Integration**: Via governance consensus (66% approval required)

### **Rating Updates After Monthly Analysis**

```python
# RPKI ASes - Post-hoc analysis only
rpki_ases = [1, 3, 5, 7, 9, 11, 13, 15, 17]
# Monthly review of voting accuracy, participation
# BGPCOIN multiplier adjustments

# Non-RPKI ASes - Instant + Post-hoc
non_rpki_ases = [666, 123, 456, ...]
# Instant: Attack detection penalties
# Monthly: Good behavior rewards, long-term trends
```

**Example Monthly Analysis**:
```
AS666 Monthly Review:
  - Instant penalties: -40 (2 attacks this month)
  - No good behavior bonuses
  - Current score: 10 (Malicious)
  - Recommendation: Block/Filter

AS123 Monthly Review:
  - No attacks detected
  - Good behavior bonus: +5
  - 100 legitimate announcements: +1
  - Current score: 56 (Neutral)
```

---

## 🔒 Security Considerations

### **1. Sybil Attack Prevention**

```
Attacker creates 100 fake nodes:
  - Each has 0 BGPCOIN (no voting power for governance)
  - Can vote on attacks, but majority still needed
  - Cannot manipulate ratings without consensus
```

### **2. False Positive Mitigation**

```
Single node false detection:
  - Requires majority to confirm
  - Confidence score indicates certainty
  - DISPUTED verdicts preserved for review
  - False accuser penalized (-20 BGPCOIN)
```

### **3. Collusion Resistance**

```
5 malicious nodes collude:
  - Need 5/9 majority to confirm fake attack
  - Honest nodes (4) will vote NO
  - Result: DISPUTED or NOT_ATTACK
  - Malicious nodes don't get rewards
  - False accusers penalized
```

---

## 📚 API Reference

### **AttackDetector**

```python
from attack_detector import AttackDetector

detector = AttackDetector(
    roa_database_path="shared_data/roa_database.json",
    as_relationships_path="shared_data/as_relationships.json"
)

# Detect all attacks
attacks = detector.detect_attacks(announcement)

# Detect specific types
hijacking = detector.detect_ip_prefix_hijacking(announcement)
route_leak = detector.detect_route_leak(announcement)

# Add ROA entry
detector.add_roa_entry("8.8.8.0/24", authorized_as=15169)

# Add AS relationship
detector.add_as_relationship(1, customers=[2,3], providers=[], peers=[5,7])
```

### **NonRPKIRatingSystem**

```python
from nonrpki_rating import NonRPKIRatingSystem

rating_system = NonRPKIRatingSystem("blockchain_data/state")

# Record attack
rating_system.record_attack(
    as_number=666,
    attack_type="ip_prefix_hijacking",
    attack_details={"victim_prefix": "8.8.8.0/24"}
)

# Record good behavior
rating_system.record_good_behavior(
    as_number=123,
    behavior_type="monthly_good_behavior"
)

# Get rating
rating = rating_system.get_rating(666)
# Returns: {"trust_score": 30, "rating_level": "suspicious", ...}

# Get summary
summary = rating_system.get_summary()
# Returns: {"total_ases": 50, "by_level": {...}, ...}
```

### **AttackConsensus**

```python
from attack_consensus import AttackConsensus

consensus = AttackConsensus(
    as_number=1,
    attack_detector=detector,
    rating_system=rating_system,
    bgpcoin_ledger=ledger,
    p2p_pool=pool,
    blockchain_dir="blockchain_data/chain"
)

# Analyze announcement and propose if attack detected
consensus.analyze_and_propose_attack(announcement, transaction_id)

# Vote on attack proposal
consensus.vote_on_attack(proposal_id, vote="YES")

# Handle incoming proposals (automatic via P2P)
consensus.handle_attack_proposal(message)
consensus.handle_attack_vote(message)
```

---

## 🚀 Future Enhancements

### **1. Machine Learning Integration**

```python
# Train ML model on historical attack patterns
ml_detector = MLAttackDetector()
ml_detector.train(attack_verdicts_history)

# Combine with rule-based detection
combined_confidence = (
    rule_based_confidence * 0.6 +
    ml_confidence * 0.4
)
```

### **2. Real-Time ROA Updates**

```python
# Fetch latest ROAs from RPKI repositories
roa_updater = ROAUpdater()
roa_updater.sync_with_rpki_repositories()
roa_updater.verify_roa_signatures()
```

### **3. Advanced Reputation Metrics**

```python
# Consider AS age, size, history
reputation = calculate_reputation(
    trust_score=rating["trust_score"],
    as_age_years=10,
    prefix_count=1000,
    historical_accuracy=0.95
)
```

### **4. Automated Response Actions**

```python
# When rating drops below threshold
if rating["trust_score"] < 30:  # Suspicious
    actions.rate_limit(as_number, max_announcements=10)
    actions.require_additional_validation(as_number)

if rating["trust_score"] < 10:  # Malicious
    actions.block_announcements(as_number)
    actions.alert_operators(as_number, reason="persistent_attacker")
```

---

## 📖 References

- **Implementation**: `blockchain_utils/attack_*.py`
- **ROA Database**: [RPKI ROA Format](https://www.rfc-editor.org/rfc/rfc6482.html)
- **Valley-Free Routing**: [Gao's Algorithm](https://dl.acm.org/doi/10.1109/90.851975)
- **BGP Security**: [NIST BGP Security Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-54.pdf)

---

**BGP-Sentry: Decentralized BGP Attack Detection with Blockchain Consensus**
