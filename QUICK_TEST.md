# 🚀 Quick Attack Detection Test

## One Command - Does Everything

```bash
python3 test_attack_detection.py
```

That's it! This single command will:

1. ✅ Inject 20 attack scenarios (12 to AS666, 8 to AS31337)
2. ✅ Monitor ratings for 5 minutes
3. ✅ Measure blockchain performance (TPS)
4. ✅ Generate visualizations
5. ✅ Analyze detection accuracy
6. ✅ Show complete results

---

## 📊 Optional: Watch Live

Want to see ratings change in real-time? Open a second terminal:

**Terminal 1:**
```bash
python3 test_attack_detection.py
```

**Terminal 2:**
```bash
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 watch_ratings_live.py
```

---

## 📈 What You Get

After running the test, you'll have:

- **Detection Rate**: % of attacks detected
- **Blockchain Performance**: TPS and throughput
- **8-Plot Dashboard**: Rating evolution over time
- **Summary Table**: Statistics for each AS
- **Classification Chart**: RED/YELLOW/GREEN distribution
- **Complete Analysis**: Detection accuracy report

---

## 📁 Results Location

All results saved to:
```
experiment_results/attack_experiment_YYYYMMDD_HHMMSS/
```

---

## 🎯 Quick Commands

```bash
# Run the test
python3 test_attack_detection.py

# Analyze results again
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 analyze_experiment.py

# View results interactively
python3 view_rating_results.py

# Open dashboard
eog experiment_results/attack_experiment_*/rating_dashboard.png
```

---

**Just run `python3 test_attack_detection.py` and let it do everything!** 🎉
