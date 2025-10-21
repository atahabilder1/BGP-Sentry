# Voting Knowledge Storage - Final Recommendation

## Summary

**RECOMMENDED LOCATION**: `blockchain_data/state/knowledge_base.json`

Each node stores its voting knowledge base in:
```
nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/knowledge_base.json
nodes/rpki_nodes/as03/blockchain_node/blockchain_data/state/knowledge_base.json
nodes/rpki_nodes/as05/blockchain_node/blockchain_data/state/knowledge_base.json
...
```

## Why This Location?

### 1. Architectural Consistency ✅

Your existing architecture already uses the `state/` folder for derived query data:

```
blockchain_data/
├── chain/                      ← Immutable blockchain history
│   ├── blockchain.json
│   ├── bgp_stream.jsonl
│   └── trust_log.jsonl
└── state/                      ← Derived state for fast queries
    ├── ip_asn_mapping.json     (existing - IP prefix lookups)
    └── knowledge_base.json     (NEW - voting observations)
```

**Knowledge base is "state" data** because:
- It's derived from observations (not primary data)
- It's time-windowed and ephemeral (5-minute window)
- It's used for fast queries during voting
- It can be rebuilt if lost (from new observations)

### 2. Per-Node Storage ✅

Each node has its **own independent knowledge base**:

```
AS01 observes: 203.0.113.0/24 from AS12 at T=100
AS03 observes: 203.0.113.0/24 from AS12 at T=102  (slightly different time)
AS05 observes: 198.51.100.0/24 from AS15 at T=105 (different announcement)
```

**Why per-node?**
- Each node observes BGP announcements independently
- Network propagation causes slight timing differences
- Observations are used to validate voting decisions
- No need for shared/centralized storage

### 3. Persistence Strategy ✅

**Hybrid Approach**: In-Memory + Periodic Disk Saves

```
┌──────────────────────────────────┐
│  In-Memory (Fast Voting)         │
│  - All vote checks use RAM       │
│  - Thread-safe with locks        │
│  - <1ms lookup time             │
└────────────┬─────────────────────┘
             │
             │ Save every 60s
             │ + on shutdown
             ↓
┌──────────────────────────────────┐
│  Disk Storage (Crash Recovery)   │
│  state/knowledge_base.json       │
│  - Atomic writes (temp + rename) │
│  - Survives node crashes         │
│  - Data loss ≤60 seconds         │
└──────────────────────────────────┘
```

**Benefits:**
1. **Performance**: In-memory voting is fast (~1ms)
2. **Persistence**: Survives crashes with minimal loss
3. **Simplicity**: No external dependencies (Redis, etc.)
4. **Debuggability**: Human-readable JSON format

## File Format

### Structure

```json
{
  "version": "1.0",
  "as_number": 1,
  "last_updated": "2025-10-21T13:45:30.123456",
  "window_seconds": 300,
  "observation_count": 2,
  "observations": [
    {
      "ip_prefix": "203.0.113.0/24",
      "sender_asn": 12,
      "timestamp": "2025-07-27T21:00:00Z",
      "trust_score": 50.0,
      "observed_at": "2025-10-21T13:37:17.123456"
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | File format version (for future compatibility) |
| `as_number` | integer | AS number of this node |
| `last_updated` | ISO 8601 | When file was last saved |
| `window_seconds` | integer | Time window in seconds (300 = 5 minutes) |
| `observation_count` | integer | Number of observations in array |
| `observations` | array | List of BGP observations |
| `observations[].ip_prefix` | string | IP prefix announced |
| `observations[].sender_asn` | integer | AS that made announcement |
| `observations[].timestamp` | ISO 8601 | When announcement occurred |
| `observations[].trust_score` | float | Trust score at observation time |
| `observations[].observed_at` | ISO 8601 | When this node observed it |

## Implementation Details

### Initialization (Startup)

```python
def __init__(self, as_number):
    # Set file location
    self.knowledge_base_file = self.blockchain.state_dir / "knowledge_base.json"

    # Load from disk
    self._load_knowledge_base()

    # Start background threads
    - Cleanup thread (remove old observations)
    - Periodic save thread (save every 60s)
```

### Load from Disk

```python
def _load_knowledge_base(self):
    """Load knowledge base from disk, filter expired observations"""
    if file.exists():
        data = json.load(file)
        observations = data['observations']

        # Filter out expired observations
        current_time = now()
        valid = [obs for obs in observations
                 if age(obs) <= window_seconds]

        self.knowledge_base = valid
        logger.info(f"Loaded {len(valid)} observations")
```

### Save to Disk (Atomic)

```python
def _save_knowledge_base(self):
    """Save atomically using temp file + rename"""
    data = {
        "version": "1.0",
        "observations": self.knowledge_base
    }

    # Write to temp file
    with open("knowledge_base.tmp", "w") as f:
        json.dump(data, f)

    # Atomic rename
    os.rename("knowledge_base.tmp", "knowledge_base.json")
```

### Periodic Save (Background Thread)

```python
def _periodic_save_knowledge_base(self):
    """Save every 60 seconds"""
    while self.running:
        time.sleep(60)
        self._save_knowledge_base()
```

### Graceful Shutdown

```python
def stop(self):
    """Save before shutdown"""
    self.running = False
    self._save_knowledge_base()  # Final save
    self.server_socket.close()
```

## Storage Requirements

### Per-Node Capacity

**Typical Scenario:**
- Window: 5 minutes (300 seconds)
- Announcement rate: 1 per 30 seconds
- Observations per window: 10

**Storage per observation:**
```
{
  "ip_prefix": "203.0.113.0/24",      ~20 bytes
  "sender_asn": 12,                   ~4 bytes
  "timestamp": "2025-07-27T21:00:00Z" ~25 bytes
  "trust_score": 50.0,                ~8 bytes
  "observed_at": "2025-10-21T13:37:17" ~25 bytes
}
Total: ~150 bytes + JSON overhead = ~200 bytes/observation
```

**Total per node:**
- 10 observations × 200 bytes = **2 KB per node**
- 9 nodes × 2 KB = **18 KB total** (negligible)

### High-Traffic Scenario

**Extreme Case:**
- Window: 5 minutes
- Announcement rate: 10 per second (very high)
- Observations: 3000

**Storage:**
- 3000 × 200 bytes = **600 KB per node**
- Still very manageable for JSON file

## Disaster Recovery

### Scenario 1: Node Crash

**Without Persistence:**
```
Node crashes → Knowledge base lost
Node restarts → Empty knowledge base
Result: Cannot vote on pending transactions until new observations
```

**With File Persistence:**
```
Node crashes → Last save ≤60s ago preserved
Node restarts → Loads knowledge base from disk
Result: Can immediately vote on transactions with recent knowledge
Data Loss: ≤60 seconds of observations
```

### Scenario 2: Corrupted File

**Detection and Recovery:**
```python
try:
    data = json.load(file)
except JSONDecodeError:
    # File corrupted
    os.rename(file, "knowledge_base.json.corrupted")
    logger.warning("Corrupted file saved for forensics")
    self.knowledge_base = []  # Start fresh
```

**Impact:**
- Node starts with empty knowledge base
- New observations rebuild naturally
- Voting works as soon as first observation added
- Corrupted file preserved for debugging

### Scenario 3: Disk Full

**Graceful Degradation:**
```python
def _save_knowledge_base(self):
    try:
        # Save to disk
    except IOError as e:
        if "No space left" in str(e):
            logger.error("Disk full - knowledge base not saved!")
            logger.warning("Node continues in-memory only")
            # Voting still works (uses in-memory data)
```

**Impact:**
- Node continues operating in-memory mode
- Voting works normally
- Knowledge lost if node restarts
- Requires manual intervention (free disk space)

## Comparison with Alternatives

### Alternative 1: In-Memory Only

❌ **Not Recommended** - Knowledge lost on every restart

### Alternative 2: SQLite Database

✅ Good for high-scale, but overkill for current needs:
- Current: 10-100 observations per node
- SQLite beneficial when: >1000 observations

### Alternative 3: Redis

❌ **Not Recommended** - Requires external service
- Adds infrastructure complexity
- Only beneficial for multi-datacenter deployments

### Alternative 4: Rebuild from Blockchain

⚠️ **Partial Solution** - Can be used as fallback:
- Slow to rebuild (must scan blockchain)
- Only includes committed transactions
- Misses observations that didn't reach consensus

**Recommendation**: Use as disaster recovery fallback only

## Testing

### Verify File Location

```bash
cd /home/anik/code/BGP-Sentry
python3 nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/test_knowledge_persistence.py
```

### Check File After Node Runs

```bash
# View knowledge base for AS01
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/knowledge_base.json | jq
```

### Simulate Crash Recovery

```bash
# 1. Start node
# 2. Let it collect observations
# 3. Kill process (simulates crash)
kill -9 <pid>

# 4. Restart node
# 5. Check logs for:
#    "📂 Loaded X observations from knowledge base"
```

## Maintenance

### Log Monitoring

**Successful Operations:**
```
[AS01] 📚 Added to knowledge base: 203.0.113.0/24 from AS12
[AS01] 💾 Saved 10 observations to knowledge base
[AS01] 🧹 Cleaned 2 old observations from knowledge base
```

**Error Conditions:**
```
[AS01] ❌ Knowledge base file corrupted
[AS01] ⚠️  Corrupted file moved to: knowledge_base.json.corrupted
[AS01] ❌ Error saving knowledge base: No space left on device
```

### Cleanup Corrupted Files

```bash
# Find corrupted files
find nodes/rpki_nodes/*/blockchain_node/blockchain_data/state/ -name "*.corrupted"

# Remove old corrupted files (after investigation)
rm nodes/rpki_nodes/*/blockchain_node/blockchain_data/state/*.corrupted
```

### Backup Strategy

```bash
# Backup all knowledge bases
tar -czf knowledge_bases_backup.tar.gz \
  nodes/rpki_nodes/*/blockchain_node/blockchain_data/state/knowledge_base.json
```

## Future Enhancements

### 1. Compression (If Needed)

```python
import gzip
with gzip.open("knowledge_base.json.gz", "wt") as f:
    json.dump(data, f)
```

**When?** Only if observations exceed 10,000 per node

### 2. Versioned History

```bash
state/
├── knowledge_base.json         (current)
├── knowledge_base.2025-10-21.json  (daily archive)
└── knowledge_base.2025-10-20.json
```

**Use Case:** Forensic analysis of voting patterns

### 3. Metrics Dashboard

Track:
- Knowledge base size over time
- Observation rate
- Save duration
- Load duration
- Corruption events

## Conclusion

**Best place for voting knowledge: `blockchain_data/state/knowledge_base.json`**

✅ Aligns with existing architecture (state folder pattern)
✅ Per-node storage (matches observation model)
✅ Hybrid in-memory + disk (fast + persistent)
✅ Atomic writes (corruption-safe)
✅ Simple JSON format (debuggable)
✅ Automatic cleanup (bounded size)
✅ Crash recovery (≤60s data loss)

**Implementation Status:** ✅ Complete
- [x] File location defined
- [x] Load on startup
- [x] Periodic save (60s)
- [x] Graceful shutdown save
- [x] Corruption handling
- [x] Atomic writes
- [x] Expiration filtering
- [x] Test scripts provided

---

**References:**
- Implementation: `blockchain_utils/p2p_transaction_pool.py:396-500`
- Test Script: `blockchain_utils/test_knowledge_persistence.py`
- Architecture Analysis: `docs/KNOWLEDGE_BASE_STORAGE_ANALYSIS.md`
- Voting Documentation: `docs/KNOWLEDGE_BASED_VOTING.md`
