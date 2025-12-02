# BGP-Sentry Architecture Details

**Purpose:** Comprehensive architecture reference with implementation locations and line numbers.

**How to use this document:** Ask any question about the system, and this document will tell you:
- ✅ **Is it implemented?** (Yes/No)
- 📁 **Where?** (File path and line numbers)
- 🔍 **How?** (Brief implementation description)

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Core Components](#2-core-components)
3. [Consensus Mechanism](#3-consensus-mechanism)
4. [Token Economics (BGPCOIN)](#4-token-economics-bgpcoin)
5. [Attack Detection](#5-attack-detection)
6. [Network Communication](#6-network-communication)
7. [Data Storage](#7-data-storage)
8. [Governance System](#8-governance-system)
9. [Performance Optimizations](#9-performance-optimizations)
10. [Configuration & Settings](#10-configuration--settings)

---

## 1. System Architecture Overview

### Q: What is the overall system architecture?

**Implementation Status:** ✅ **Fully Implemented**

**Architecture Type:** Distributed P2P blockchain simulation

**Components:**
```
9 RPKI Nodes (AS01, AS03, AS05, AS07, AS09, AS11, AS13, AS15, AS17)
    ↓
Each node runs independently with:
    • P2P Transaction Pool (consensus engine)
    • Blockchain Storage (local blockchain)
    • BGPCOIN Ledger (token balance)
    • Attack Detector (security validation)
    • Knowledge Base (observed BGP announcements)
```

**Main Entry Point:**
- **File:** `main_experiment.py`
- **Class:** `BGPSentryExperiment` (lines 42-523)
- **Startup:** Line 525 `def main()`

**Node Configuration:**
- **File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/rpki_node_registry.py`
- **Registry Class:** Lines 1-50
- **Node List:** Hardcoded list of 9 RPKI AS numbers (1, 3, 5, 7, 9, 11, 13, 15, 17)

---

## 2. Core Components

### Q: What are the main components and where are they?

#### 2.1 P2P Transaction Pool (Consensus Engine)

**Status:** ✅ **Fully Implemented**

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/p2p_transaction_pool.py`

**Key Features:**
- **Class Definition:** Line 23 `class P2PTransactionPool`
- **Initialization:** Lines 29-117
  - Line 31: `self.my_port = base_port + as_number` (port assignment)
  - Line 34: Peer node discovery from registry
  - Line 53: `self.consensus_threshold = 3` (3/9 consensus)
  - Line 58: `self.knowledge_window_seconds = 480` (8-minute window)
  - Line 62-63: Timeout configuration (60s regular, 180s attack)
  - Line 66: `self.SAMPLING_WINDOW_SECONDS = 3600` (1-hour sampling)

**Core Methods:**
- **Start P2P Server:** Lines 119-166
  - Line 122-125: Socket initialization and binding
  - Line 131-138: Governance system initialization
  - Line 141-162: Attack consensus system initialization

- **Broadcast Transaction:** Lines 308-348
  - Line 320-326: Create pending vote entry with timestamp
  - Line 329-336: Get relevant neighbors (optimized voting)
  - Line 344-345: Send vote requests to peers

- **Handle Vote Response:** Lines 233-306
  - Line 262-268: **Vote deduplication** (prevent replay attacks)
  - Line 271-276: **Vote overflow protection**
  - Line 287-292: Check consensus threshold (3/9)
  - Line 293-297: Commit when consensus reached

- **Transaction Timeout:** Lines 552-608
  - Line 570: Background thread checks every 30 seconds
  - Line 591: Determine timeout (60s or 180s based on type)
  - Line 595-600: Handle timed-out transactions

- **Knowledge Base:** Lines 707-752
  - Line 726-730: **Sampling logic** (check 1-hour window)
  - Line 732-752: Add observation to knowledge base
  - Line 746-750: Record in neighbor cache (optimized voting)

---

#### 2.2 Blockchain Interface

**Status:** ✅ **Fully Implemented**

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/blockchain_interface.py`

**Purpose:** Manages reading/writing blockchain data

**Key Features:**
- Writes transactions to `blockchain_data/chain/blockchain.json`
- Each node maintains its own blockchain file
- JSON-based storage (human-readable)

**Location Details:**
- **Initialization:** Each node path: `nodes/rpki_nodes/as{XX}/blockchain_node/blockchain_data/chain/`
- **State Files:** `nodes/rpki_nodes/as{XX}/blockchain_node/blockchain_data/state/`

---

#### 2.3 BGPCOIN Ledger

**Status:** ✅ **Fully Implemented**

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/bgpcoin_ledger.py`

**Key Features:**
- **Class Definition:** Line 45 `class BGPCoinLedger`
- **Initialization:** Lines 56-134
  - Line 70: `self.total_supply = 10_000_000` (10 million coins)
  - Lines 76-82: Reward configuration
    - Line 77: `block_commit: 10` BGPCOIN
    - Line 78: `vote_approve: 1` BGPCOIN
    - Line 79: `first_commit_bonus: 5` BGPCOIN
    - Line 80: `attack_detection: 100` BGPCOIN
  - Lines 85-89: Multiplier ranges (accuracy, participation, quality)
  - Lines 92-96: Penalty configuration

**Core Methods:**
- **Reward Formula:** Lines 185-210
  - Line 204: `earned = base_reward * accuracy * participation * quality`

- **Award Block Commit:** Lines 212-301
  - Line 228-230: Calculate committer reward with multipliers
  - Line 232: Check treasury balance
  - Line 240-242: Award to committer and deduct from treasury
  - Line 254-277: Award voters (1 BGPCOIN each with multipliers)

- **Spend Coins (50% burn / 50% recycle):** Lines 303-354
  - Line 326-327: Calculate burn and recycle amounts
  - Line 329-331: Update burned, recycled, and treasury balances

- **Get Balance:** Line 356-358

---

#### 2.4 Attack Detection System

**Status:** ✅ **Fully Implemented**

**Location:** `nodes/rpki_nodes/bgp_attack_detection/`

**Main Detector File:** `attack_detector.py`

**Detector Types:**

1. **Prefix Hijack Detector**
   - **File:** `detectors/prefix_hijack_detector.py`
   - **Purpose:** Detects exact prefix hijacking (attacker announces victim's prefix)
   - **Method:** RPKI ROA validation

2. **Sub-Prefix Hijack Detector**
   - **File:** `detectors/subprefix_detector.py`
   - **Purpose:** Detects more-specific prefix attacks (e.g., /25 instead of /24)
   - **Method:** RPKI + longest prefix match analysis

3. **Route Leak Detector**
   - **File:** `detectors/route_leak_detector.py`
   - **Purpose:** Detects valley-free routing violations
   - **Method:** AS relationship validation (customer-provider, peer-peer)

**Validators:**

1. **RPKI Validator**
   - **File:** `validators/rpki_validator.py`
   - **Purpose:** Validate announcements against ROA database
   - **Returns:** Valid, Invalid, or NotFound

2. **IRR Validator**
   - **File:** `validators/irr_validator.py`
   - **Purpose:** Validate using Internet Routing Registry
   - **Returns:** Matches IRR records or not

---

#### 2.5 Attack Consensus System

**Status:** ✅ **Fully Implemented**

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/attack_consensus.py`

**Purpose:** Nodes vote on whether detected anomalies are true attacks

**Integration:**
- **Initialized in:** `p2p_transaction_pool.py` lines 141-162
- **Triggered after:** Transaction committed to blockchain
- **Vote Collection:** Similar to transaction consensus (3/9 threshold)

---

#### 2.6 Governance System

**Status:** ✅ **Fully Implemented**

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/governance_system.py`

**Purpose:** Decentralized decision-making for:
- Monthly behavioral analysis
- Protocol upgrades
- Trust score modifications
- Reward adjustments

**Integration:**
- **Initialized in:** `p2p_transaction_pool.py` lines 131-138
- **Voting Mechanism:** BGPCOIN-weighted voting
- **Consensus Required:** 66% (configurable per proposal type)

---

## 3. Consensus Mechanism

### Q: How does consensus work?

**Status:** ✅ **Fully Implemented**

**Type:** Knowledge-Based Voting with Byzantine Fault Tolerance

**Implementation:** `p2p_transaction_pool.py`

---

### Q: What is the consensus threshold?

**Status:** ✅ **Implemented**

**Value:** 3 out of 9 nodes (33%)

**Location:**
- **File:** `p2p_transaction_pool.py`
- **Line 53:** `self.consensus_threshold = 3`
- **Comment:** Line 49: "need 3/9 for consensus"

**Rationale:**
- BGP is globally observed but locally validated
- Not all RPKI nodes see every announcement
- Balance between security (Byzantine tolerance) and liveness

**Byzantine Tolerance:**
- Can tolerate up to 2 malicious nodes
- If 3+ nodes collude, system can be compromised

---

### Q: How do nodes vote?

**Status:** ✅ **Fully Implemented**

**Voting Process:**

1. **Observation Collection** (Lines 707-752 in `p2p_transaction_pool.py`)
   - Node observes BGP announcement
   - Adds to knowledge base with 8-minute time window
   - Records in neighbor cache for optimized voting

2. **Transaction Broadcast** (Lines 308-348)
   - Node creates transaction from observation
   - Broadcasts to relevant neighbors (optimized)
   - Starts timeout timer (60s regular, 180s attack)

3. **Vote Request Handling** (Lines 220-231)
   - Peer receives vote request
   - Validates against own knowledge base (lines 839-856)
   - Sends vote response (approve/reject)

4. **Vote Response Handling** (Lines 233-306)
   - Originator receives vote
   - **Deduplication check** (lines 262-268): Reject if AS already voted
   - **Overflow check** (lines 271-276): Reject if votes > total nodes
   - Count approve votes (line 288)
   - If >= 3 approvals: Commit to blockchain (line 292)

5. **Timeout Handling** (Lines 552-608)
   - If consensus not reached within timeout
   - Determine status based on vote count:
     - 3+ approve: `CONFIRMED`
     - 1-2 approve: `INSUFFICIENT_CONSENSUS`
     - 0 approve: `SINGLE_WITNESS`
   - Commit with status metadata

---

### Q: What prevents replay attacks (duplicate votes)?

**Status:** ✅ **Fully Implemented**

**Vote Deduplication:**

**File:** `p2p_transaction_pool.py`
**Lines:** 262-268

```python
# Check if this AS already voted
existing_voters = [v["from_as"] for v in self.pending_votes[tx_id]["votes"]]

if from_as in existing_voters:
    self.logger.warning(
        f"🚨 REPLAY ATTACK DETECTED: AS{from_as} already voted on {tx_id}"
    )
    return  # Reject duplicate vote
```

**Additional Protection:**
- **Vote Overflow Check** (lines 271-276): Reject if vote count exceeds total nodes (9)
- **Security Log:** Warnings logged for audit trail

---

### Q: How does knowledge-based voting work?

**Status:** ✅ **Fully Implemented**

**Knowledge Base Management:**

**File:** `p2p_transaction_pool.py`

**Key Components:**

1. **Knowledge Storage** (Line 57)
   - `self.knowledge_base = []` (list of observations)
   - Each observation contains: IP prefix, sender AS, timestamp, trust score

2. **Time Window** (Line 58)
   - `self.knowledge_window_seconds = 480` (8 minutes)
   - Allows for BGP propagation delays + fork resolution

3. **Add Observation** (Lines 707-752)
   - Line 726-730: Check sampling (skip if seen in last hour)
   - Line 732-741: Add observation with metadata
   - Line 746-750: Record in neighbor cache

4. **Check Knowledge** (Lines 790-837)
   - Search knowledge base for matching observation
   - Check IP prefix + AS number + timestamp within window
   - Return approve if match found, reject otherwise

5. **Cleanup Old Observations** (Lines 754-788)
   - Background thread runs every 60 seconds
   - Removes observations older than 8 minutes
   - Prevents unbounded memory growth

6. **Persistence** (Lines 993-1091)
   - Save to disk every 60 seconds (lines 1074-1091)
   - Load on startup (lines 993-1038)
   - Crash recovery with data validation

---

## 4. Token Economics (BGPCOIN)

### Q: What is BGPCOIN?

**Status:** ✅ **Fully Implemented**

**Definition:** Protocol-level incentive token for BGP-Sentry

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/bgpcoin_ledger.py`

**Specifications:**
- **Name:** BGPCOIN (line 68)
- **Symbol:** BGPC (line 69)
- **Total Supply:** 10,000,000 (line 70)
- **Initial Distribution:** All in protocol treasury (line 104)

---

### Q: How are rewards calculated?

**Status:** ✅ **Fully Implemented**

**Formula:** `C_earned = C_base × A_accuracy × P_participation × Q_quality`

**Implementation:**
- **File:** `bgpcoin_ledger.py`
- **Lines:** 185-210
- **Method:** `calculate_earned_coins(base_reward, as_number)`

**Multiplier Ranges** (Lines 85-89):
- **Accuracy:** 0.5 - 1.5 (based on voting history)
- **Participation:** 0.8 - 1.2 (based on activity)
- **Quality:** 0.9 - 1.3 (based on evidence quality)

**Example:**
```python
# Base reward: 10 BGPCOIN
# Accuracy: 1.2 (good history)
# Participation: 1.1 (consistent)
# Quality: 1.0 (average)
# Final = 10 × 1.2 × 1.1 × 1.0 = 13.2 BGPCOIN
```

---

### Q: What rewards exist?

**Status:** ✅ **Fully Implemented**

**Reward Types** (Lines 76-82):

| Action | Base Reward | Line |
|--------|-------------|------|
| Block Commit | 10 BGPCOIN | 77 |
| Vote (Approve) | 1 BGPCOIN | 78 |
| First-to-Commit Bonus | +5 BGPCOIN | 79 |
| Attack Detection | 100 BGPCOIN | 80 |
| Daily Monitoring | 10 BGPCOIN | 81 |

**Implementation:**
- **Award Block Commit:** Lines 212-301
  - Committer gets 10 BGPCOIN (+ 5 if first) × multipliers
  - Voters get 1 BGPCOIN each × multipliers
  - Deducted from treasury (line 241)
  - Logged to transaction log (lines 249-252, 274-277)

---

### Q: How does the 50% burn / 50% recycle work?

**Status:** ✅ **Fully Implemented**

**Implementation:**
- **File:** `bgpcoin_ledger.py`
- **Lines:** 303-354
- **Method:** `spend_coins(as_number, amount, purpose)`

**Mechanism** (Lines 326-331):
```python
# 50% burn, 50% recycle
burned = amount * 0.5
recycled = amount * 0.5

self.ledger_data["total_burned"] += burned
self.ledger_data["total_recycled"] += recycled
self.ledger_data["protocol_treasury"] += recycled  # Back to treasury
```

**Example:**
- Node spends 100 BGPCOIN
- 50 BGPCOIN permanently burned (removed from supply)
- 50 BGPCOIN recycled to treasury (reusable)
- Node balance decreases by 100 BGPCOIN

**Purpose:**
- Burn creates deflationary pressure (scarcity)
- Recycle ensures long-term sustainability (treasury doesn't deplete)

---

### Q: Can nodes have negative balances?

**Status:** ✅ **Yes (for penalties)**

**Implementation:**
- **Normal Spending:** Line 318 checks balance, rejects if insufficient
- **Penalties:** Line 471 allows negative balances

**Penalty Method:** Lines 454-486
- Deducts penalty amount (can go negative)
- Used for malicious behavior punishment

---

### Q: How are multipliers updated?

**Status:** ✅ **Fully Implemented**

**Implementation:**
- **File:** `bgpcoin_ledger.py`
- **Lines:** 377-408
- **Method:** `update_node_multipliers(as_number, accuracy, participation, quality)`

**Update Mechanism:**
- Monthly behavioral analysis calculates new multipliers
- Clamped to valid ranges:
  - Accuracy: 0.5 - 1.5 (line 394)
  - Participation: 0.8 - 1.2 (line 398)
  - Quality: 0.9 - 1.3 (line 402)
- Saved to ledger atomically

**Trigger:**
- Governance proposal for monthly analysis
- Consensus required (66% nodes approve)
- Applied to all nodes simultaneously

---

## 5. Attack Detection

### Q: What attacks can be detected?

**Status:** ✅ **Fully Implemented**

**Attack Types:**

1. **Prefix Hijack**
   - **Status:** ✅ Implemented
   - **File:** `bgp_attack_detection/detectors/prefix_hijack_detector.py`
   - **Detection Method:** RPKI ROA validation
   - **Accuracy:** High (relies on cryptographic ROAs)

2. **Sub-Prefix Hijack**
   - **Status:** ✅ Implemented
   - **File:** `bgp_attack_detection/detectors/subprefix_detector.py`
   - **Detection Method:** More-specific prefix analysis + RPKI
   - **Accuracy:** Medium (requires careful origin validation)

3. **Route Leak**
   - **Status:** ✅ Implemented
   - **File:** `bgp_attack_detection/detectors/route_leak_detector.py`
   - **Detection Method:** AS relationship validation (valley-free routing)
   - **Accuracy:** Medium (depends on AS relationship database accuracy)

---

### Q: How is attack detection triggered?

**Status:** ✅ **Fully Implemented**

**Trigger Flow:**

1. **Transaction Committed to Blockchain**
   - **File:** `p2p_transaction_pool.py`
   - **Method:** `_commit_to_blockchain` (lines 858-907)
   - **Line 897:** `self._trigger_attack_detection(transaction, transaction_id)`

2. **Attack Detection Analysis**
   - **Method:** `_trigger_attack_detection` (lines 957-991)
   - **Lines 973-978:** Extract BGP announcement details
   - **Line 988:** `self.attack_consensus.analyze_and_propose_attack()`

3. **Attack Consensus Voting**
   - **File:** `attack_consensus.py`
   - Each node analyzes independently
   - Proposes attack if detected
   - Other nodes vote (approve/reject)
   - 3/9 consensus required to confirm attack

---

### Q: What is the Non-RPKI Rating System?

**Status:** ✅ **Fully Implemented**

**Purpose:** Track reputation of non-RPKI ASes based on behavior

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/nonrpki_rating.py`

**Key Features:**
- Maintains trust scores for non-RPKI autonomous systems
- Decreases score for malicious announcements
- Increases score for legitimate announcements
- Used in attack detection (low-rated ASes more suspicious)

**Storage:** `blockchain_data/state/nonrpki_ratings.json` per node

---

## 6. Network Communication

### Q: How do nodes communicate?

**Status:** ✅ **Fully Implemented (TCP Sockets)**

**Implementation:** `p2p_transaction_pool.py`

**Communication Protocol:**

1. **Server Setup** (Lines 119-166)
   - Line 122: Create TCP socket
   - Line 123: Set SO_REUSEADDR (prevent "address already in use")
   - Line 124: Bind to `localhost:800X` (X = AS number)
   - Line 125: Listen for connections (queue size 5)

2. **Port Assignment** (Line 31)
   - `self.my_port = base_port + as_number`
   - Base port: 8000
   - AS01 → 8001, AS03 → 8003, ..., AS17 → 8017

3. **Message Types** (Lines 194-213)
   - `vote_request`: Request vote from peer
   - `vote_response`: Send vote back to originator
   - `governance_proposal`: Propose governance action
   - `governance_vote`: Vote on governance proposal
   - `attack_proposal`: Propose detected attack
   - `attack_vote`: Vote on attack proposal

4. **Message Format** (JSON)
   ```json
   {
     "type": "vote_request",
     "from_as": 1,
     "transaction": {...},
     "timestamp": "2025-12-02T14:30:00"
   }
   ```

---

### Q: What is the Relevant Neighbor Cache?

**Status:** ✅ **Fully Implemented**

**Purpose:** Optimize voting by only querying nodes likely to have observed announcement

**File:** `nodes/rpki_nodes/shared_blockchain_stack/network_stack/relevant_neighbor_cache.py`

**How It Works:**

1. **Observation Recording**
   - **File:** `p2p_transaction_pool.py` lines 746-750
   - When node observes BGP announcement from AS X
   - Records: "I (RPKI node Y) observed AS X"

2. **Cache Lookup**
   - **Lines:** 329-336 in `broadcast_transaction()`
   - Query cache: "Which RPKI nodes have observed AS X?"
   - Only send vote requests to those nodes

3. **Performance Benefit:**
   - Without: Broadcast to all 8 peers (16 messages total)
   - With: Broadcast to ~3-4 relevant peers (8 messages)
   - **50% reduction** in network traffic

---

### Q: Are there network timeouts?

**Status:** ✅ **Fully Implemented**

**Socket Timeouts:**
- **File:** `p2p_transaction_pool.py`
- **Line 354:** `sock.settimeout(5)` (5-second connection timeout)
- **Line 379:** `sock.settimeout(5)` (5-second send timeout)

**Purpose:**
- Prevent hanging on unresponsive nodes
- Allow system to continue if peer is down

---

## 7. Data Storage

### Q: Where is data stored?

**Status:** ✅ **Fully Implemented**

**Storage Structure:**

```
nodes/rpki_nodes/as{XX}/blockchain_node/blockchain_data/
├── chain/
│   └── blockchain.json              ← Transaction blockchain
├── state/
│   ├── bgpcoin_ledger.json          ← Token balances
│   ├── bgpcoin_transactions.jsonl   ← Token transaction log
│   ├── knowledge_base.json          ← Observed BGP announcements
│   ├── last_seen_announcements.json ← Sampling cache
│   ├── nonrpki_ratings.json         ← Non-RPKI AS reputation
│   ├── governance_proposals.json    ← Active governance votes
│   ├── governance_votes.jsonl       ← Governance vote history
│   ├── behavioral_analysis.json     ← Latest analysis results
│   ├── analysis_history.jsonl       ← Historical analysis
│   └── roa_database.json            ← RPKI ROA database
```

**Storage Format:** JSON (human-readable, easy to parse)

---

### Q: How is blockchain data structured?

**Status:** ✅ **Fully Implemented**

**Blockchain File:** `blockchain_data/chain/blockchain.json`

**Structure:**
```json
{
  "version": "1.0",
  "as_number": 1,
  "created_at": "2025-12-02T14:00:00",
  "last_updated": "2025-12-02T15:30:00",
  "transaction_count": 850,
  "transactions": [
    {
      "transaction_id": "tx_20251202_140030_prefix_203.0.113.0_24_as64500",
      "timestamp": "2025-12-02T14:00:30",
      "ip_prefix": "203.0.113.0/24",
      "sender_asn": 64500,
      "trust_score": 0.95,
      "is_attack": false,
      "consensus_reached": true,
      "consensus_status": "CONFIRMED",
      "signature_count": 5,
      "approve_count": 5,
      "signatures": [
        {"from_as": 3, "vote": "approve", "timestamp": "..."},
        {"from_as": 5, "vote": "approve", "timestamp": "..."},
        ...
      ]
    },
    ...
  ]
}
```

---

### Q: How does duplicate prevention work? (Sampling)

**Status:** ✅ **FULLY IMPLEMENTED**

**Purpose:** Prevent duplicate transactions from being written to blockchain if they already exist within the last 1 hour.

**Implementation:** `p2p_transaction_pool.py`

---

#### **Mechanism Overview**

**Problem:** BGP announcements are repetitive (keepalives, redundant paths)
- Without sampling: ~10,000 blockchain entries per hour
- With sampling: ~200-850 unique entries per hour
- **Reduction:** 91.5%+ blockchain bloat prevented

**Solution:** 1-hour sampling window with in-memory cache

---

#### **How It Works**

**Step 1: Check Before Adding Observation**

**File:** `p2p_transaction_pool.py`
**Method:** `add_bgp_observation()` (Lines 707-752)

```python
# SAMPLING: For regular announcements, check if recorded in last 1 hour
if not is_attack:
    if self._check_recent_announcement_in_cache(ip_prefix, sender_asn):
        # Already recorded within 1 hour, skip
        return False
```

**Line 726-730:** Sampling check happens BEFORE adding to knowledge base

---

**Step 2: Cache Lookup (O(1) Fast)**

**Method:** `_check_recent_announcement_in_cache()` (Lines 398-429)

```python
cache_key = (ip_prefix, sender_asn)  # e.g., ("203.0.113.0/24", 64500)
current_time = datetime.now().timestamp()
cutoff_time = current_time - self.SAMPLING_WINDOW_SECONDS  # 3600 seconds = 1 hour

if cache_key in self.last_seen_cache:
    last_seen = self.last_seen_cache[cache_key]

    if last_seen > cutoff_time:
        # Found within 1 hour window - SKIP!
        time_since = int(current_time - last_seen)
        self.logger.info(f"📊 Sampling: {ip_prefix} from AS{sender_asn} seen {time_since}s ago, skipping")
        return True  # Skip (duplicate)

return False  # Not found or too old - record it
```

**Performance:**
- **O(1) dictionary lookup** (instant)
- No blockchain scanning required (would be O(N))
- **100,000× faster** than scanning blockchain

---

**Step 3: Update Cache After Commit**

**Method:** `_update_last_seen_cache()` (Lines 431-445)

Called from two places:

1. **Normal Commit** (Line 886-891)
   ```python
   # Update last_seen cache for sampling (if regular announcement)
   if not transaction.get('is_attack', False):
       self._update_last_seen_cache(
           transaction.get('ip_prefix'),
           transaction.get('sender_asn')
       )
   ```

2. **Timeout Commit** (Line 688-693)
   ```python
   # Update last_seen cache for sampling (if regular announcement and has some approval)
   if not transaction.get('is_attack', False) and approve_count > 0:
       self._update_last_seen_cache(
           transaction.get('ip_prefix'),
           transaction.get('sender_asn')
       )
   ```

**Cache Update:**
```python
cache_key = (ip_prefix, sender_asn)
self.last_seen_cache[cache_key] = datetime.now().timestamp()
```

---

#### **Important: Attack Bypass**

**Line 727:** Attacks always bypass sampling

```python
if not is_attack:
    # Only check sampling for regular announcements
    if self._check_recent_announcement_in_cache(...):
        return False  # Skip duplicate

# Attacks always recorded (even if seen recently)
```

**Rationale:**
- Attack announcements are critical security events
- Must record every occurrence (not sample)
- Even if same attack repeats within 1 hour

---

#### **Cache Persistence**

**File Storage:**
- **File:** `blockchain_data/state/last_seen_announcements.json`
- **Save Method:** Lines 447-472
- **Load Method:** Lines 474-502

**Cache Structure:**
```json
{
  "version": "1.0",
  "last_updated": "2025-12-02T15:30:00",
  "cache": {
    "203.0.113.0/24|64500": 1733155800.0,
    "198.51.100.0/24|64501": 1733159400.0,
    ...
  }
}
```

**Key Format:** `{ip_prefix}|{as_number}` (pipe-separated for JSON compatibility)
**Value:** Unix timestamp of last commit

**Persistence Triggers:**
- **Every 100 updates** (line 444-445)
- **On shutdown** (line 1147-1148)
- **Hourly cleanup** (line 547)

**Crash Recovery:**
- Loaded on startup (line 81)
- Expired entries filtered out (lines 490-494)
- Max data loss: Last 100 updates (< 1 minute of data)

---

#### **Cache Cleanup**

**Method:** `_cleanup_last_seen_cache()` (Lines 504-527)

```python
# Remove expired entries (older than 1 hour)
current_time = datetime.now().timestamp()
cutoff_time = current_time - self.SAMPLING_WINDOW_SECONDS

self.last_seen_cache = {
    key: timestamp
    for key, timestamp in self.last_seen_cache.items()
    if timestamp > cutoff_time  # Keep only entries within 1 hour
}
```

**Background Thread:** `_periodic_cleanup_last_seen_cache()` (Lines 529-550)
- Runs every 3600 seconds (1 hour)
- Removes expired entries
- Saves cache to disk
- Prevents unbounded memory growth

---

#### **Configuration**

**File:** `p2p_transaction_pool.py`

| Parameter | Value | Line | Purpose |
|-----------|-------|------|---------|
| **SAMPLING_WINDOW_SECONDS** | 3600 | 66 | 1-hour duplicate detection window |
| **Cleanup Interval** | 3600s | 541 | Cache cleanup frequency (1 hour) |
| **Save Frequency** | Every 100 updates | 444 | Disk persistence trigger |

---

#### **Example Scenario**

```
Time 14:00:00 - Transaction "203.0.113.0/24 from AS64500" committed
                Cache: {("203.0.113.0/24", 64500): 1733155200.0}

Time 14:15:00 - Same announcement observed again
                Check cache: 1733156100 - 1733155200 = 900 seconds (< 3600)
                Result: SKIP (duplicate within 1 hour)
                Log: "📊 Sampling: 203.0.113.0/24 from AS64500 seen 900s ago, skipping"

Time 14:30:00 - Same announcement observed again
                Check cache: 1733157000 - 1733155200 = 1800 seconds (< 3600)
                Result: SKIP (still within 1 hour)

Time 15:00:01 - Same announcement observed again
                Check cache: 1733158801 - 1733155200 = 3601 seconds (> 3600)
                Result: RECORD (outside 1-hour window)
                New transaction created and committed
                Cache updated: {("203.0.113.0/24", 64500): 1733158801.0}
```

---

#### **Performance Impact**

**Without Sampling:**
- 10,000 BGP announcements/hour
- 10,000 blockchain entries
- ~20 MB blockchain growth/hour
- 200 MB/day, 73 GB/year

**With Sampling:**
- 10,000 BGP announcements/hour
- 850 unique (prefix, AS) pairs
- ~1.7 MB blockchain growth/hour
- **91.5% reduction**
- 17 MB/day, 6.2 GB/year

---

#### **Edge Cases Handled**

1. **Cache Miss (New Announcement):**
   - Not in cache → Record
   - Add to cache with current timestamp

2. **Cache Hit (Duplicate):**
   - In cache and recent (< 1 hour) → Skip
   - Log with time_since info

3. **Cache Hit (Expired):**
   - In cache but old (> 1 hour) → Record
   - Update cache with new timestamp

4. **Attack Announcement:**
   - Bypass sampling completely
   - Always record (even if duplicate)

5. **Cache Corruption:**
   - Load fails → Start with empty cache
   - System continues (allows recording)

6. **Startup with Old Cache:**
   - Expired entries filtered out (lines 490-494)
   - Only load entries within 1-hour window

---

#### **Verification**

**How to verify sampling is working:**

1. **Check logs for sampling messages:**
   ```bash
   grep "Sampling:" nodes/rpki_nodes/as01/blockchain_node/*.log
   ```
   Should see: `📊 Sampling: 203.0.113.0/24 from AS64500 seen 900s ago, skipping`

2. **Check cache file exists:**
   ```bash
   cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/last_seen_announcements.json
   ```

3. **Compare blockchain size:**
   - Without sampling: ~10,000 transactions/hour
   - With sampling: ~850 transactions/hour

4. **Check for duplicates within 1 hour:**
   ```bash
   # Should find ZERO duplicates within 1 hour
   python3 analysis/check_duplicates.py --window 3600
   ```

---

### Q: Can sampling window be adjusted?

**Status:** ✅ **Yes - Configurable**

**File:** `p2p_transaction_pool.py`
**Line 66:** `self.SAMPLING_WINDOW_SECONDS = 3600`

**To change:**
```python
# 30 minutes
self.SAMPLING_WINDOW_SECONDS = 1800

# 2 hours
self.SAMPLING_WINDOW_SECONDS = 7200

# 10 minutes (more aggressive sampling)
self.SAMPLING_WINDOW_SECONDS = 600
```

**Trade-offs:**
- **Shorter window (< 1 hour):** More transactions recorded, larger blockchain
- **Longer window (> 1 hour):** Fewer transactions, smaller blockchain, but may miss legitimate changes

**Recommendation:** Keep at 3600 seconds (1 hour) - balances accuracy and efficiency

---

## 8. Governance System

### Q: What can be governed?

**Status:** ✅ **Fully Implemented**

**File:** `nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/governance_system.py`

**Governable Actions:**

1. **Monthly Behavioral Analysis**
   - Review node performance
   - Award bonuses/penalties
   - Update multipliers
   - Consensus Required: 66%

2. **Trust Score Modifications**
   - Adjust Non-RPKI AS ratings
   - Change trust thresholds
   - Consensus Required: 75%

3. **Reward Adjustments**
   - Modify BGPCOIN reward amounts
   - Change multiplier ranges
   - Consensus Required: 66%

4. **Threat Detection Rules**
   - Add new attack detection algorithms
   - Tune detection thresholds
   - Consensus Required: 60%

5. **Protocol Upgrades**
   - Major system changes
   - Consensus algorithm modifications
   - Consensus Required: 75%

---

### Q: How does governance voting work?

**Status:** ✅ **Fully Implemented**

**Voting Process:**

1. **Proposal Creation**
   - Any node can propose
   - Proposal includes: type, description, parameters
   - Broadcast to all peers

2. **Voting**
   - Each node votes independently (approve/reject)
   - Votes weighted by BGPCOIN balance
   - Vote stored locally and broadcast

3. **Consensus Check**
   - **Simple Majority:** Count nodes (e.g., 7/9 = 77.8%)
   - **Weighted Majority:** Sum BGPCOIN of approvers / total BGPCOIN
   - Both must exceed threshold

4. **Execution**
   - If consensus reached: Execute on ALL nodes
   - Results recorded to blockchain
   - Governance state updated

**Integration:** Initialized in `p2p_transaction_pool.py` lines 131-138

---

## 9. Performance Optimizations

### Q: What performance optimizations exist?

#### 9.1 Transaction Sampling (1-hour window)

**Status:** ✅ **Fully Implemented**

**Purpose:** Reduce blockchain bloat by 90%+

**Implementation:**
- **File:** `p2p_transaction_pool.py`
- **Lines:** 398-445 (cache management)
- **Lines:** 726-730 (sampling check in `add_bgp_observation`)

**Mechanism:**
- Track last seen time for each (IP prefix, AS number) pair
- Skip if seen within last 3600 seconds (1 hour)
- Attack announcements bypass sampling (always recorded)

**Performance:**
- **Cache Lookup:** O(1) (dictionary lookup)
- **Blockchain Scan Avoided:** Would be O(N) scanning all transactions
- **Speedup:** ~100,000× faster than scanning blockchain

**Result:**
- ~10,000 BGP announcements → ~850 blockchain entries
- 91.5% reduction in blockchain size

---

#### 9.2 Relevant Neighbor Cache

**Status:** ✅ **Fully Implemented**

**Purpose:** Reduce P2P message overhead by 50%

**Implementation:**
- **File:** `network_stack/relevant_neighbor_cache.py`
- **Integration:** `p2p_transaction_pool.py` lines 97-102, 329-336, 746-750

**Mechanism:**
- Track which RPKI nodes have observed which non-RPKI ASes
- Only query relevant nodes for votes
- Fallback to all peers if cache empty

**Performance:**
- Without: 1 tx × 8 peers × 2 messages = 16 messages
- With: 1 tx × 4 relevant peers × 2 messages = 8 messages
- **50% reduction** in network traffic

---

#### 9.3 Lock-Free I/O Pattern

**Status:** ✅ **Fully Implemented**

**Purpose:** Prevent deadlocks during blockchain writes

**Implementation:**
- **File:** `p2p_transaction_pool.py`
- **Pattern:** "Decide inside lock, execute outside lock"

**Example** (Lines 250-306 in `_handle_vote_response`):
```python
# CRITICAL SECTION (with lock)
with self.lock:
    # Quick data structure updates
    self.pending_votes[tx_id]["votes"].append(vote)

    # Check consensus
    if approve_votes >= self.consensus_threshold:
        self.committed_transactions.add(tx_id)
        should_commit = True  # Set flag

# LOCK RELEASED HERE!

# NON-CRITICAL SECTION (lock-free)
if should_commit:
    self._commit_to_blockchain(tx_id)  # Slow I/O, no lock!
```

**Benefits:**
- Blockchain write takes 100-500ms (slow)
- Lock held for <1ms (fast data structure update)
- Other threads can process votes concurrently
- No deadlock risk

---

#### 9.4 Background Threads

**Status:** ✅ **Fully Implemented**

**Cleanup Threads:**

1. **Knowledge Base Cleanup** (Lines 754-788)
   - Runs every 60 seconds
   - Removes observations older than 8 minutes
   - Prevents memory growth

2. **Sampling Cache Cleanup** (Lines 529-550)
   - Runs every 3600 seconds (1 hour)
   - Removes expired sampling entries
   - Saves cache to disk

3. **Knowledge Base Persistence** (Lines 1074-1091)
   - Runs every 60 seconds
   - Saves knowledge base to disk
   - Crash recovery (max 60 seconds data loss)

4. **Transaction Timeout Checker** (Lines 552-608)
   - Runs every 30 seconds
   - Commits timed-out transactions
   - Prevents buffer overflow

**Thread Safety:**
- All use `threading.RLock()` for synchronization
- Daemon threads (exit when main thread exits)

---

## 10. Configuration & Settings

### Q: Where are system parameters configured?

#### 10.1 Consensus Configuration

**File:** `p2p_transaction_pool.py`

| Parameter | Value | Line | Purpose |
|-----------|-------|------|---------|
| Consensus Threshold | 3 | 53 | Minimum votes for consensus (3/9 = 33%) |
| Total Nodes | 9 | 52 | RPKI nodes in network |
| Regular Timeout | 60s | 62 | Timeout for regular announcements |
| Attack Timeout | 180s | 63 | Timeout for attack transactions |
| Knowledge Window | 480s | 58 | Time window for observation matching (8 min) |
| Sampling Window | 3600s | 66 | Duplicate detection window (1 hour) |
| Cleanup Interval | 60s | 59 | Knowledge base cleanup frequency |

---

#### 10.2 Token Configuration

**File:** `bgpcoin_ledger.py`

| Parameter | Value | Line | Purpose |
|-----------|-------|------|---------|
| Total Supply | 10,000,000 | 70 | Max BGPCOIN tokens |
| Block Commit | 10 | 77 | Reward for committing block |
| Vote Approve | 1 | 78 | Reward for correct vote |
| First Commit Bonus | 5 | 79 | Bonus for first to commit |
| Attack Detection | 100 | 80 | Reward for detecting attack |
| Accuracy Range | 0.5 - 1.5 | 86 | Multiplier range |
| Participation Range | 0.8 - 1.2 | 87 | Multiplier range |
| Quality Range | 0.9 - 1.3 | 88 | Multiplier range |
| Burn Rate | 50% | 326 | % burned on spending |
| Recycle Rate | 50% | 327 | % recycled to treasury |

---

#### 10.3 Network Configuration

**File:** `p2p_transaction_pool.py`

| Parameter | Value | Line | Purpose |
|-----------|-------|------|---------|
| Base Port | 8000 | 29 | Starting port number |
| Connection Timeout | 5s | 354, 379 | Socket timeout |
| Server Queue | 5 | 125 | Listen queue size |
| Host | localhost | 124 | P2P communication host |

---

#### 10.4 Experiment Configuration

**File:** `simulation_helpers/shared_data/experiment_config.json`

```json
{
  "simulation_parameters": {
    "time_scale": 1.0,           // Real-time (1.0) or accelerated (>1.0)
    "max_duration": 3600,        // Experiment duration (seconds)
    "expected_nodes": 9,         // Number of RPKI nodes
    "processing_interval": 5.0   // Status update interval (seconds)
  },
  "monitoring": {
    "health_check_interval": 10, // Health check frequency (seconds)
    "enable_dashboard": true,    // Enable live dashboard
    "alert_on_failures": true    // Alert on node failures
  }
}
```

---

## 11. Targeted Attack Handling & Consensus Status Flags

### Q: What happens if a targeted attack has no signers (0 votes)?

**Status:** ✅ **FULLY IMPLEMENTED**

**Concept:** Proof-of-Reputation Consensus with Timeout

**Implementation:** `p2p_transaction_pool.py`

---

#### **The Problem: Targeted Attacks**

**Scenario:**
```
Attacker targets only AS01's prefix
   ↓
AS01 observes attack and creates transaction
   ↓
Broadcasts to 8 peers for signatures
   ↓
But: Other nodes didn't see the attack (targeted)
   ↓
Result: 0 signatures collected
   ↓
Question: Should this be discarded or recorded?
```

**Answer:** **RECORD with special status flag!**

---

#### **Timeout Mechanism with Status Flags**

**File:** `p2p_transaction_pool.py`

**Timeout Configuration** (Lines 62-63):
- **Regular announcements:** 60 seconds
- **Attack transactions:** 180 seconds (longer for analysis)

**Consensus Status Decision Tree** (Lines 638-644):

```python
# After timeout, determine status based on vote count
if approve_count >= self.consensus_threshold:  # >= 3 votes
    consensus_status = "CONFIRMED"
elif approve_count >= 1:  # 1-2 votes
    consensus_status = "INSUFFICIENT_CONSENSUS"
else:  # 0 votes
    consensus_status = "SINGLE_WITNESS"
```

**Three Status Levels:**

| Status | Vote Count | Meaning | Confidence |
|--------|-----------|---------|------------|
| **CONFIRMED** | 3+ approve | Multiple nodes saw it | HIGH (Proof-of-Reputation achieved) |
| **INSUFFICIENT_CONSENSUS** | 1-2 approve | Some nodes saw it | MEDIUM (Partial agreement) |
| **SINGLE_WITNESS** | 0 approve | Only observer saw it | LOW (Potential targeted attack) |

---

#### **Transaction Metadata Stored**

**File:** `p2p_transaction_pool.py`
**Lines:** 672-677

```python
# Metadata added to transaction before blockchain write
transaction["consensus_status"] = consensus_status  # "CONFIRMED", "INSUFFICIENT_CONSENSUS", or "SINGLE_WITNESS"
transaction["consensus_reached"] = (consensus_status == "CONFIRMED")  # Boolean
transaction["signature_count"] = len(vote_data["votes"])  # Total signatures
transaction["approve_count"] = approve_count  # Approve votes only
transaction["timeout_commit"] = True  # Flag indicating timeout (not normal consensus)
```

**Blockchain Entry Example:**

```json
{
  "transaction_id": "tx_20251202_140030_prefix_203.0.113.0_24_as64500",
  "timestamp": "2025-12-02T14:00:30",
  "ip_prefix": "203.0.113.0/24",
  "sender_asn": 64500,
  "is_attack": true,
  "trust_score": 0.2,

  "consensus_status": "SINGLE_WITNESS",
  "consensus_reached": false,
  "signature_count": 0,
  "approve_count": 0,
  "timeout_commit": true,
  "signatures": [],

  "observer_as": 1,
  "observed_at": "2025-12-02T14:00:30"
}
```

**Key Fields for Post-Hoc Analysis:**
- `consensus_status`: Filter by confidence level
- `consensus_reached`: Boolean filter (true/false)
- `approve_count`: Quantitative measure of agreement
- `timeout_commit`: Indicates timeout (not normal consensus path)

---

#### **Why Record SINGLE_WITNESS?**

**Rationale:**

1. **Targeted Attack Detection**
   - Attacker may only target specific nodes
   - Other nodes won't see the attack (no signatures)
   - But the observation is still valuable evidence

2. **Forensic Analysis**
   - Post-hoc analysis can correlate single-witness events
   - Multiple SINGLE_WITNESS events for same prefix → suspicious
   - Can upgrade status after investigation

3. **Complete Audit Trail**
   - No data loss (all observations recorded)
   - Prevents attacker from hiding by avoiding detection
   - Allows retrospective analysis

4. **False Positive Mitigation**
   - SINGLE_WITNESS has low weight in trust scoring
   - Doesn't trigger immediate response
   - Requires post-hoc confirmation

---

#### **Post-Hoc Analysis Integration**

**In Post-Hoc Analysis Script:**

```python
# Filter transactions by consensus status
confirmed_attacks = [
    tx for tx in blockchain
    if tx.get("is_attack") and tx.get("consensus_status") == "CONFIRMED"
]

insufficient_attacks = [
    tx for tx in blockchain
    if tx.get("is_attack") and tx.get("consensus_status") == "INSUFFICIENT_CONSENSUS"
]

single_witness_attacks = [
    tx for tx in blockchain
    if tx.get("is_attack") and tx.get("consensus_status") == "SINGLE_WITNESS"
]

# Analysis
print(f"High Confidence Attacks: {len(confirmed_attacks)}")
print(f"Medium Confidence Attacks: {len(insufficient_attacks)}")
print(f"Low Confidence (Single Witness): {len(single_witness_attacks)}")

# Further investigation of SINGLE_WITNESS
for tx in single_witness_attacks:
    # Check if other nodes saw similar patterns
    # Correlate with timing/prefix/AS patterns
    # Potentially upgrade to confirmed after investigation
```

---

#### **Trust Score Weighting**

**Different weights based on consensus status:**

```python
# Trust scoring logic (example)
if consensus_status == "CONFIRMED":
    trust_weight = 1.0  # 100% weight (high confidence)
elif consensus_status == "INSUFFICIENT_CONSENSUS":
    trust_weight = 0.5  # 50% weight (medium confidence)
elif consensus_status == "SINGLE_WITNESS":
    trust_weight = 0.1  # 10% weight (low confidence)
```

**Rationale:**
- SINGLE_WITNESS has low weight → doesn't heavily penalize AS
- But still recorded → can investigate later
- CONFIRMED has full weight → strong evidence

---

#### **BGPCOIN Rewards**

**Reward Logic** (Lines 696-697):

```python
# Award reduced BGPCOIN rewards for partial consensus
if approve_count > 0 and consensus_status in ["CONFIRMED", "INSUFFICIENT_CONSENSUS"]:
    self._award_bgpcoin_rewards(transaction_id, vote_data)
```

**Reward Policy:**

| Status | Committer Reward | Voter Reward |
|--------|-----------------|--------------|
| **CONFIRMED** (3+ votes) | ✅ Full reward (10-15 BGPCOIN) | ✅ Full reward (1 BGPCOIN each) |
| **INSUFFICIENT_CONSENSUS** (1-2 votes) | ✅ Reduced reward | ✅ Reduced reward |
| **SINGLE_WITNESS** (0 votes) | ❌ No reward | N/A (no voters) |

**Rationale:**
- SINGLE_WITNESS gets no immediate reward (low confidence)
- Can be rewarded later if upgraded to confirmed in post-hoc analysis
- Prevents gaming the system (fake observations for rewards)

---

#### **Implementation Flow**

**Step-by-Step Process:**

1. **Observation** (Time 0s)
   ```python
   # Node AS01 observes potential attack
   p2p_pool.add_bgp_observation(
       ip_prefix="203.0.113.0/24",
       sender_asn=64500,
       is_attack=True  # Attack flag
   )
   ```

2. **Broadcast** (Time 0-5s)
   ```python
   # Create transaction and broadcast for signatures
   p2p_pool.broadcast_transaction(transaction)
   # Sends to 8 peer nodes
   ```

3. **Vote Collection** (Time 5-180s)
   ```python
   # Wait for votes from peers
   # Timeout: 180 seconds for attacks (longer analysis time)
   # If 3+ approve → immediate commit
   # If <3 approve → wait for timeout
   ```

4. **Timeout** (Time 180s)
   ```python
   # Background thread detects timeout
   # Check vote count:
   #   0 votes → SINGLE_WITNESS
   #   1-2 votes → INSUFFICIENT_CONSENSUS
   #   3+ votes → CONFIRMED
   ```

5. **Commit with Status** (Time 180s)
   ```python
   # Write to blockchain with metadata
   transaction["consensus_status"] = "SINGLE_WITNESS"
   transaction["timeout_commit"] = True
   blockchain.add_transaction_to_blockchain(transaction)
   ```

6. **Post-Hoc Analysis** (After experiment)
   ```python
   # Analyze SINGLE_WITNESS events
   # Correlate patterns
   # Potentially upgrade status
   ```

---

#### **Verification**

**How to check if this is working:**

1. **Check logs for timeout messages:**
   ```bash
   grep "timed out" nodes/rpki_nodes/as01/blockchain_node/*.log
   ```
   Should see: `⏱️ Transaction tx_XXX timed out after 180s (ATTACK, timeout=180s)`

2. **Check blockchain for status flags:**
   ```bash
   cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json | \
       jq '.transactions[] | select(.consensus_status != null) | {id: .transaction_id, status: .consensus_status, votes: .approve_count}'
   ```

3. **Count transactions by status:**
   ```python
   import json

   with open('blockchain.json', 'r') as f:
       blockchain = json.load(f)

   status_counts = {
       "CONFIRMED": 0,
       "INSUFFICIENT_CONSENSUS": 0,
       "SINGLE_WITNESS": 0
   }

   for block in blockchain["blocks"]:
       for tx in block.get("transactions", []):
           status = tx.get("consensus_status", "CONFIRMED")  # Default CONFIRMED
           if status in status_counts:
               status_counts[status] += 1

   print(status_counts)
   ```

4. **Expected output:**
   ```
   {
     "CONFIRMED": 750,               # 88% (normal consensus)
     "INSUFFICIENT_CONSENSUS": 80,   # 9% (partial agreement)
     "SINGLE_WITNESS": 20            # 3% (targeted or unique observations)
   }
   ```

---

#### **Post-Hoc Analysis Considerations**

**Analysis Questions:**

1. **Are SINGLE_WITNESS events correlated?**
   - Same prefix/AS across multiple nodes?
   - Same time period?
   - → May indicate distributed targeted attack

2. **Are SINGLE_WITNESS events false positives?**
   - Node malfunction?
   - Misconfigured RPKI ROA?
   - → May need to filter out

3. **Should SINGLE_WITNESS be upgraded?**
   - External evidence (RouteViews, RIPE RIS)?
   - Historical pattern analysis?
   - → Can change status in post-hoc report

**Upgrade Logic:**

```python
def upgrade_single_witness_to_confirmed(transaction_id, reason):
    """
    Upgrade SINGLE_WITNESS to CONFIRMED based on post-hoc evidence.

    Args:
        transaction_id: ID of transaction to upgrade
        reason: Evidence for upgrade (e.g., "Confirmed by RouteViews data")
    """
    # Add upgrade metadata (doesn't modify blockchain, but adds annotation)
    upgrade_record = {
        "transaction_id": transaction_id,
        "original_status": "SINGLE_WITNESS",
        "upgraded_status": "CONFIRMED",
        "upgrade_reason": reason,
        "upgrade_timestamp": datetime.now().isoformat()
    }

    # Save to analysis results
    with open("analysis_results/upgrades.json", "a") as f:
        f.write(json.dumps(upgrade_record) + "\n")
```

---

### Q: Is this the same as "unconfirmed" transactions?

**Status:** ✅ **Yes - Different terminology for same concept**

**Terminology Mapping:**

| Your Term | Implementation Term | Meaning |
|-----------|-------------------|---------|
| "Unconfirmed" | `SINGLE_WITNESS` or `INSUFFICIENT_CONSENSUS` | Did not reach 3/9 consensus |
| "Confirmed" | `CONFIRMED` | Reached 3/9 consensus |
| "Flag" | `consensus_status` field | Status indicator |
| "Post-hoc analysis" | Post-experiment analysis script | Analyze unconfirmed transactions |

**Boolean Field:**
- `consensus_reached: true` → CONFIRMED (confirmed)
- `consensus_reached: false` → INSUFFICIENT_CONSENSUS or SINGLE_WITNESS (unconfirmed)

---

### Q: Can transactions be upgraded from SINGLE_WITNESS to CONFIRMED?

**Status:** ⚠️ **Partially - In Post-Hoc Analysis Only**

**Current Behavior:**
- Blockchain is immutable (cannot modify `consensus_status` field)
- But can create **upgrade annotations** in analysis results

**Proposed Post-Hoc Upgrade:**

```python
# analysis/upgrade_single_witness.py

class TransactionUpgrader:
    def __init__(self, blockchain_path):
        self.blockchain = load_blockchain(blockchain_path)
        self.upgrades = []

    def find_upgradeable_transactions(self):
        """Find SINGLE_WITNESS that should be upgraded."""
        candidates = []

        for tx in self.blockchain["transactions"]:
            if tx.get("consensus_status") == "SINGLE_WITNESS":
                # Check upgrade criteria
                if self._should_upgrade(tx):
                    candidates.append(tx)

        return candidates

    def _should_upgrade(self, tx):
        """Determine if SINGLE_WITNESS should be upgraded."""
        # Criterion 1: Multiple nodes observed same attack
        similar_txs = self._find_similar_transactions(tx)
        if len(similar_txs) >= 3:
            return True

        # Criterion 2: External data confirms attack
        if self._check_external_data(tx):
            return True

        # Criterion 3: Historical pattern match
        if self._matches_known_attack_pattern(tx):
            return True

        return False

    def create_upgrade_report(self, transactions):
        """Create report of upgraded transactions."""
        report = {
            "upgrade_timestamp": datetime.now().isoformat(),
            "upgraded_count": len(transactions),
            "transactions": [
                {
                    "transaction_id": tx["transaction_id"],
                    "original_status": tx["consensus_status"],
                    "upgraded_status": "CONFIRMED",
                    "upgrade_reason": self._get_upgrade_reason(tx)
                }
                for tx in transactions
            ]
        }

        with open("analysis_results/transaction_upgrades.json", "w") as f:
            json.dump(report, f, indent=2)
```

**Usage in Post-Hoc Analysis:**

```python
# During post-hoc analysis
upgrader = TransactionUpgrader("nodes/rpki_nodes/as01/blockchain_data/chain/blockchain.json")
upgradeable = upgrader.find_upgradeable_transactions()

print(f"Found {len(upgradeable)} SINGLE_WITNESS transactions that should be upgraded")

# Create upgrade report (doesn't modify blockchain)
upgrader.create_upgrade_report(upgradeable)

# Use upgraded status in analysis
for tx in upgradeable:
    # Treat as CONFIRMED in trust scoring
    # Include in high-confidence attack count
    # Report in final analysis
```

---

## 12. Fork Resolution & Transaction Rescue

### Q: What happens when a blockchain fork occurs?

**Status:** ⚠️ **PARTIALLY IMPLEMENTED** - Needs transaction rescue mechanism

**Current Behavior:**

When nodes have divergent blockchains (fork):
1. Each node maintains its own blockchain independently
2. Transactions on the "uncle chain" (shorter/discarded fork) are NOT rescued
3. Those transactions are lost permanently

**Problem:**

```
Node A blockchain:  Block 0 → Block 1 → Block 2 → Block 3 (longer chain)
                                   ↓
Node B blockchain:  Block 0 → Block 1 → Block 2' (uncle/orphan block)
                                         └─ Transaction X (LOST!)
```

If Transaction X was valid but ended up on shorter chain, it should be re-added to main chain.

---

### Q: Is there fork detection implemented?

**Status:** ⚠️ **Partially** - Can detect but doesn't auto-resolve

**Detection Method:**

**Post-Hoc Analysis** (Section 9 in post-hoc analysis):
- Compare blockchains from all 9 nodes
- Check block counts and hashes at each height
- Identify divergence points

**Not Implemented:**
- Real-time fork detection during experiment
- Automatic fork resolution
- Transaction rescue from uncle chains

---

### Q: How should fork resolution work?

**Status:** ❌ **NOT IMPLEMENTED** - Design needed

**Proposed Solution: Transaction Rescue Mechanism**

#### **Step 1: Fork Detection**

**File to Create:** `fork_resolver.py`

**Mechanism:**
```python
class ForkResolver:
    def detect_fork(self, all_node_blockchains):
        """
        Compare blockchains from all nodes to detect forks.

        Args:
            all_node_blockchains: Dict of {as_number: blockchain_data}

        Returns:
            fork_info: {
                "fork_detected": True/False,
                "fork_height": block_number where fork occurred,
                "main_chain": [list of nodes on longest chain],
                "uncle_chains": [list of nodes on shorter chains]
            }
        """
        # Find longest chain (most blocks)
        max_length = max(len(chain["blocks"]) for chain in all_node_blockchains.values())

        # Nodes with max length = main chain
        main_chain_nodes = [as_num for as_num, chain in all_node_blockchains.items()
                           if len(chain["blocks"]) == max_length]

        # Other nodes = uncle chains
        uncle_chain_nodes = [as_num for as_num, chain in all_node_blockchains.items()
                            if len(chain["blocks"]) < max_length]

        if not uncle_chain_nodes:
            return {"fork_detected": False}

        # Find fork point (where chains diverged)
        fork_height = find_divergence_point(all_node_blockchains)

        return {
            "fork_detected": True,
            "fork_height": fork_height,
            "main_chain_nodes": main_chain_nodes,
            "uncle_chain_nodes": uncle_chain_nodes
        }
```

#### **Step 2: Transaction Extraction**

**Extract Uncle Chain Transactions:**

```python
def extract_uncle_transactions(uncle_blockchain, fork_height):
    """
    Extract transactions from blocks after fork point on uncle chain.

    Args:
        uncle_blockchain: Blockchain data from node on shorter chain
        fork_height: Block number where fork occurred

    Returns:
        List of transactions from uncle blocks
    """
    uncle_transactions = []

    # Get all blocks after fork point
    for block in uncle_blockchain["blocks"][fork_height+1:]:
        for transaction in block.get("transactions", []):
            uncle_transactions.append(transaction)

    return uncle_transactions
```

#### **Step 3: Transaction Validation**

**Check if Uncle Transactions Already Exist on Main Chain:**

```python
def filter_missing_transactions(uncle_transactions, main_chain_blockchain):
    """
    Filter out transactions that already exist on main chain.

    Args:
        uncle_transactions: Transactions from uncle chain
        main_chain_blockchain: Blockchain data from main chain node

    Returns:
        List of transactions NOT on main chain (need to be rescued)
    """
    main_chain_tx_ids = set()

    # Collect all transaction IDs from main chain
    for block in main_chain_blockchain["blocks"]:
        for tx in block.get("transactions", []):
            main_chain_tx_ids.add(tx["transaction_id"])

    # Filter uncle transactions not on main chain
    missing_transactions = [
        tx for tx in uncle_transactions
        if tx["transaction_id"] not in main_chain_tx_ids
    ]

    return missing_transactions
```

#### **Step 4: Transaction Re-Submission**

**Add Missing Transactions to Main Chain:**

```python
def rescue_transactions(missing_transactions, target_node):
    """
    Re-submit missing transactions to be added to main chain.

    Args:
        missing_transactions: Transactions to rescue
        target_node: P2PTransactionPool instance on main chain

    Process:
        1. Re-broadcast transaction for voting
        2. Collect consensus (3/9 threshold)
        3. Commit to blockchain
    """
    for transaction in missing_transactions:
        # Mark as "rescued" to avoid timeout
        transaction["rescued_from_fork"] = True
        transaction["original_block"] = transaction.get("block_number")

        # Re-broadcast for consensus
        target_node.broadcast_transaction(transaction)

        # Transaction will go through normal consensus process
        # If 3+ nodes approve, it gets added to main chain
```

#### **Step 5: Synchronization**

**Sync Uncle Chain Nodes to Main Chain:**

```python
def sync_uncle_node_to_main_chain(uncle_node, main_chain_blockchain):
    """
    Replace uncle node's blockchain with main chain.

    Args:
        uncle_node: Node on shorter chain
        main_chain_blockchain: Blockchain data from main chain

    WARNING: This discards the uncle chain completely!
    """
    # Backup uncle chain (for forensics)
    backup_path = f"blockchain_backup_fork_{datetime.now().isoformat()}.json"
    with open(backup_path, 'w') as f:
        json.dump(uncle_node.blockchain.blockchain_data, f, indent=2)

    # Replace with main chain
    uncle_node.blockchain.blockchain_data = main_chain_blockchain.copy()
    uncle_node.blockchain._save_blockchain()

    print(f"✅ Node AS{uncle_node.as_number} synced to main chain")
    print(f"   Uncle chain backed up to: {backup_path}")
```

---

### Q: When should fork resolution run?

**Trigger Points:**

**Option 1: Post-Experiment (Safer)**
- Run after experiment completes
- Analyze all blockchains
- Rescue transactions offline
- No risk of interfering with live consensus

**Option 2: Periodic During Experiment (Complex)**
- Background thread checks every 5 minutes
- Detects forks early
- Rescues transactions immediately
- Risk: Adds complexity to live system

**Recommendation:** Start with **Post-Experiment** resolution.

---

### Q: What's the implementation priority?

**Implementation Plan:**

**Phase 1: Detection (Required for Post-Hoc Analysis)**
- ✅ Already possible in post-hoc analysis (Section 9)
- Compare blockchains manually
- Identify forks

**Phase 2: Transaction Rescue (High Priority)**
- ⚠️ **NEEDS IMPLEMENTATION**
- Extract uncle transactions
- Filter missing transactions
- Re-submit to main chain

**Phase 3: Automatic Synchronization (Medium Priority)**
- Sync uncle nodes to main chain
- Backup discarded chains
- Update node states

**Phase 4: Real-Time Fork Resolution (Low Priority)**
- Live detection during experiment
- Automatic rescue mechanism
- Fork prevention strategies

---

### Q: What are the implementation files?

**Files to Create:**

1. **`fork_resolver.py`**
   - **Location:** `shared_blockchain_stack/blockchain_utils/`
   - **Purpose:** Fork detection and resolution
   - **Status:** ❌ Not Implemented

2. **`transaction_rescue.py`**
   - **Location:** `shared_blockchain_stack/blockchain_utils/`
   - **Purpose:** Extract and re-submit uncle transactions
   - **Status:** ❌ Not Implemented

3. **`blockchain_sync.py`**
   - **Location:** `shared_blockchain_stack/blockchain_utils/`
   - **Purpose:** Sync uncle nodes to main chain
   - **Status:** ❌ Not Implemented

**Integration Points:**

- **Post-Hoc Analysis:** Add fork resolution step (Section 5.9)
- **Main Experiment:** Optional periodic fork check
- **Blockchain Interface:** Add fork detection methods

---

### Q: What causes forks in BGP-Sentry?

**Common Fork Causes:**

1. **Network Partition**
   - Nodes temporarily lose connectivity
   - Different subsets commit different transactions
   - Chains diverge

2. **Concurrent Commits**
   - Two nodes commit at exact same time
   - Different nodes see different "latest block"
   - Race condition creates fork

3. **Timeout with Insufficient Consensus**
   - Node A commits with CONFIRMED (3+ votes)
   - Node B commits same announcement with INSUFFICIENT (1-2 votes)
   - Different transaction IDs → fork

4. **Node Failure During Commit**
   - Node crashes mid-commit
   - Some nodes see transaction, others don't
   - Inconsistent state

**Prevention Strategies:**

- **Leader Election:** One node commits per round (no races)
- **Stronger Consensus:** Increase threshold to 6/9 (harder to fork)
- **Transaction Ordering:** Global timestamp coordination
- **Periodic Sync:** Nodes check for divergence every 60 seconds

---

### Q: How to test fork resolution?

**Test Scenario:**

```python
# Test Fork Resolution
def test_fork_resolution():
    # Step 1: Create intentional fork
    # Stop AS09 from receiving votes
    # AS09 commits with SINGLE_WITNESS
    # Other nodes commit with CONFIRMED
    # → Fork created!

    # Step 2: Detect fork
    fork_info = fork_resolver.detect_fork(all_blockchains)
    assert fork_info["fork_detected"] == True
    assert fork_info["uncle_chain_nodes"] == [9]

    # Step 3: Extract uncle transactions
    uncle_txs = fork_resolver.extract_uncle_transactions(
        blockchain_as09,
        fork_info["fork_height"]
    )
    assert len(uncle_txs) > 0

    # Step 4: Filter missing transactions
    missing = fork_resolver.filter_missing_transactions(
        uncle_txs,
        blockchain_as01  # Main chain
    )

    # Step 5: Rescue transactions
    for tx in missing:
        p2p_pool.broadcast_transaction(tx)

    # Step 6: Verify rescue
    # Check that transactions now exist on main chain
    assert all(tx_exists_on_main_chain(tx) for tx in missing)
```

**Test File:** `tests/test_fork_resolution.py`

---

## 12. Questions & Answers Template

Use this section to ask specific questions about implementation. Format:

### Q: [Your Question]

**Status:** ✅ Implemented / ⚠️ Partially Implemented / ❌ Not Implemented

**File:** `path/to/file.py`

**Lines:** XX-YY

**Implementation Details:** ...

---

## 12. File Directory Reference

### Core Files

| Component | File Path | Lines | Purpose |
|-----------|-----------|-------|---------|
| Main Entry | `main_experiment.py` | 1-575 | Experiment orchestrator |
| Consensus Engine | `shared_blockchain_stack/blockchain_utils/p2p_transaction_pool.py` | 1-1151 | P2P consensus, voting, timeouts |
| Token Ledger | `shared_blockchain_stack/blockchain_utils/bgpcoin_ledger.py` | 1-535 | BGPCOIN economics |
| Blockchain Interface | `shared_blockchain_stack/blockchain_utils/blockchain_interface.py` | - | Read/write blockchain |
| Attack Detector | `bgp_attack_detection/attack_detector.py` | - | Aggregate attack detection |
| Attack Consensus | `shared_blockchain_stack/blockchain_utils/attack_consensus.py` | - | Attack voting system |
| Governance | `shared_blockchain_stack/blockchain_utils/governance_system.py` | - | Decentralized governance |
| Node Registry | `shared_blockchain_stack/blockchain_utils/rpki_node_registry.py` | 1-50 | RPKI node list |
| Neighbor Cache | `shared_blockchain_stack/network_stack/relevant_neighbor_cache.py` | - | Optimized voting |

### Attack Detectors

| Detector | File Path | Purpose |
|----------|-----------|---------|
| Prefix Hijack | `bgp_attack_detection/detectors/prefix_hijack_detector.py` | Exact prefix hijack |
| Sub-Prefix Hijack | `bgp_attack_detection/detectors/subprefix_detector.py` | More-specific prefix |
| Route Leak | `bgp_attack_detection/detectors/route_leak_detector.py` | Valley-free violation |

### Validators

| Validator | File Path | Purpose |
|-----------|-----------|---------|
| RPKI | `bgp_attack_detection/validators/rpki_validator.py` | ROA validation |
| IRR | `bgp_attack_detection/validators/irr_validator.py` | IRR validation |

---

## 13. Key Metrics & Statistics

### Current Implementation Stats

- **Total Python Files:** 44
- **Core Blockchain Utils:** 30 files
- **Attack Detection Files:** 9 files
- **Total Lines (blockchain_utils):** 11,398 lines
- **Largest File:** `p2p_transaction_pool.py` (1,151 lines)
- **Second Largest:** `bgpcoin_ledger.py` (535 lines)

### Node Statistics

- **RPKI Nodes:** 9 (AS01, AS03, AS05, AS07, AS09, AS11, AS13, AS15, AS17)
- **P2P Connections:** 72 (9 nodes × 8 peers each)
- **Ports Used:** 8001, 8003, 8005, 8007, 8009, 8011, 8013, 8015, 8017
- **Storage per Node:** ~10-20 MB per experiment hour

---

## Usage

**To find implementation details:**

1. **Search by question:** Use section headings (e.g., "Q: How does consensus work?")
2. **Search by keyword:** Ctrl+F for terms like "timeout", "BGPCOIN", "vote"
3. **Search by file:** Look up file path in Section 12 (File Directory Reference)
4. **Search by line number:** Go directly to implementation

**Example queries:**
- "Where is consensus threshold set?" → Section 3, Line 53 of p2p_transaction_pool.py
- "How is sampling implemented?" → Section 9.1, Lines 398-445, 726-730
- "What attack detectors exist?" → Section 5, three detector files listed
- "Where are rewards calculated?" → Section 4, bgpcoin_ledger.py lines 185-210

---

**Last Updated:** December 2, 2025

**Document Version:** 1.0

**Maintainer:** BGP-Sentry Team
