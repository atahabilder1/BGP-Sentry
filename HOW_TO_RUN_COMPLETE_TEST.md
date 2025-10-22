# 🚀 How to Run Complete Attack Detection Test

## ❌ What Went Wrong

Your test showed **0 TPS** and **no detections** because:

1. **Blockchain nodes are NOT running** - No transactions being processed
2. **BGP simulation is NOT running** - No announcements being sent
3. The experiment just monitored an idle system for 5 minutes

## ✅ Correct Workflow

You need to run things in this order:

### Step 1: Start Blockchain Nodes

**First, start all 9 RPKI blockchain nodes:**

```bash
# Start all nodes (you should have a script for this)
# Example:
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes

# Start each node (as01, as03, as05, as07, as09, as11, as13, as15, as17)
# Or use your startup script if you have one
```

**Verify blockchain is running:**
```bash
ps aux | grep blockchain | grep -v grep
# Should see 9 processes
```

### Step 2: Start BGP Simulation

**Start your BGP announcement simulation:**

```bash
# Start your BGP simulation (you should have a script for this)
# This feeds BGP announcements into the blockchain
```

### Step 3: Verify System is Running

**Check that transactions are being processed:**

```bash
# Check a blockchain directory for activity
ls -lt /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node/blockchain_data/blocks/

# Should see blocks being created with recent timestamps
```

### Step 4: NOW Run the Attack Experiment

**Once everything is running, then run the test:**

```bash
python3 test_attack_detection.py
```

**What happens:**
1. Injects 20 attacks + 1980 legitimate announcements
2. Your blockchain processes them
3. Attack detection system flags the malicious ones
4. Ratings go down for attackers (AS666, AS31337)
5. Blockchain TPS is measured
6. Results are analyzed

---

## 🎯 Alternative: Manual Step-by-Step

If you don't have automated scripts, do this manually:

### Terminal 1: Start First Blockchain Node
```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node
python3 blockchain_node.py
```

### Terminal 2-9: Start Remaining Nodes
```bash
# Repeat for as03, as05, as07, as09, as11, as13, as15, as17
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as03/blockchain_node
python3 blockchain_node.py
```

### Terminal 10: Start BGP Simulation
```bash
# Your BGP announcement sender
# This should continuously send announcements
```

### Terminal 11: Run Attack Test
```bash
cd /home/anik/code/BGP-Sentry
python3 test_attack_detection.py
```

### Terminal 12: Watch Live (Optional)
```bash
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 watch_ratings_live.py
```

---

## 🔍 Verify Before Running Test

**Run these checks BEFORE starting the experiment:**

### Check 1: Blockchain Nodes Running
```bash
ps aux | grep blockchain_node | grep -v grep | wc -l
# Should output: 9
```

### Check 2: Blocks Being Created
```bash
ls -lt /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node/blockchain_data/blocks/ | head -5
# Should see recent timestamps (within last few seconds)
```

### Check 3: Transactions Being Processed
```bash
# Check latest block has transactions
cat /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node/blockchain_data/blocks/block_*.json | tail -50 | grep -c '"transactions"'
# Should see transactions
```

### Check 4: TPS > 0
```bash
# Wait a minute, then check if new blocks appeared
sleep 60
ls -lt /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node/blockchain_data/blocks/ | head -5
# Should see NEW blocks created
```

**Only when ALL checks pass, run:**
```bash
python3 test_attack_detection.py
```

---

## 📊 Expected Results (When System is Running)

### During Experiment:
- **TPS**: 3-15 transactions/second (not 0!)
- **Blocks**: New blocks every few seconds
- **Ratings**: AS666 and AS31337 drop from 50 → 30-40
- **Detection Rate**: 95-100%

### After Experiment:
- **Dashboard**: Shows downward trends for attackers
- **Summary Table**: AS666/AS31337 in RED zone
- **Detection Report**: All 20 attacks detected
- **Performance**: TPS > 1.0

---

## 🛠️ Troubleshooting

### Issue: "No blockchain processes running"

**Solution:**
```bash
# Check if you have a startup script
ls -la nodes/rpki_nodes/*/start*.sh

# Or start nodes manually
cd nodes/rpki_nodes/as01/blockchain_node
python3 blockchain_node.py
```

### Issue: "TPS = 0.00"

**Cause:** No announcements being sent to blockchain

**Solution:**
1. Check BGP simulation is running
2. Check announcements are reaching blockchain
3. Verify blockchain is processing them

### Issue: "No attacks detected"

**Cause:** Attack detection system not running OR no consensus

**Solution:**
1. Need at least 3 blockchain nodes for consensus
2. Attack detection must be enabled in config
3. Check logs for detection messages

---

## 💡 Quick Test (No Full Simulation)

**Want to test the visualization without full simulation?**

You can inject attacks and manually create some rating data:

```bash
# 1. Inject attacks
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 -c "
from attack_injection_system import AttackInjectionSystem
injector = AttackInjectionSystem('.')
injector.inject_attack_scenarios([(666, 12), (31337, 8)])
"

# 2. Manually create rating file (for testing viz only)
cat > /home/anik/code/BGP-Sentry/nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json <<EOF
{
  "as_ratings": {
    "666": {"trust_score": 32.0, "rating_level": "bad", "attacks_detected": 12},
    "31337": {"trust_score": 38.0, "rating_level": "suspicious", "attacks_detected": 8}
  }
}
EOF

# 3. Test analyzer
python3 analyze_experiment.py
```

**This only tests the visualization, not the actual detection system!**

---

## 📚 Summary

**For a REAL test:**
1. ✅ Start all 9 blockchain nodes
2. ✅ Start BGP simulation
3. ✅ Verify TPS > 0
4. ✅ THEN run `python3 test_attack_detection.py`

**What you did (wrong):**
1. ❌ Started experiment with no blockchain running
2. ❌ No announcements being sent
3. ❌ System monitored an idle system for 5 minutes
4. ❌ Result: TPS = 0, no detections

---

**Next Steps:**
1. Start your blockchain nodes
2. Start your BGP simulation
3. Verify system is active (check TPS > 0)
4. Re-run: `python3 test_attack_detection.py`

Then you'll see real results! 🚀
