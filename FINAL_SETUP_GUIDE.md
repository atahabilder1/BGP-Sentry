# 🎯 Final Setup - Complete Attack Detection Test

## ✅ All Done! Ready to Use

Everything is set up and ready. You have **TWO options**:

---

## 🚀 Option 1: ONE COMMAND - Does Everything (Recommended)

```bash
python3 run_complete_test.py
```

**This automatically:**
1. ✅ Initializes all non-RPKI ASes with random ratings (80-85)
2. ✅ Starts all 9 blockchain nodes
3. ✅ Starts BGP simulation (if you have it)
4. ✅ Waits for blockchain to be ready
5. ✅ Injects 20 attacks + 1980 legitimate announcements
6. ✅ Monitors for 5 minutes
7. ✅ Generates visualizations
8. ✅ Analyzes results
9. ✅ Cleans up and stops everything

**Just run it and let it do everything!**

---

## 🎲 Option 2: Manual Step-by-Step

If you want more control:

### Step 1: Initialize Ratings
```bash
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 initialize_ratings.py
```

**What it does:**
- Sets all non-RPKI ASes to random ratings between 80-85
- Gives them "good" initial reputation
- Ratings will adjust based on behavior during experiment

**Example output:**
```
AS Number    Initial Rating  Level
------------------------------------------
AS666        82.34          🟢 good
AS31337      84.12          🟢 excellent
AS100        81.56          🟢 good
AS200        83.45          🟢 good
```

### Step 2: Run Test
```bash
cd /home/anik/code/BGP-Sentry
python3 test_attack_detection.py
```

---

## 📊 What Happens During Test

### Initialization Phase
```
🎲 INITIALIZING NON-RPKI RATINGS
Setting all non-RPKI ASes to random ratings (80-85)...
✅ Ratings initialized successfully
```

### Attack Injection
```
Injecting 20 attacks...
  AS666: 12 attacks
  AS31337: 8 attacks

Generating 1980 legitimate announcements...
Total: 2000 announcements (1.0% attack ratio)
```

### Monitoring Phase (5 minutes)
```
Sample #1  | Elapsed: 0s   | Remaining: 300s
Sample #2  | Elapsed: 10s  | Remaining: 290s
...

Ratings adjusting based on behavior:
  AS666:   82.34 → 78.20 → 72.15 → ... → 32.50  (detected attacks!)
  AS31337: 84.12 → 80.45 → 75.30 → ... → 38.20  (detected attacks!)
  AS100:   81.56 → 82.10 → 83.00 → ... → 84.50  (legitimate, rating up!)
```

### Results
```
Detection Rate: 100.00% (20/20 attacks detected)
Classification Accuracy: 87.5% (7/8 ASes correct)

AS666:   Initial: 82.34 → Final: 32.50  (-49.84) 🔴 RED
AS31337: Initial: 84.12 → Final: 38.20  (-45.92) 🟡 YELLOW
AS100:   Initial: 81.56 → Final: 84.50  (+2.94)  🟢 GREEN
```

---

## 🎨 Live Visualization (Optional)

While test runs, open another terminal:

```bash
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 watch_ratings_live.py
```

**You'll see:**
- Real-time rating changes every 10 seconds
- Attackers' ratings dropping from 80-85 → RED zone
- Legitimate ASes staying in GREEN zone
- TPS and detection metrics updating live

---

## 📁 Results Location

All results saved to:
```
experiment_results/attack_experiment_YYYYMMDD_HHMMSS/
```

**Files generated:**
- `rating_dashboard.png` - 8-plot visualization
- `rating_summary_table.png` - Statistics table
- `classification_distribution.png` - Pie chart
- `attack_scenarios.json` - Ground truth
- `rating_monitoring_data.json` - Time-series data
- `blockchain_performance_report.json` - TPS metrics
- `detection_accuracy_report.json` - Analysis

---

## 🔍 Analyze Results

```bash
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 analyze_experiment.py
```

**Shows:**
- Detection rate (target: 100%)
- Rating changes for each AS
- Classification accuracy
- Blockchain performance (TPS)
- Overall verdict

---

## 📊 View Results Interactively

```bash
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 view_rating_results.py
```

**Menu options:**
1. Show current non-RPKI ratings
2. View latest experiment results
3. Regenerate visualizations
4. Show blockchain performance
5. Run automated analysis
6. Exit

---

## 🎯 Expected Results

### Initial State (Before Attacks)
```
AS666:   Rating: 82.34  Level: 🟢 good
AS31337: Rating: 84.12  Level: 🟢 excellent
AS100:   Rating: 81.56  Level: 🟢 good
AS200:   Rating: 83.45  Level: 🟢 good
```

### After Attacks Detected
```
AS666:   Rating: 32.50  Level: 🔴 bad         (12 attacks detected)
AS31337: Rating: 38.20  Level: 🟡 suspicious  (8 attacks detected)
AS100:   Rating: 84.50  Level: 🟢 excellent   (0 attacks, good behavior)
AS200:   Rating: 85.20  Level: 🟢 excellent   (0 attacks, good behavior)
```

### Metrics
- Detection Rate: 95-100%
- False Positive Rate: <5%
- Classification Accuracy: >75%
- Average TPS: 3-15 (depends on your system)

---

## 💡 Key Points

### Rating Behavior

**Attackers:**
- Start: 80-85 (good reputation)
- During: Drop gradually as attacks detected
- End: 30-45 (RED/YELLOW zone)

**Legitimate:**
- Start: 80-85 (good reputation)
- During: Stay stable or increase slightly
- End: 80-90 (GREEN zone)

### Why Start at 80-85?

- Gives all ASes "benefit of the doubt"
- Represents "unknown but probably good" reputation
- Allows system to distinguish good from bad behavior
- Attackers drop from 80+ → 30-40 (clear distinction!)
- Legitimate ASes stay high or improve

---

## 🛠️ Troubleshooting

### Issue: "Blockchain nodes not starting"

**Check:**
```bash
ls nodes/rpki_nodes/as01/blockchain_node/blockchain_node.py
```

**Should exist!** If not, check your project structure.

### Issue: "TPS = 0.00"

**Cause:** Blockchain not processing

**Solution:** Make sure blockchain nodes are running:
```bash
ps aux | grep blockchain | grep -v grep
```

### Issue: "No ratings changing"

**Cause:** Attacks not being detected

**Solution:**
- Check blockchain consensus (need 3+ nodes)
- Check attack detection is enabled
- Review logs for detection messages

---

## 📚 All Available Commands

```bash
# MAIN COMMAND - Does everything
python3 run_complete_test.py

# Initialize ratings only
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 initialize_ratings.py

# Run test only (manual)
python3 test_attack_detection.py

# Watch live
cd nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 watch_ratings_live.py

# Analyze results
python3 analyze_experiment.py

# View results interactively
python3 view_rating_results.py

# Open dashboard
eog experiment_results/attack_experiment_*/rating_dashboard.png
```

---

## ✅ Summary

**Super simple workflow:**

1. Run: `python3 run_complete_test.py`
2. Wait 10 minutes
3. Check results!

**Features:**
- ✅ Automatic rating initialization (80-85)
- ✅ Automatic blockchain startup
- ✅ Attack injection (1% ratio)
- ✅ Real-time monitoring
- ✅ Live visualization (optional)
- ✅ Complete analysis
- ✅ Automatic cleanup

**You're all set!** 🎉

Just run:
```bash
python3 run_complete_test.py
```

And enjoy watching your attack detection system in action! 🚀
