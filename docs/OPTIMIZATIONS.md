# Performance Optimizations for Real-Time BGP Processing

This document details all performance optimizations implemented in BGP-Sentry to achieve real-time processing of BGP announcements through the blockchain consensus pipeline.

## Problem Statement

BGP-Sentry must process BGP announcements in real-time: if the dataset spans 28 minutes of BGP activity, the simulation must complete within 28 minutes of wall-clock time. Each RPKI node must:

1. Receive a BGP announcement
2. Validate via RPKI (VRP lookup)
3. Add to knowledge base
4. Create a blockchain transaction
5. Broadcast to peers for consensus voting
6. Collect votes (BFT threshold: 3-5 signatures)
7. Write the committed block to blockchain
8. Replicate block to all peers
9. Run attack detection on committed transaction
10. Award BGPCOIN rewards

All 10 steps must complete fast enough that nodes don't fall behind the real-time clock.

## Baseline Performance (Before Optimization)

With 100 nodes (58 RPKI validators, 42 non-RPKI observers) and ~7,000 observations:

| Metric | Value |
|--------|-------|
| Node lag from clock | **383 seconds** (6+ minutes behind) |
| Avg TPS per node | ~0.3 |
| Consensus timeout (regular) | 30 seconds |
| Consensus timeout (attack) | 60 seconds |
| Timeout check interval | 10 seconds |
| Broadcast peers | 10 |
| Message delivery | Synchronous (blocking caller) |
| Block replication | Synchronous (blocking commit path) |
| Attack detection | Synchronous (blocking commit path) |

The system was **not real-time viable** at baseline.

## Optimizations Implemented

### 1. Consensus Timeout Reduction

**File:** `.env`

| Parameter | Before | After | Rationale |
|-----------|--------|-------|-----------|
| `P2P_REGULAR_TIMEOUT` | 30s | 3s | In-memory message bus delivers votes in <100ms. 3s is generous. |
| `P2P_ATTACK_TIMEOUT` | 60s | 5s | Attack transactions are high priority but still resolve quickly. |

**Impact:** Transactions that don't reach consensus no longer block the pipeline for 30-60 seconds. They time out after 3-5 seconds and are written with their partial consensus status (CONFIRMED, INSUFFICIENT_CONSENSUS, or SINGLE_WITNESS).

### 2. Timeout Check Frequency

**File:** `p2p_transaction_pool.py` — `_cleanup_timed_out_transactions()`

| Parameter | Before | After | Rationale |
|-----------|--------|-------|-----------|
| Initial wait | 10s | 1s | Start checking sooner after server starts. |
| Check interval | 10s | 0.5s | Match the reduced timeout values. A 3s timeout with 10s checks means effective timeout is 10-13s. |

**Impact:** Timed-out transactions are detected and resolved within 0.5s of expiry instead of up to 10s.

### 3. Async Attack Detection

**File:** `p2p_transaction_pool.py` — `_commit_to_blockchain()`

**Before:**
```python
# Attack detection ran synchronously after commit
self._trigger_attack_detection(transaction, transaction_id)
```

**After:**
```python
# Attack detection runs in a background thread
threading.Thread(
    target=self._trigger_attack_detection,
    args=(transaction, transaction_id),
    daemon=True,
).start()
```

**Impact:** The commit path no longer waits for attack detection (which involves detector logic + attack consensus proposal + voting). The block is committed and the node moves on immediately.

### 4. Async Message Bus Delivery

**File:** `message_bus.py` — `InMemoryMessageBus`

**Before:**
```python
def send(self, from_as, to_as, message):
    handler = self.handlers.get(to_as)
    if handler is not None:
        handler(message)  # Blocks the sender until handler completes
```

**After:**
```python
def __init__(self):
    self._executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="MsgBus")

def send(self, from_as, to_as, message):
    handler = self.handlers.get(to_as)
    if handler is not None:
        self._executor.submit(self._dispatch, handler, to_as, message)
```

**Impact:** When node A broadcasts a vote request to nodes B, C, D, E, F — node A no longer waits for each handler to complete sequentially. All 5 handlers execute concurrently in the thread pool. This is critical because each handler involves knowledge base lookup + Ed25519 signing + vote response.

**Thread pool size:** 16 workers. With 5 broadcast peers per transaction, this allows ~3 concurrent transactions to have all their vote requests in flight simultaneously.

### 5. Reduced Broadcast Peers

**File:** `.env`

| Parameter | Before | After | Rationale |
|-----------|--------|-------|-----------|
| `P2P_MAX_BROADCAST_PEERS` | 10 | 5 | Consensus threshold is 3 signatures. Broadcasting to 5 peers gives 66% headroom while halving message volume. |

**Impact:** Each transaction generates 5 vote requests instead of 10, reducing total P2P message volume by ~50%. This reduces thread contention and lock pressure on the message bus.

### 6. Async Block Replication

**File:** `p2p_transaction_pool.py` — `_replicate_block_to_peers()`

**Before:**
```python
def _replicate_block_to_peers(self, block):
    bus = InMemoryMessageBus.get_instance()
    message = {"type": "block_replicate", "from_as": self.as_number, "block": block}
    bus.broadcast(self.as_number, message)  # Blocks until all peers receive
```

**After:**
```python
def _replicate_block_to_peers(self, block):
    threading.Thread(
        target=self._do_replicate_block,
        args=(block,),
        daemon=True,
    ).start()
```

**Impact:** Block replication to N-1 peers (broadcasting the full committed block) happens in the background. The committing node can immediately process the next transaction.

### 7. Probabilistic Buffer Sampling

**File:** `virtual_node.py` — `_PriorityBuffer`

Each node has an ingestion buffer for non-attack BGP announcements. To prevent the buffer from filling completely (which would cause hard drops), probabilistic sampling starts at 60% capacity:

```python
SAMPLE_THRESHOLD = 0.6  # Start sampling at 60% full

def try_add(self, obs):
    fill = len(self._queue) / self.max_size
    if fill >= 1.0:
        return False  # Hard cap
    if fill >= self.SAMPLE_THRESHOLD:
        # Linear ramp: 0% drop at 60%, 100% drop at 100%
        drop_prob = (fill - 0.6) / (1.0 - 0.6)
        if random() < drop_prob:
            return False
    self._queue.append(obs)
    return True
```

**Key:** Attack observations bypass the buffer entirely and are always processed.

**Impact:** Graceful degradation under load instead of hard buffer overflow. The dashboard shows `buffer_sampled` counts per node to monitor this.

## Performance After Optimization

With 100 nodes (58 RPKI validators, 42 non-RPKI observers) and ~7,000 observations:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Node lag from clock | 383s | ~4s | **~96x** |
| Avg TPS per node | ~0.3 | ~1.4 | **~4.7x** |
| Effective consensus time | 10-30s | 0.5-3s | **~10x** |
| Message throughput | Sequential | Concurrent (16 threads) | **~5x** |
| Commit path blocking | ~5-10s | <100ms | **~50x** |

The system now processes BGP announcements in real-time with ~4 seconds of lag — well within acceptable bounds for a simulation.

## Real-Time Monitoring Dashboard

A Flask-based dashboard (`monitoring/dashboard_server.py`) runs at `http://localhost:5555` during experiments and provides live visibility into:

- **Countdown timer** — elapsed / total / remaining time based on dataset timestamp span
- **Three timestamp progress bars** — Simulation Clock (blue), Average Node (orange), Slowest Node (red)
- **Lag indicator** — shows if nodes are keeping up with real-time
- **Per-RPKI-node health bars** — individual node lag from clock
- **TPS over time chart** — throughput trend across the experiment
- **Avg Node Lag over time chart** — historical lag to detect degradation
- **RPKI node table** — processed/total, TPS, buffer drops per node

Time-series data is collected every 5 seconds and saved to `monitoring_timeseries.json` in the results directory for post-experiment analysis.

## Future Optimization Opportunities

### Transaction Batching (Investigated, Not Implemented)

Batching multiple BGP announcements into a single blockchain transaction was investigated but deemed inappropriate for this system:

- Each BGP announcement is from a different origin AS about a different prefix
- Announcements arrive asynchronously from different vantage points
- Consensus votes are per-announcement (a node may approve one prefix but reject another)
- Batching would conflate independent security decisions

If a future use case requires batching (e.g., bulk import of historical data), it could be implemented as a separate "batch mode" that bypasses real-time consensus.

### 8. Ed25519 Signatures (Implemented)

**File:** `signature_utils.py`

Replaced RSA-2048 with Ed25519 for all transaction signing and vote signing:

| Algorithm | Sign | Verify | Key Gen | Key Size |
|-----------|------|--------|---------|----------|
| RSA-2048 (before) | ~1ms | ~0.05ms | ~50ms | 256 bytes |
| Ed25519 (after) | ~0.05ms | ~0.1ms | ~0.05ms | 32 bytes |

**Impact:** Key generation is ~100x faster (matters at startup with 58 nodes), signing is ~20x faster (matters on every transaction and vote). Keys remain in RAM (fastest possible — disk I/O would add ~0.1ms per access).

### 9. Early-Skip Deduplication (Implemented)

**File:** `virtual_node.py`

Moved dedup check to Step 0 — the very first thing in the pipeline, before any expensive operations:

**Before (late dedup):**
```
1. Add to knowledge base       ← wasted work on duplicates
2. RPKI validation (VRP)       ← wasted work on duplicates
3. Attack detection (4 types)  ← wasted work on duplicates
4. Dedup check                 ← too late!
5. Create transaction + broadcast
```

**After (early skip):**
```
0. Dedup check (is_attack? → never skip)  ← FIRST!
   If same (prefix, origin) seen within skip window → skip everything
1. Add to knowledge base
2. RPKI validation (VRP)
3. Attack detection (4 types)
4. Create transaction + broadcast
```

**Skip windows (from `.env`):**
- RPKI nodes: 300 seconds (5 minutes) — each legitimate (prefix, origin) processed at most ~5-6 times in a 28-min simulation
- Non-RPKI nodes: 120 seconds (2 minutes)
- Attacks: **NEVER skipped** — always processed immediately

**Impact:** Reduces total transactions created by ~60-80%, meaning far fewer consensus rounds, fewer P2P messages, and less blockchain write I/O.

### Future: Lock-Free Data Structures

The `pending_votes` dictionary uses a threading lock. At high contention (500+ concurrent transactions), this could become a bottleneck. Options:

- `concurrent.futures` based approach with per-transaction locks instead of global lock
- Lock-free queue for vote responses (CAS-based)
- Sharded pending_votes by transaction ID hash

### Connection Pooling for Block Replication

Currently each block replication creates a new background thread. A dedicated replication thread with a queue would reduce thread creation overhead:

```python
# Instead of: threading.Thread(target=...).start() per block
# Use: self._replication_queue.put(block) -> single worker drains queue
```

## Configuration Reference

All performance-related parameters in `.env`:

```bash
# Consensus timeouts (seconds)
P2P_REGULAR_TIMEOUT=3          # Regular BGP announcement consensus timeout
P2P_ATTACK_TIMEOUT=5           # Attack transaction consensus timeout

# Broadcast scope
P2P_MAX_BROADCAST_PEERS=5      # Max peers per broadcast (consensus threshold is 3)

# Buffer management
INGESTION_BUFFER_MAX_SIZE=1000  # Per-node buffer for non-attack announcements
# Buffer sampling starts at 60% (hardcoded in _PriorityBuffer.SAMPLE_THRESHOLD)

# Early-skip dedup windows (seconds)
RPKI_DEDUP_WINDOW=300          # RPKI: skip same (prefix, origin) within 5 min
NONRPKI_DEDUP_WINDOW=120       # Non-RPKI: skip within 2 min
SAMPLING_WINDOW_SECONDS=300    # P2P pool sampling window (matches RPKI)

# Capacity limits (prevent unbounded memory growth)
PENDING_VOTES_MAX_CAPACITY=5000
COMMITTED_TX_MAX_SIZE=50000
KNOWLEDGE_BASE_MAX_SIZE=50000
LAST_SEEN_CACHE_MAX_SIZE=100000
```
