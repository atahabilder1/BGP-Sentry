# 🚀 One-Command Attack Detection Test

## Super Simple - Just Run This:

```bash
python3 run_complete_test.py
```

**That's it!** This one command will:

1. ✅ Start all 9 blockchain nodes automatically
2. ✅ Start BGP simulation (if you have it)
3. ✅ Wait for blockchain to be ready
4. ✅ Inject 20 attacks + 1980 legitimate announcements
5. ✅ Monitor for 5 minutes
6. ✅ Generate visualizations
7. ✅ Analyze results
8. ✅ Clean up and stop everything

---

## 📊 What You'll Get

After running, you'll see:

- **Detection Rate**: % of attacks detected (target: 100%)
- **Blockchain Performance**: TPS and throughput
- **8-Plot Dashboard**: Rating evolution over time
- **Summary Table**: Statistics for each AS
- **Classification Chart**: RED/YELLOW/GREEN distribution
- **Complete Analysis**: Overall verdict

All results saved to:
```
experiment_results/attack_experiment_YYYYMMDD_HHMMSS/
```

---

## 🎯 Files You Can Run

| File | What It Does |
|------|--------------|
| **`run_complete_test.py`** | **ALL-IN-ONE**: Start nodes → Run test → Cleanup |
| `test_attack_detection.py` | Run test only (nodes must already be running) |

---

## 💡 Optional: Watch Live

While the test runs, open another terminal to watch live updates:

```bash
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 watch_ratings_live.py
```

---

## 🔧 What Happens Behind the Scenes

### Automatic Startup:
```
Starting as01... ✅ PID 12345
Starting as03... ✅ PID 12346
Starting as05... ✅ PID 12347
...
Started 9 blockchain nodes
```

### Blockchain Ready Check:
```
Waiting for blockchain activity...
✅ Blockchain is active! (45 blocks)
```

### Experiment Runs:
```
Injecting 20 attacks...
Monitoring for 5 minutes...
Generating visualizations...
Analyzing results...
```

### Automatic Cleanup:
```
Stopping as01... ✅
Stopping as03... ✅
...
Cleanup complete
```

---

## ❓ Troubleshooting

### "Failed to start blockchain nodes"

**Cause:** blockchain_node.py not found

**Check:**
```bash
ls nodes/rpki_nodes/as01/blockchain_node/blockchain_node.py
```

**Solution:** Make sure blockchain_node.py exists in each node directory

### "Blockchain may not be fully active yet"

**Not a problem!** The script continues anyway. The experiment will still work as nodes become active.

### "No BGP simulation script found"

**OK!** The script will skip BGP simulation. If you have attacks injected, that's enough for testing.

---

## 🎓 Comparison: Old vs New Way

### Old Way (What You Did):
```bash
# Start 9 nodes manually
python3 nodes/rpki_nodes/as01/blockchain_node/blockchain_node.py &
python3 nodes/rpki_nodes/as03/blockchain_node/blockchain_node.py &
# ... 7 more times

# Start BGP simulation
python3 bgp_simulation.py &

# Wait and check if ready
sleep 30

# Run test
python3 test_attack_detection.py

# Cleanup manually
kill <PID1> <PID2> ... <PID9>
```

### New Way (Now):
```bash
python3 run_complete_test.py
# Done! Everything automatic!
```

---

## ✅ Summary

**Super simple:**
```bash
python3 run_complete_test.py
```

**What you get:**
- Complete attack detection test
- All visualizations
- Complete analysis
- Automatic cleanup

**No manual steps needed!** 🎉

---

## 📚 Other Useful Commands

```bash
# Just analyze existing results
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 analyze_experiment.py

# View results interactively
python3 view_rating_results.py

# Open dashboard
eog experiment_results/attack_experiment_*/rating_dashboard.png
```

---

**Ready?** Just run:
```bash
python3 run_complete_test.py
```

And let it do everything! 🚀
