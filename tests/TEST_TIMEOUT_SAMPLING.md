# Test Documentation: Timeout, Sampling, and Vote Deduplication

## Overview

This document describes the test scenarios for verifying the timeout mechanism, sampling logic, and vote deduplication in the BGP-Sentry P2P transaction pool.

---

## Test Categories

### 1. Transaction Timeout Mechanism
### 2. Sampling Logic (1-hour window)
### 3. Vote Deduplication (Replay Attack Prevention)

---

## 1. Transaction Timeout Mechanism

### Purpose
Prevent buffer overflow and system deadlock by timing out pending transactions that don't reach consensus.

### Timeout Configuration
- **Regular announcements**: 60 seconds
- **Attack transactions**: 180 seconds

### Test Scenarios

#### Test 1.1: Regular Transaction Timeout (60 seconds)

**Setup:**
- Create regular BGP announcement transaction
- Broadcast to peers (0 votes expected)

**Expected Behavior:**
```
T=0s:   Transaction created, broadcast to peers
T=30s:  Transaction still pending (no timeout yet)
T=60s:  Timeout triggered
T=61s:  Transaction written as SINGLE_WITNESS
        pending_votes cleared
        Buffer freed
```

**Success Criteria:**
- Transaction committed to blockchain at T≥60s
- Consensus status: `SINGLE_WITNESS`
- `approve_count`: 0
- `timeout_commit`: true

**Failure Modes:**
- ❌ Transaction NOT committed after 60s (timeout not working)
- ❌ Transaction committed too early (<60s)
- ❌ Buffer overflow (pending_votes not cleared)

---

#### Test 1.2: Attack Transaction Timeout (180 seconds)

**Setup:**
- Create attack BGP announcement transaction
- Broadcast to peers (0 votes expected)

**Expected Behavior:**
```
T=0s:    Transaction created, broadcast to peers
T=60s:   Transaction still pending (NOT timed out, attack has 180s timeout)
T=120s:  Transaction still pending
T=180s:  Timeout triggered
T=181s:  Transaction written as SINGLE_WITNESS
```

**Success Criteria:**
- Transaction NOT committed at T=60s (should still be pending)
- Transaction committed at T≥180s
- Consensus status: `SINGLE_WITNESS`

**Failure Modes:**
- ❌ Attack timed out at 60s (wrong timeout duration)
- ❌ Attack never timed out (timeout not working)

---

#### Test 1.3: Insufficient Consensus Timeout

**Setup:**
- Create regular transaction
- Receive 2 approve votes (threshold is 3)
- Wait 60 seconds

**Expected Behavior:**
```
T=0s:   Transaction created
T=5s:   AS3 votes approve (1/3)
T=10s:  AS5 votes approve (2/3)
T=60s:  Timeout triggered (consensus not reached)
T=61s:  Transaction written as INSUFFICIENT_CONSENSUS
```

**Success Criteria:**
- Transaction committed at T≥60s
- Consensus status: `INSUFFICIENT_CONSENSUS`
- `approve_count`: 2
- `timeout_commit`: true

**Impact Analysis:**
- Trust scoring: 10% impact (low confidence, per user requirements)
- Attack detection: Still analyzed but flagged as low confidence
- Post-hoc analysis: Can be upgraded to CONFIRMED if pattern matches

---

#### Test 1.4: Confirmed Before Timeout

**Setup:**
- Create regular transaction
- Receive 3 approve votes within 60 seconds

**Expected Behavior:**
```
T=0s:   Transaction created
T=5s:   AS3 votes approve (1/3)
T=10s:  AS5 votes approve (2/3)
T=15s:  AS7 votes approve (3/3) → CONSENSUS REACHED
T=16s:  Transaction immediately committed as CONFIRMED
        Timeout thread finds transaction already committed, skips
```

**Success Criteria:**
- Transaction committed at T<60s (no timeout needed)
- Consensus status: `CONFIRMED` (or `consensus_reached: true`)
- `timeout_commit`: false (committed via normal consensus)

---

## 2. Sampling Logic (1-hour window)

### Purpose
Reduce blockchain bloat by sampling regular announcements (1 per hour per prefix/AS pair).

### Sampling Configuration
- **Window**: 3600 seconds (1 hour)
- **Applies to**: Regular announcements only
- **Bypass**: Attack announcements always recorded

### Test Scenarios

#### Test 2.1: Skip Duplicate Within 1 Hour

**Setup:**
- Record observation: AS12 announces 203.0.113.0/24 at T=0
- Try to record same observation at T=30 minutes

**Expected Behavior:**
```
T=0min:   add_bgp_observation(203.0.113.0/24, AS12) → Returns True (recorded)
          last_seen_cache[(203.0.113.0/24, 12)] = timestamp_0

T=30min:  add_bgp_observation(203.0.113.0/24, AS12) → Returns False (skipped)
          Log: "📊 Sampling: 203.0.113.0/24 from AS12 seen 1800s ago, skipping"
```

**Success Criteria:**
- First observation recorded (knowledge base += 1)
- Second observation skipped (knowledge base unchanged)
- Cache hit in O(1) time (no blockchain scan)

**Failure Modes:**
- ❌ Duplicate recorded (sampling not working)
- ❌ Blockchain scanned instead of cache (performance issue)

---

#### Test 2.2: Record After 1 Hour

**Setup:**
- Record observation at T=0
- Try to record same observation at T=61 minutes

**Expected Behavior:**
```
T=0min:   add_bgp_observation(203.0.113.0/24, AS12) → Returns True
          last_seen_cache[(203.0.113.0/24, 12)] = timestamp_0

T=61min:  add_bgp_observation(203.0.113.0/24, AS12) → Returns True (recorded)
          last_seen_cache[(203.0.113.0/24, 12)] = timestamp_61
```

**Success Criteria:**
- Second observation recorded (outside 1-hour window)
- Cache updated with new timestamp

---

#### Test 2.3: Different Prefix or AS Not Affected

**Setup:**
- Record: AS12 announces 203.0.113.0/24 at T=0
- Try: AS12 announces 198.51.100.0/24 at T=1min (different prefix)
- Try: AS13 announces 203.0.113.0/24 at T=2min (different AS)

**Expected Behavior:**
```
T=0min:  add_bgp_observation(203.0.113.0/24, AS12) → True
T=1min:  add_bgp_observation(198.51.100.0/24, AS12) → True (different prefix)
T=2min:  add_bgp_observation(203.0.113.0/24, AS13) → True (different AS)
```

**Success Criteria:**
- All 3 observations recorded (different cache keys)

---

#### Test 2.4: Attack Bypass Sampling

**Setup:**
- Record attack: AS12 announces 203.0.113.0/24 (attack) at T=0
- Try: Same attack at T=5 minutes

**Expected Behavior:**
```
T=0min:  add_bgp_observation(203.0.113.0/24, AS12, is_attack=True) → True
T=5min:  add_bgp_observation(203.0.113.0/24, AS12, is_attack=True) → True
         (Attacks bypass sampling check)
```

**Success Criteria:**
- Both attacks recorded
- No cache lookup performed for attacks

---

#### Test 2.5: Cache Persistence Across Restarts

**Setup:**
- Node AS01 records observation at T=0
- Save cache to `last_seen_announcements.json`
- Restart node
- Try to record same observation at T=30 minutes

**Expected Behavior:**
```
T=0min:     Record observation → last_seen_cache updated
            _save_last_seen_cache() → File written

[Node restart]

T=0min+1s:  _load_last_seen_cache() → Cache loaded from disk
T=30min:    Try same observation → Skipped (cache persisted)
```

**Success Criteria:**
- Cache loaded on startup
- Expired entries filtered out (>1 hour old)
- Valid entries restored

---

## 3. Vote Deduplication (Replay Attack Prevention)

### Purpose
Prevent malicious nodes from inflating vote counts through replay attacks.

### Security Rules
- Each AS can vote ONCE per transaction
- Total votes ≤ total nodes (9)
- Duplicate votes rejected with warning

### Test Scenarios

#### Test 3.1: Reject Duplicate Vote from Same AS

**Setup:**
- Transaction created
- AS3 votes "approve" at T=0
- AS3 tries to vote "approve" again at T=1s

**Expected Behavior:**
```
T=0s:  AS3 votes approve
       votes = [{from_as: 3, vote: "approve"}]
       Log: "✅ Received signature from AS3"

T=1s:  AS3 votes approve (duplicate)
       Check: AS3 in existing_voters → TRUE
       Log: "🚨 REPLAY ATTACK DETECTED: AS3 already voted"
       Vote rejected
       votes = [{from_as: 3, vote: "approve"}]  (unchanged)
```

**Success Criteria:**
- First vote accepted
- Second vote rejected
- Vote count remains 1
- Warning logged

**Failure Modes:**
- ❌ Duplicate vote accepted (vote count = 2)
- ❌ No warning logged

---

#### Test 3.2: Reject Vote Overflow (>9 votes)

**Setup:**
- Transaction already has 9 votes (all nodes voted)
- Hypothetical 10th node tries to vote

**Expected Behavior:**
```
votes = [AS1, AS3, AS5, AS7, AS9, AS11, AS13, AS15, AS17]  (9 votes)

AS19 tries to vote:
  Check: len(existing_voters) >= total_nodes (9)
  Log: "🚨 VOTE OVERFLOW: Transaction already has 9 votes"
  Vote rejected
```

**Success Criteria:**
- Vote rejected
- Vote count remains 9
- Error logged

**Security Impact:**
- Prevents vote stuffing attacks
- Maintains Byzantine fault tolerance bounds

---

#### Test 3.3: Accept Unique Votes from Different Nodes

**Setup:**
- Transaction created
- AS3, AS5, AS7 vote sequentially

**Expected Behavior:**
```
T=0s:  AS3 votes → Accepted (1/3)
T=1s:  AS5 votes → Accepted (2/3)
T=2s:  AS7 votes → Accepted (3/3) → CONSENSUS REACHED
```

**Success Criteria:**
- All 3 votes accepted
- Vote count = 3
- Consensus triggered

---

## Running Tests

### Unit Tests (Mocked Dependencies)

```bash
cd /home/anik/code/BGP-Sentry/tests
python3 test_p2p_timeout_and_sampling.py
```

**Expected Output:**
```
test_regular_transaction_timeout_60_seconds ... ok
test_attack_transaction_timeout_180_seconds ... ok
test_insufficient_consensus_status ... ok
test_sampling_skip_within_1_hour ... ok
test_sampling_record_after_1_hour ... ok
test_attack_bypass_sampling ... ok
test_reject_duplicate_vote_from_same_as ... ok
test_reject_vote_overflow ... ok
test_accept_unique_votes_from_different_nodes ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.245s

OK
```

---

### Manual Integration Tests (Real Environment)

```bash
cd /home/anik/code/BGP-Sentry/tests
python3 manual_test_timeout_sampling.py
```

**Expected Output:**
```
======================================================================
TEST 1: Transaction Timeout Mechanism
======================================================================
[1A] Testing regular transaction timeout (60 seconds)...
Waiting 70 seconds for timeout...
✅ SUCCESS: Regular transaction timed out and was committed

[1B] Testing attack transaction timeout (180 seconds)...
Waiting 70 seconds (should NOT timeout yet)...
✅ SUCCESS: Attack transaction did NOT timeout at 70 seconds
Waiting another 120 seconds...
✅ SUCCESS: Attack transaction timed out at 180+ seconds

======================================================================
TEST 2: Sampling Logic (1-hour window)
======================================================================
[2A] Recording first observation...
✅ SUCCESS: First observation recorded

[2B] Trying to record duplicate observation...
✅ SUCCESS: Duplicate observation was skipped (sampling)

[2C] Recording different observation...
✅ SUCCESS: Different observation recorded

[2D] Recording attack...
✅ SUCCESS: Attack observation recorded (bypassed sampling)

======================================================================
TEST 3: Vote Deduplication
======================================================================
[3A] Simulating vote from AS3...
✅ SUCCESS: Vote from AS3 accepted (count=1)

[3B] Simulating DUPLICATE vote from AS3...
✅ SUCCESS: Duplicate vote rejected (count still 1)

[3C] Simulating votes from AS5 and AS7...
✅ SUCCESS: Unique votes accepted (total count=3)
```

---

## Performance Benchmarks

### Cache Lookup Performance

**Requirement:** O(1) lookup for sampling check

**Test:**
```python
# Measure cache lookup time
import time

cache_key = ("203.0.113.0/24", 12)
start = time.perf_counter()
result = cache_key in pool.last_seen_cache
end = time.perf_counter()

lookup_time_us = (end - start) * 1_000_000
```

**Expected:**
- Cache lookup: <1μs (microsecond)
- Blockchain scan: ~100ms (100,000μs)
- Speedup: 100,000x faster

---

### Timeout Thread Performance

**Requirement:** Check timeouts every 30 seconds without blocking

**Test:**
- Add 100 pending transactions
- Measure timeout check duration

**Expected:**
- Timeout check: <10ms for 100 transactions
- No lock contention (uses "decide inside lock, execute outside lock" pattern)

---

## Verification Checklist

After running tests, verify the following in blockchain data:

### Blockchain Files to Check

**Path:** `nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json`

```json
{
  "transaction_id": "tx_...",
  "consensus_status": "SINGLE_WITNESS",  // ← Verify this field
  "approve_count": 0,
  "timeout_commit": true,               // ← Verify timeout flag
  "signatures": []
}
```

### State Files to Check

**Path:** `nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/last_seen_announcements.json`

```json
{
  "version": "1.0",
  "last_updated": "2025-10-21T14:30:00",
  "cache": {
    "203.0.113.0/24|12": 1729516200.123456  // ← Verify cache entries
  }
}
```

### Knowledge Base File

**Path:** `nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/knowledge_base.json`

```json
{
  "version": "1.0",
  "window_seconds": 480,  // ← Verify 8-minute window
  "observation_count": 5,
  "observations": [
    {
      "ip_prefix": "203.0.113.0/24",
      "sender_asn": 12,
      "is_attack": false,  // ← Verify attack flag
      "observed_at": "2025-10-21T14:25:00"
    }
  ]
}
```

---

## Troubleshooting

### Issue: Transactions not timing out

**Symptoms:**
- Pending transactions remain in memory indefinitely
- Buffer overflow warnings

**Debug:**
```python
# Check timeout thread status
print(pool.running)  # Should be True

# Check pending votes
print(pool.pending_votes)  # Should show created_at timestamps

# Check timeout configuration
print(pool.REGULAR_TIMEOUT)  # Should be 60
print(pool.ATTACK_TIMEOUT)   # Should be 180
```

**Solution:**
- Verify timeout thread started in `__init__`
- Check `created_at` timestamp is set in `broadcast_transaction`

---

### Issue: Sampling not working (duplicates recorded)

**Symptoms:**
- Same announcement recorded multiple times within 1 hour
- Blockchain bloat

**Debug:**
```python
# Check cache
print(pool.last_seen_cache)

# Check if sampling check is called
# Add debug logging to _check_recent_announcement_in_cache
```

**Solution:**
- Verify `is_attack=False` for regular announcements
- Check cache key format: `(ip_prefix, sender_asn)` tuple

---

### Issue: Vote replay attack not prevented

**Symptoms:**
- Same AS voting multiple times
- Vote count exceeds expected

**Debug:**
```python
# Check votes for transaction
tx_id = "tx_..."
votes = pool.pending_votes[tx_id]["votes"]
print([v["from_as"] for v in votes])  # Should have no duplicates
```

**Solution:**
- Verify deduplication code in `_handle_vote_response`
- Check `existing_voters` list before appending

---

## Conclusion

These test scenarios comprehensively verify:

1. ✅ **Timeout Mechanism**: Prevents buffer overflow, handles 60s/180s timeouts
2. ✅ **Sampling Logic**: Reduces blockchain bloat, O(1) performance, attack bypass
3. ✅ **Vote Deduplication**: Prevents replay attacks, enforces uniqueness

**All systems operational and secure.**
