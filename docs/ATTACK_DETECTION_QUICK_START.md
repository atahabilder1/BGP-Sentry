# Attack Detection System - Quick Start Guide

## ✅ System Status

**All components implemented and tested:**
- ✅ IP Prefix Hijacking Detection
- ✅ Route Leak Detection
- ✅ Non-RPKI Rating System
- ✅ Attack Consensus Voting
- ✅ BGPCOIN Rewards
- ✅ Blockchain Integration

**Test Results**: All 6 tests passed!

---

## 🚀 Quick Start

### **1. Run the Test Suite**

Verify the attack detection system is working:

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 test_attack_detection.py
```

**Expected Output**:
```
🎉 ALL TESTS PASSED! Attack detection system is working correctly.
```

---

### **2. Start BGP-Sentry Nodes**

The attack detection system is automatically integrated. Just start the nodes normally:

```bash
# Terminal 1 - Start AS01
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node
python3 observer_main.py

# Terminal 2 - Start AS03
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as03/blockchain_node
python3 observer_main.py

# ... (repeat for AS05, AS07, AS09, etc.)
```

**Look for these initialization messages**:
```
🔍 Attack Detector initialized
   ROA entries: 3
   AS relationships: 9

📊 Loaded ratings for X non-RPKI ASes

🛡️ Attack consensus system initialized
   Min votes required: 3
   Verdicts file: blockchain_data/chain/attack_verdicts.jsonl
```

---

### **3. How Attack Detection Works Automatically**

When a BGP announcement is processed:

```
1. BGP Announcement Observed
   ↓
2. Knowledge-Based Voting (3/9) → Transaction to Blockchain
   ↓
3. ATTACK DETECTION TRIGGERED AUTOMATICALLY
   Each node analyzes independently
   ↓
4. If attack detected → Attack proposal broadcast
   ↓
5. Attack consensus voting (majority)
   ↓
6. Verdict executed:
   - Rating updated
   - BGPCOIN distributed
   - Verdict saved to blockchain
```

**No manual intervention needed!**

---

## 📊 Monitoring Attack Detection

### **View Attack Verdicts**

```bash
# View attack verdict history
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/attack_verdicts.jsonl | jq

# Count total attacks detected
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/attack_verdicts.jsonl | wc -l

# View latest attack
tail -n 1 nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/attack_verdicts.jsonl | jq
```

### **View Non-RPKI Ratings**

```bash
# View all non-RPKI AS ratings
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json | jq

# View specific AS rating
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json | jq '.as_ratings["666"]'

# View rating history
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/rating_history.jsonl | jq
```

### **View BGPCOIN Balances**

```bash
# View ledger summary
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/bgpcoin_ledger.json | jq '{
  treasury: .protocol_treasury,
  total_distributed: .total_distributed,
  total_burned: .total_burned
}'

# View node balance
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/bgpcoin_ledger.json | jq '.balances["1"]'

# View BGPCOIN transaction log
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/bgpcoin_transactions.jsonl | grep "attack" | jq
```

---

## 🧪 Testing Attack Detection

### **Test 1: Simulate IP Prefix Hijacking**

Create a malicious BGP announcement:

```python
# In observer_main.py or test script
announcement = {
    "sender_asn": 666,          # Malicious AS
    "ip_prefix": "8.8.8.0/24",  # Google's prefix
    "as_path": [666],
    "timestamp": datetime.now().isoformat()
}

# The system will:
# 1. Detect IP hijacking (ROA violation)
# 2. Broadcast attack proposal
# 3. Nodes vote YES/NO
# 4. If majority YES → Rating penalty, BGPCOIN rewards
```

**Expected Result**:
```
🚨 IP PREFIX HIJACKING DETECTED!
   Attacker: AS666
   Stolen Prefix: 8.8.8.0/24
   Legitimate Owner: AS15169

Voting: 6 YES, 3 NO
Verdict: ATTACK_CONFIRMED (confidence: 0.67)

AS666 rating: 50 → 30
Detector: +10 BGPCOIN
Correct voters: +2 BGPCOIN each
```

### **Test 2: Simulate Route Leak**

Create a route leak announcement:

```python
announcement = {
    "sender_asn": 5,
    "ip_prefix": "203.0.113.0/24",
    "as_path": [5, 7, 5, 3, 1],  # AS5 leaked from provider to peer
    "timestamp": datetime.now().isoformat()
}

# The system will:
# 1. Detect route leak (valley-free violation)
# 2. Broadcast attack proposal
# 3. Nodes vote
# 4. Execute verdict
```

**Expected Result**:
```
🚨 ROUTE LEAK DETECTED!
   Leaker: AS7
   Received from: AS5 (peer)
   Leaked to: AS5 (peer)

Voting: 7 YES, 2 NO
Verdict: ATTACK_CONFIRMED (confidence: 0.78)

AS5 rating: 50 → 35
```

### **Test 3: Legitimate Announcement**

```python
announcement = {
    "sender_asn": 15169,        # Google
    "ip_prefix": "8.8.8.0/24",  # Google's prefix
    "as_path": [15169],
    "timestamp": datetime.now().isoformat()
}

# Expected: No attack detected, normal processing
```

---

## 📁 File Locations

### **Code Files**

```
blockchain_utils/
├── attack_detector.py          # Attack detection logic
├── nonrpki_rating.py           # Rating system
├── attack_consensus.py         # Consensus voting
├── bgpcoin_ledger.py           # Token rewards
├── p2p_transaction_pool.py     # P2P integration
└── test_attack_detection.py    # Test suite
```

### **Data Files**

```
blockchain_data/
├── chain/
│   ├── blockchain.json         # Transactions
│   └── attack_verdicts.jsonl   # Attack verdicts (NEW)
└── state/
    ├── roa_database.json       # IP → AS mappings (NEW)
    ├── as_relationships.json   # AS relationships (NEW)
    ├── nonrpki_ratings.json    # Trust scores (NEW)
    ├── rating_history.jsonl    # Rating changes (NEW)
    ├── bgpcoin_ledger.json     # Token balances
    └── knowledge_base.json     # BGP observations
```

---

## 🔧 Configuration

### **ROA Database** (`roa_database.json`)

Add IP prefix authorizations:

```json
{
  "8.8.8.0/24": {
    "authorized_as": 15169,
    "max_length": 24,
    "description": "Google DNS"
  },
  "YOUR_PREFIX": {
    "authorized_as": YOUR_AS,
    "max_length": 24,
    "description": "Description"
  }
}
```

### **AS Relationships** (`as_relationships.json`)

Define AS relationships:

```json
{
  "YOUR_AS": {
    "customers": [LIST_OF_CUSTOMER_AS],
    "providers": [LIST_OF_PROVIDER_AS],
    "peers": [LIST_OF_PEER_AS]
  }
}
```

### **BGPCOIN Rewards** (`attack_consensus.py`)

Adjust rewards/penalties:

```python
self.rewards = {
    "attack_detection": 10,      # Detector reward
    "correct_vote": 2,           # Voter reward
    "false_accusation": -20      # False accusation penalty
}
```

---

## 📊 Example Attack Detection Log

**Node AS01 Logs**:
```
[2025-10-21 15:58:30] 📨 Received BGP announcement
[2025-10-21 15:58:31] 🔍 Analyzing transaction for potential attacks...
[2025-10-21 15:58:31] 🚨 IP PREFIX HIJACKING DETECTED!
[2025-10-21 15:58:31]    Attacker: AS666, Victim: 8.8.8.0/24
[2025-10-21 15:58:31] 📡 Broadcasted attack proposal to 8 nodes
[2025-10-21 15:58:32] 🗳️ AS3 voted YES on attack proposal
[2025-10-21 15:58:32] 🗳️ AS5 voted YES on attack proposal
[2025-10-21 15:58:33] 🗳️ AS7 voted NO on attack proposal
[2025-10-21 15:58:34] 📊 Consensus Check: 6 YES, 3 NO (67% approval)
[2025-10-21 15:58:34] ✅ CONSENSUS REACHED: ATTACK_CONFIRMED
[2025-10-21 15:58:34] 📉 AS666 rating: 50 → 30
[2025-10-21 15:58:34] 💰 Detector AS1 awarded 10 BGPCOIN
[2025-10-21 15:58:34] 💰 5 correct voters awarded 2 BGPCOIN each
[2025-10-21 15:58:34] 💾 Verdict saved to blockchain
```

---

## 🔍 Troubleshooting

### **Issue: No attacks detected**

**Solution**: Check ROA database and AS relationships are configured:

```bash
# Verify ROA database exists
cat blockchain_data/state/roa_database.json | jq

# Verify AS relationships exist
cat blockchain_data/state/as_relationships.json | jq
```

### **Issue: Verdicts not saved**

**Solution**: Ensure blockchain directory exists:

```bash
mkdir -p nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain
mkdir -p nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state
```

### **Issue: BGPCOIN rewards not distributed**

**Solution**: Check treasury balance:

```bash
cat blockchain_data/state/bgpcoin_ledger.json | jq .protocol_treasury
```

If depleted, the system will warn but continue operating.

---

## 📚 Additional Documentation

- **Complete System**: `ATTACK_DETECTION_COMPLETE_SYSTEM.md`
- **Implementation Summary**: `ATTACK_DETECTION_IMPLEMENTATION_SUMMARY.md`
- **BGPCOIN System**: `BGPCOIN_COMPLETE_SYSTEM.md`
- **Knowledge-Based Voting**: `KNOWLEDGE_BASED_VOTING.md`

---

## 🎯 Next Steps

1. **✅ Run Test Suite** - Verify everything works
2. **✅ Start Nodes** - Launch RPKI observers
3. **✅ Monitor Logs** - Watch attack detection in action
4. **Configure ROAs** - Add real-world IP prefix authorizations
5. **Configure AS Relationships** - Add accurate AS topology
6. **Analyze Results** - Review attack verdicts and ratings

---

## 🎉 System Ready!

The attack detection system is **fully implemented and tested**. It will:

- ✅ Automatically detect IP prefix hijacking
- ✅ Automatically detect route leaks
- ✅ Use majority voting for consensus
- ✅ Update non-RPKI AS ratings instantly
- ✅ Distribute BGPCOIN rewards/penalties
- ✅ Record all verdicts to blockchain
- ✅ Preserve full transparency with voter records

**No additional setup required - just start the nodes!**

---

**Questions?** Check the comprehensive documentation in the `docs/` folder or review the test suite for examples.
