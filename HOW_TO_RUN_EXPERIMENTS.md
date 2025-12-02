# How to Run BGP-Sentry Experiments - Step-by-Step Guide

**Last Updated:** 2025-12-02
**For:** Running experiments, understanding data, and cleanup

---

## Table of Contents
1. [Quick Start (3 Commands)](#quick-start)
2. [Understanding Your Dataset](#understanding-your-dataset)
3. [What Gets Written to Blockchain](#what-gets-written-to-blockchain)
4. [Detailed Step-by-Step Guide](#detailed-step-by-step-guide)
5. [Cleanup Between Experiments](#cleanup-between-experiments)
6. [Monitoring Running Experiments](#monitoring-running-experiments)
7. [Analyzing Results](#analyzing-results)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start (3 Commands)

If you just want to run an experiment quickly:

```bash
# 1. Clean previous data (optional but recommended)
./cleanup_experiment.sh

# 2. Run experiment (50 seconds by default)
python3 main_experiment.py

# 3. Analyze results
python3 analysis/targeted_attack_analyzer.py test_experiment_results/
```

**Done!** Your experiment will run for 50 seconds and create blockchain with consensus data.

---

## Understanding Your Dataset

### What BGP Data Do You Have?

You currently have **~34,000 lines** of BGP log data from 18 routers (R1-R18).

**Location:** `bgp_feed/mininet_logs/`

**Files:**
```
R1-bgpd.log  - BGP daemon logs from Router 1
R1.log       - Router 1 system logs
R2-bgpd.log  - BGP daemon logs from Router 2
...
R18-bgpd.log - BGP daemon logs from Router 18
```

**Total:** 36 files (18 routers × 2 log types)

### BGP Log Format

Each BGP log contains announcements like:

```
2025/07/18 19:50:15.114606 BGP: [T5JFA-13199] subgroup_process_announce_selected: p=10.0.0.0/24, selected=0x567596fee690
2025/07/18 19:50:15.114686 BGP: [HVRWP-5R9NQ] u1:s1 send UPDATE 10.0.0.0/24 IPv4 unicast
2025/07/18 19:50:15.215104 BGP: [RZMGQ-A03CG] 9.0.1.2(bgpd-R4) rcvd UPDATE about 10.0.0.0/24 IPv4 unicast -- DENIED due to: as-path contains our own AS;
```

**Key Information Extracted:**
- **Timestamp:** When announcement happened
- **IP Prefix:** Which network is announced (e.g., `10.0.0.0/24`, `203.0.113.0/24`)
- **Sender ASN:** Which AS announced it
- **AS Path:** Route through which ASes
- **Action:** send UPDATE / rcvd UPDATE / DENIED

### How BGP Data Flows to Blockchain

```
BGP Logs (bgp_feed/mininet_logs/)
    ↓
BGP Observer (processes logs line by line)
    ↓
Creates Transaction (ip_prefix + sender_asn + timestamp)
    ↓
Broadcasts to 8 peers (P2P network)
    ↓
Collects Votes (needs 3/9 for consensus)
    ↓
Writes to Blockchain (on all 9 nodes)
```

**Example:** If Router R1 announces `203.0.113.0/24`, the system:
1. Parses the log line
2. Creates transaction: `{ip_prefix: "203.0.113.0/24", sender_asn: 12, ...}`
3. Broadcasts to peers (AS3, AS5, AS7, ...)
4. Collects votes (need 3+ "approve")
5. Writes to blockchain with consensus metadata

---

## What Gets Written to Blockchain

### Full Transaction Structure

When a BGP announcement reaches consensus, this is written to blockchain:

```json
{
  "transaction_id": "c36d91b6-3c1c-4755-ae4e-2903c59d846c",
  "observer_as": 1,
  "sender_asn": 12,
  "ip_prefix": "203.0.113.0/24",
  "timestamp": "2025-07-27T21:00:00Z",
  "trust_score": 50.0,
  "transaction_timestamp": "2025-12-02T20:42:09.377425+00:00",
  "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "signature": "test_signature_1_1764708129",
  "votes": [],
  "signatures": [
    {
      "from_as": 3,
      "vote": "approve",
      "timestamp": "2025-12-02T15:42:09.380309"
    },
    {
      "from_as": 11,
      "vote": "approve",
      "timestamp": "2025-12-02T15:42:09.380480"
    },
    {
      "from_as": 13,
      "vote": "approve",
      "timestamp": "2025-12-02T15:42:09.380852"
    }
  ],
  "consensus_reached": true,
  "signature_count": 3,
  "consensus_status": "CONFIRMED",      // Added if timeout
  "approve_count": 3,                    // Added if timeout
  "timeout_commit": false                // True if written due to timeout
}
```

### Data Fields Explained

| Field | Description | Always Present? |
|-------|-------------|-----------------|
| `transaction_id` | Unique UUID for this announcement | ✅ Yes |
| `observer_as` | Which RPKI node observed it | ✅ Yes |
| `sender_asn` | AS that announced the prefix | ✅ Yes |
| `ip_prefix` | Network announced (e.g., 203.0.113.0/24) | ✅ Yes |
| `timestamp` | When BGP announcement happened | ✅ Yes |
| `trust_score` | Reputation score for this AS | ✅ Yes |
| `transaction_timestamp` | When transaction created | ✅ Yes |
| `signatures` | List of votes from other nodes | ✅ Yes |
| `consensus_reached` | True if 3+ votes | ✅ Yes |
| `signature_count` | Total votes received | ✅ Yes |
| `consensus_status` | CONFIRMED / INSUFFICIENT_CONSENSUS / SINGLE_WITNESS | ⚠️ Only if timeout |
| `approve_count` | Number of "approve" votes | ⚠️ Only if timeout |
| `timeout_commit` | True if written due to timeout | ⚠️ Only if timeout |

### Is Full Data Written?

**Yes!** The blockchain contains:
- ✅ All BGP announcement metadata (prefix, AS, timestamp)
- ✅ All votes from peer nodes (who voted, when, approve/reject)
- ✅ Consensus status (3+ votes = confirmed)
- ✅ Chain integrity (previous_hash, block_hash, merkle_root)

**Not Included:**
- ❌ Raw BGP log lines (only parsed metadata)
- ❌ AS paths (could be added if needed)
- ❌ BGP attributes (MED, local-pref, communities)
- ❌ Full BGP UPDATE messages

**Why not everything?** To keep blockchain size manageable. You're storing **security-relevant metadata**, not full routing tables.

---

## Detailed Step-by-Step Guide

### Step 1: Check Current State

Before running an experiment, check what's already there:

```bash
# Check if blockchain exists
ls nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# Check blockchain size
jq '.metadata.total_blocks' nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# Check BGP data
ls -lh bgp_feed/mininet_logs/*.log
```

### Step 2: Clean Previous Experiment (Optional)

**When to clean:**
- Starting a fresh experiment
- Previous experiment crashed
- Want reproducible results

**When NOT to clean:**
- Continuing from previous state
- Testing fork resolution
- Analyzing existing data

```bash
# Option A: Use cleanup script (recommended)
./cleanup_experiment.sh

# Option B: Manual cleanup
find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/ -type f -name "*.json" -delete
find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/ -type f -name "*.log" -delete
rm -rf test_experiment_results/
rm experiment_test_run.log
```

### Step 3: Configure Experiment Duration

Edit the configuration file to set how long the experiment runs:

```bash
nano simulation_helpers/shared_data/experiment_config.json
```

**Change this line:**
```json
"max_duration": 50,     // Seconds to run experiment
```

**Recommended durations:**
- **Quick test:** 50 seconds (default)
- **Short run:** 300 seconds (5 minutes)
- **Medium run:** 1800 seconds (30 minutes)
- **Full run:** 3600 seconds (1 hour)

**Note:** Your BGP data covers several hours, so you can run long experiments!

### Step 4: Run the Experiment

```bash
python3 main_experiment.py
```

**What happens:**
1. **[0-2s]** Initialize 9 RPKI nodes
2. **[2-5s]** Start P2P servers on ports 8001-8017
3. **[5s-end]** Process BGP announcements:
   - Read from `bgp_feed/mininet_logs/`
   - Create transactions
   - Broadcast to peers
   - Collect votes (need 3/9)
   - Write to blockchain
   - Award BGPCOIN tokens
   - Detect attacks
4. **[end]** Graceful shutdown, save state

**You'll see output like:**
```
INFO:P2P-AS1:✅ Received signature from AS3 for c36d91b6...
INFO:P2P-AS1:Signatures collected: 3/3 for c36d91b6...
INFO:P2P-AS1:🎉 CONSENSUS REACHED (3/9) - Will write to blockchain!
INFO:P2P-AS1:⛓️  Transaction c36d91b6... committed to blockchain with 3 signatures
INFO:P2P-AS1:💰 BGPCOIN rewards distributed:
INFO:P2P-AS1:   Committer (AS1): 15.0 BGPCOIN
INFO:P2P-AS1:   Voter (AS3): 1.0 BGPCOIN
```

### Step 5: Wait for Completion

**Option A: Foreground (see live logs)**
```bash
# Just wait... logs scroll by
# Press Ctrl+C to stop early (not recommended)
```

**Option B: Background (run while you do other things)**
```bash
# Run in background
python3 main_experiment.py > experiment.log 2>&1 &

# Save process ID
echo $! > experiment_pid.txt

# Check if still running
ps -p $(cat experiment_pid.txt)

# Follow logs
tail -f experiment.log

# Check progress
grep "Transaction.*committed" experiment.log | wc -l
```

### Step 6: Verify Results

After experiment completes, verify blockchain was created:

```bash
# Check all nodes have blockchains
for node in as01 as03 as05 as07 as09 as11 as13 as15 as17; do
  blocks=$(jq '.metadata.total_blocks' nodes/rpki_nodes/$node/blockchain_node/blockchain_data/chain/blockchain.json)
  txs=$(jq '.metadata.total_transactions' nodes/rpki_nodes/$node/blockchain_node/blockchain_data/chain/blockchain.json)
  echo "$node: $blocks blocks, $txs transactions"
done
```

**Expected output:**
```
as01: 5 blocks, 4 transactions
as03: 5 blocks, 4 transactions
as05: 5 blocks, 4 transactions
as07: 5 blocks, 4 transactions
as09: 5 blocks, 4 transactions
as11: 5 blocks, 4 transactions
as13: 5 blocks, 4 transactions
as15: 5 blocks, 4 transactions
as17: 5 blocks, 4 transactions
```

✅ **All nodes should have IDENTICAL counts** (blockchain consensus working!)

### Step 7: Analyze Results

```bash
# Create results directory structure
mkdir -p test_experiment_results/nodes
for node in as01 as03 as05 as07 as09 as11 as13 as15 as17; do
  mkdir -p "test_experiment_results/nodes/${node}/blockchain_node/blockchain_data/chain"
  cp "nodes/rpki_nodes/${node}/blockchain_node/blockchain_data/chain/blockchain.json" \
     "test_experiment_results/nodes/${node}/blockchain_node/blockchain_data/chain/"
done

# Run post-hoc analysis
python3 analysis/targeted_attack_analyzer.py test_experiment_results/
```

**Analysis will show:**
- ✅ Consensus rate (% transactions with 3+ votes)
- ✅ SINGLE_WITNESS transactions (potential targeted attacks)
- ✅ INSUFFICIENT_CONSENSUS transactions (1-2 votes)
- ✅ Repeated attempts (route flapping)
- ✅ Temporal bursts (BGP storms)
- ✅ Cross-node consistency (fork detection)

---

## Cleanup Between Experiments

### What Needs Cleaning?

When you run multiple experiments, you need to clean:

1. **Blockchain files** - `.json` files in `blockchain_data/chain/`
2. **State files** - Knowledge base, BGPCOIN ledger, caches
3. **Log files** - Previous experiment logs
4. **Results directories** - Old analysis results

### Cleanup Script

Create this script to automate cleanup:

```bash
nano cleanup_experiment.sh
```

**Content:**
```bash
#!/bin/bash
# BGP-Sentry Experiment Cleanup Script

echo "🧹 Cleaning BGP-Sentry Experiment Data..."

# 1. Clean blockchain data
echo "[1/4] Removing blockchain files..."
find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/ -type f -name "*.json" -delete 2>/dev/null
find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/ -type f -name "*.log" -delete 2>/dev/null

# 2. Clean state directories
echo "[2/4] Removing state files..."
rm -rf nodes/rpki_nodes/as*/blockchain_node/blockchain_data/state/*.json 2>/dev/null

# 3. Clean experiment results
echo "[3/4] Removing old results..."
rm -rf test_experiment_results/ 2>/dev/null
rm -f experiment_test_run.log experiment_pid.txt 2>/dev/null

# 4. Clean backup directories
echo "[4/4] Removing backups..."
rm -rf backup_blockchain_* 2>/dev/null

echo "✅ Cleanup complete! Ready for new experiment."
echo ""
echo "Next steps:"
echo "  1. python3 main_experiment.py"
echo "  2. python3 analysis/targeted_attack_analyzer.py test_experiment_results/"
```

**Make it executable:**
```bash
chmod +x cleanup_experiment.sh
```

**Run it:**
```bash
./cleanup_experiment.sh
```

---

## Monitoring Running Experiments

### Real-Time Monitoring

**Option 1: Watch transaction commits**
```bash
# In separate terminal
tail -f experiment.log | grep "⛓️  Transaction"
```

**Option 2: Count transactions over time**
```bash
# Every 10 seconds, show transaction count
watch -n 10 'jq ".metadata.total_transactions" nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json'
```

**Option 3: Monitor consensus rate**
```bash
# Show consensus success messages
tail -f experiment.log | grep "🎉 CONSENSUS REACHED"
```

### Check Experiment Progress

```bash
# How many transactions processed?
grep "Transaction.*committed" experiment.log | wc -l

# What's the consensus rate?
grep "CONSENSUS REACHED" experiment.log | wc -l

# Any errors?
grep -i "error\|failed" experiment.log | grep -v "Failed to send vote" | wc -l

# Any timeouts?
grep "⏱️  Transaction.*timed out" experiment.log | wc -l
```

### Kill Running Experiment (Emergency)

```bash
# If you need to stop early
kill $(cat experiment_pid.txt)

# Or find and kill manually
ps aux | grep main_experiment.py
kill <PID>
```

---

## Analyzing Results

### Quick Analysis Commands

```bash
# 1. Show blockchain summary
jq '.metadata' nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# 2. Show all transactions
jq '.blocks[].transactions[]' nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# 3. Count consensus statuses
jq '[.blocks[].transactions[] | select(.consensus_status) | .consensus_status] | group_by(.) | map({status: .[0], count: length})' \
   nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# 4. Show SINGLE_WITNESS transactions
jq '.blocks[].transactions[] | select(.consensus_status == "SINGLE_WITNESS")' \
   nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# 5. Show all IP prefixes recorded
jq -r '.blocks[].transactions[].ip_prefix' nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json | sort -u
```

### Full Post-Hoc Analysis

```bash
# Prepare results
mkdir -p test_experiment_results/nodes
for node in as01 as03 as05 as07 as09 as11 as13 as15 as17; do
  mkdir -p "test_experiment_results/nodes/${node}/blockchain_node/blockchain_data/chain"
  cp "nodes/rpki_nodes/${node}/blockchain_node/blockchain_data/chain/blockchain.json" \
     "test_experiment_results/nodes/${node}/blockchain_node/blockchain_data/chain/"
done

# Run analysis
python3 analysis/targeted_attack_analyzer.py test_experiment_results/
```

**Output shows:**
- ✅ Consensus breakdown (CONFIRMED / INSUFFICIENT / SINGLE_WITNESS)
- ✅ Attack analysis (targeted attacks, network issues)
- ✅ Misbehavior patterns (repeated attempts, bursts, escalations)
- ✅ Cross-node consistency (fork detection)
- ✅ Recommendations (upgrade candidates, system health)

---

## Troubleshooting

### Problem: "Address already in use"

**Symptom:**
```
ERROR:P2P-AS1:Failed to start P2P server: [Errno 98] Address already in use
```

**Cause:** Previous experiment didn't shut down cleanly, ports still bound

**Solution:**
```bash
# Kill all Python processes
pkill -f main_experiment.py

# Wait a few seconds
sleep 5

# Try again
python3 main_experiment.py
```

### Problem: "No blockchain data found"

**Symptom:** Analysis shows "No blockchain data found"

**Cause:** Blockchain path is wrong or experiment didn't create files

**Solution:**
```bash
# Check if blockchain exists
ls nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# If not, experiment didn't run properly
# Check experiment logs
tail -100 experiment.log

# Try running again
python3 main_experiment.py
```

### Problem: All transactions are SINGLE_WITNESS

**Symptom:** Post-hoc analysis shows 100% SINGLE_WITNESS (0 votes)

**Cause:** Nodes couldn't communicate (P2P network failed)

**Solution:**
```bash
# Check P2P server logs
grep "P2P server started" experiment.log

# Should see 9 messages (one per node)
# If not, check firewall or port availability

# Check vote collection
grep "Received signature" experiment.log | wc -l

# Should see many vote messages
```

### Problem: Blockchain sizes differ across nodes

**Symptom:**
```
as01: 5 blocks, 4 transactions
as03: 5 blocks, 3 transactions  ← DIFFERENT!
```

**Cause:** Blockchain fork or network partition

**Solution:**
```bash
# Run fork analysis
python3 analysis/targeted_attack_analyzer.py test_experiment_results/

# Look for "BLOCKCHAIN FORK DETECTED"

# If fork found, check logs for network issues
grep -i "connection refused\|timeout" experiment.log
```

### Problem: Experiment never completes

**Symptom:** Runs forever, never stops

**Cause:** Infinite loop or stuck waiting for something

**Solution:**
```bash
# Check what it's doing
tail -50 experiment.log

# If stuck on same message, kill and restart
kill $(cat experiment_pid.txt)

# Check max_duration setting
jq '.simulation_parameters.max_duration' simulation_helpers/shared_data/experiment_config.json

# Should be reasonable number (50-3600)
```

---

## Summary Checklist

### Before Running Experiment:
- [ ] BGP data exists in `bgp_feed/mininet_logs/`
- [ ] Cleaned previous blockchain data (optional)
- [ ] Set experiment duration in `experiment_config.json`
- [ ] No other experiments running (`ps aux | grep main_experiment`)

### During Experiment:
- [ ] Monitor logs (`tail -f experiment.log`)
- [ ] Check transaction commits (should see ⛓️ messages)
- [ ] Watch for errors (should be minimal)

### After Experiment:
- [ ] All 9 nodes have identical blockchain sizes
- [ ] Run post-hoc analysis
- [ ] Review consensus rate (should be >90%)
- [ ] Check for SINGLE_WITNESS or INSUFFICIENT_CONSENSUS

### Understanding Results:
- [ ] Know how many transactions processed
- [ ] Understand consensus statuses (CONFIRMED vs others)
- [ ] Check for misbehavior patterns (repeated attempts, bursts)
- [ ] Verify no blockchain forks

---

## Quick Reference Commands

```bash
# Clean and run experiment
./cleanup_experiment.sh && python3 main_experiment.py

# Check blockchain size
jq '.metadata' nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json

# Verify all nodes consistent
for n in as01 as03 as05 as07 as09 as11 as13 as15 as17; do
  jq '.metadata.total_transactions' nodes/rpki_nodes/$n/blockchain_node/blockchain_data/chain/blockchain.json
done

# Run post-hoc analysis
python3 analysis/targeted_attack_analyzer.py test_experiment_results/

# Show all IP prefixes recorded
jq -r '.blocks[].transactions[].ip_prefix' nodes/rpki_nodes/as01/blockchain_node/blockchain_data/chain/blockchain.json | sort -u | wc -l
```

---

**Questions?** See `COLLABORATOR_GUIDE.md` and `ARCHITECTURE_DETAILS.md` for more details.

**Ready to run?**
```bash
./cleanup_experiment.sh
python3 main_experiment.py
```

🚀 **Let's secure BGP routing!**
