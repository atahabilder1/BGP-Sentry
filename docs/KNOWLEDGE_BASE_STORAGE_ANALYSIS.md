# Knowledge Base Storage Analysis

## Storage Options for Voting Knowledge Base

### Option 1: In-Memory Only (Current Implementation) ⚠️

**Location**: RAM only, no persistence

**Pros:**
- ✅ Fastest lookups (O(1) list iteration)
- ✅ Simple implementation
- ✅ No disk I/O overhead
- ✅ Automatic cleanup on restart

**Cons:**
- ❌ Lost on node restart/crash
- ❌ Can't audit historical voting decisions
- ❌ No forensic analysis capability
- ❌ Race condition: if node restarts during active voting

**Use Case**: Development/testing only

---

### Option 2: File-Based JSON (RECOMMENDED) ✅

**Location**: `blockchain_data/state/knowledge_base.json`

**Structure:**
```json
{
  "version": "1.0",
  "last_updated": "2025-10-21T13:45:30",
  "window_seconds": 300,
  "observations": [
    {
      "ip_prefix": "203.0.113.0/24",
      "sender_asn": 12,
      "timestamp": "2025-07-27T21:00:00Z",
      "trust_score": 50.0,
      "observed_at": "2025-10-21T13:37:17",
      "observation_id": "obs_12345"
    }
  ]
}
```

**Pros:**
- ✅ Persists across restarts
- ✅ Easy to inspect/debug (human-readable)
- ✅ Follows existing state folder pattern
- ✅ Can be backed up/versioned
- ✅ Forensic analysis possible
- ✅ Fast with in-memory cache

**Cons:**
- ⚠️ Requires periodic saves to disk
- ⚠️ Potential data loss if crash between saves
- ⚠️ File locking needed for concurrent access

**Implementation Strategy:**
1. Load from disk on startup
2. Keep in-memory for fast lookups
3. Save to disk every 60 seconds
4. Save on graceful shutdown
5. Use atomic writes (temp file + rename)

**Use Case**: **PRODUCTION RECOMMENDED**

---

### Option 3: SQLite Database

**Location**: `blockchain_data/state/knowledge.db`

**Schema:**
```sql
CREATE TABLE observations (
    observation_id TEXT PRIMARY KEY,
    ip_prefix TEXT NOT NULL,
    sender_asn INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    trust_score REAL,
    observed_at TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prefix_asn ON observations(ip_prefix, sender_asn);
CREATE INDEX idx_observed_at ON observations(observed_at);
```

**Pros:**
- ✅ Fast indexed queries (O(log n))
- ✅ Efficient time-based cleanup with SQL: `DELETE WHERE observed_at < ?`
- ✅ ACID guarantees (atomic, consistent, isolated, durable)
- ✅ Can query historical patterns
- ✅ Better for large knowledge bases (>1000 observations)
- ✅ Built-in concurrency control

**Cons:**
- ❌ More complex implementation
- ❌ Requires SQLite library
- ❌ Less human-readable
- ❌ Overkill for small datasets

**Use Case**: High-throughput production with >100 announcements/minute

---

### Option 4: Rebuild from Blockchain

**Location**: No separate storage, derive from `blockchain.json`

**Approach:**
- On startup, scan last 5 minutes of blockchain transactions
- Extract observations that this node created
- Rebuild knowledge base from blockchain history

**Pros:**
- ✅ No separate storage needed
- ✅ Always consistent with blockchain
- ✅ Can't get out of sync
- ✅ Space efficient

**Cons:**
- ❌ Slow startup (must scan blockchain)
- ❌ Misses observations that didn't reach consensus
- ❌ Only includes this node's transactions, not all observations
- ❌ No record of rejected votes

**Use Case**: Disaster recovery fallback only

---

### Option 5: Redis (In-Memory Database)

**Location**: Redis server with TTL keys

**Structure:**
```
Key: obs:203.0.113.0/24:12:2025-07-27T21:00:00Z
Value: {"trust_score": 50.0, "observed_at": "2025-10-21T13:37:17"}
TTL: 300 seconds (auto-expire)
```

**Pros:**
- ✅ Extremely fast (in-memory)
- ✅ Automatic expiration with TTL
- ✅ Built-in persistence options (RDB/AOF)
- ✅ Distributed caching possible
- ✅ No manual cleanup needed

**Cons:**
- ❌ Requires separate Redis service
- ❌ Additional infrastructure complexity
- ❌ Overkill for single-node deployment
- ❌ Network overhead

**Use Case**: Multi-datacenter deployments with shared knowledge base

---

## Recommended Implementation: Hybrid File-Based

### Architecture

```
┌─────────────────────────────────────────┐
│  In-Memory Knowledge Base (Fast)        │
│  - List of observations                 │
│  - Thread-safe with locks              │
│  - Used for all vote validation        │
└─────────────┬───────────────────────────┘
              │
              │ Sync every 60s
              │ + on shutdown
              ↓
┌─────────────────────────────────────────┐
│  Persistent Storage (Crash-Safe)        │
│  blockchain_data/state/                 │
│  └── knowledge_base.json                │
└─────────────────────────────────────────┘
```

### Directory Structure

```
blockchain_data/
├── chain/                          ← Immutable blockchain
│   ├── blockchain.json
│   ├── bgp_stream.jsonl
│   └── trust_log.jsonl
└── state/                          ← Derived query state
    ├── ip_asn_mapping.json         (existing)
    └── knowledge_base.json         (NEW)
```

### Benefits of This Approach

1. **Performance**: In-memory lookups during voting (~1ms)
2. **Persistence**: Survives crashes with <60s data loss
3. **Simplicity**: No external dependencies
4. **Debuggability**: Human-readable JSON files
5. **Consistency**: Aligns with existing state folder pattern
6. **Recovery**: Can rebuild from blockchain if needed

---

## Storage Size Analysis

### Typical Knowledge Base Size

**Assumptions:**
- Window: 5 minutes (300 seconds)
- Announcement rate: 1 every 30 seconds
- Observations per window: 300/30 = 10 observations

**Per Observation:**
```json
{
  "ip_prefix": "203.0.113.0/24",          // ~20 bytes
  "sender_asn": 12,                       // ~4 bytes
  "timestamp": "2025-07-27T21:00:00Z",    // ~25 bytes
  "trust_score": 50.0,                    // ~8 bytes
  "observed_at": "2025-10-21T13:37:17",   // ~25 bytes
  "observation_id": "obs_12345"           // ~15 bytes
}
// Total: ~150 bytes per observation (with JSON overhead: ~200 bytes)
```

**Total Storage:**
- 10 observations × 200 bytes = **2 KB per node**
- 9 nodes × 2 KB = **18 KB total**

**Conclusion:** Storage is negligible, file-based approach is perfectly fine.

---

## Disaster Recovery Considerations

### Scenario 1: Node Crashes During Voting

**With In-Memory Only:**
- ❌ Knowledge base lost
- ❌ Can't vote on pending transactions
- ❌ Must wait for new observations

**With File Persistence:**
- ✅ Load knowledge base from disk
- ✅ Can vote on transactions immediately
- ⚠️ May lose last 60 seconds of observations

### Scenario 2: Corrupted Knowledge Base File

**Recovery Steps:**
1. Detect corruption on load (JSON parse error)
2. Rename corrupted file: `knowledge_base.json.corrupted`
3. Initialize empty knowledge base
4. Log warning: "Knowledge base corrupted, starting fresh"
5. Continue operation (observations rebuild naturally)

### Scenario 3: Disk Full

**Graceful Degradation:**
- Continue operation in-memory mode
- Log error: "Cannot save knowledge base: disk full"
- Voting still works (uses in-memory data)
- Warning: "Knowledge will be lost on restart"

---

## Recommendation Summary

### For Development/Testing:
**Option 1**: In-Memory Only
- Simple, no persistence needed
- Fast iteration

### For Production (Small-Medium Scale):
**Option 2**: File-Based JSON ✅ **RECOMMENDED**
- Perfect balance of simplicity and reliability
- Aligns with existing architecture
- Easy to debug and inspect

### For Production (Large Scale):
**Option 3**: SQLite Database
- If handling >100 announcements/minute
- If need historical analysis
- If knowledge base grows >1000 observations

### For Distributed Deployments:
**Option 5**: Redis with TTL
- Multi-datacenter scenarios
- Shared knowledge base across regions
- Advanced caching requirements

---

## Implementation Checklist

If implementing File-Based JSON persistence:

- [ ] Create `knowledge_base.json` in state folder
- [ ] Load knowledge base on startup
- [ ] Periodic save every 60 seconds
- [ ] Save on graceful shutdown
- [ ] Atomic writes (temp file + rename)
- [ ] Handle file corruption gracefully
- [ ] Log all persistence operations
- [ ] Add recovery from blockchain fallback
- [ ] Document knowledge base format
- [ ] Add metrics (save time, file size, load time)

