# 📊 Result Analysis - Quick Reference

## 🚀 Three Ways to Analyze Your Results

### Method 1: Automated Analysis (Recommended for Quick Insights)

**Run automated analyzer:**
```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 analyze_experiment.py
```

**What you get:**
- ✅ Detection rate analysis (% of attacks detected)
- ✅ Rating change analysis (which ASes went up/down)
- ✅ Classification accuracy (correctness of RED/YELLOW/GREEN)
- ✅ Blockchain performance summary (TPS, throughput)
- ✅ Overall verdict (successes and issues)
- ✅ Per-attacker breakdown

**Example output:**
```
=============================================================
📊 EXPERIMENT ANALYSIS REPORT
=============================================================

🎯 ATTACK DETECTION ANALYSIS
   Total Injected: 20 attacks
   Total Detected: 20 attacks
   Detection Rate: 100.00%
   Status: ✅ EXCELLENT (≥95%)

   Per-Attacker Breakdown:
      AS666: 12/12 detected (100.0%)
      AS31337: 8/8 detected (100.0%)

📈 RATING CHANGE ANALYSIS
AS       Initial    Final      Change     Class        Trend
--------------------------------------------------------------
AS666    50.0       32.0       -18.0      🔴 RED       decreasing   ATTACKER
AS31337  50.0       38.0       -12.0      🟡 YELLOW    decreasing   ATTACKER
AS100    50.0       50.0       0.0        🟡 YELLOW    stable       Legitimate

🎨 CLASSIFICATION ACCURACY
   Total ASes: 8
   Correctly Classified: 7
   Accuracy: 87.50%
   Status: ✅ GOOD (≥75%)

✅ OVERALL VERDICT
   ✅ Successes:
      • Excellent attack detection (≥95%)
      • Good classification accuracy (≥75%)
      • All attackers penalized (rating decreased)
      • Legitimate ASes correctly classified

   🏆 RECOMMENDATION: System is working excellently!
```

---

### Method 2: Interactive Viewer (Best for Exploring Data)

**Run interactive viewer:**
```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 view_rating_results.py
```

**Menu options:**
```
1. Show current non-RPKI ratings           - Real-time rating table
2. View latest experiment results          - File listing + locations
3. Regenerate visualizations               - Create fresh charts
4. Show blockchain performance             - TPS metrics
5. Run automated analysis                  - Full analysis report
6. Exit
```

**Use when:**
- You want to browse through different aspects of results
- Need to see current ratings (not just experiment results)
- Want to regenerate visualizations
- Prefer interactive exploration

---

### Method 3: Manual Analysis (Deep Dive)

**For detailed investigation, follow the comprehensive guide:**
```bash
cat /home/anik/code/BGP-Sentry/RESULT_ANALYSIS_GUIDE.md
```

**This guide includes:**
- 📂 Step 1: Locate your results
- 🔍 Step 2: Verify attack injection
- 📈 Step 3: Analyze rating evolution
- 📊 Step 4: Review summary statistics
- 🎯 Step 5: Calculate detection accuracy
- ⚡ Step 6: Assess blockchain performance
- 📉 Step 7: Analyze time-series data
- 🎨 Step 8: Interpret classification distribution
- 🧮 Step 9: Calculate custom metrics
- 🔬 Step 10: Deep dive analysis (advanced)

**Use when:**
- You need to understand every detail
- Writing a research paper or report
- Troubleshooting unexpected results
- Creating custom visualizations

---

## 📋 Quick Analysis Checklist

After running your experiment, verify these key points:

### ✅ Detection Performance
```bash
# Check detection rate
cat experiment_results/attack_experiment_*/detection_accuracy_report.json | jq '.detection_rate_percent'
# Target: >90% (ideally 100%)
```

### ✅ Rating Changes
```bash
# View rating dashboard
eog experiment_results/attack_experiment_*/rating_dashboard.png
```

**Look for:**
- Attackers (AS666, AS31337) show **downward trends** into RED zone
- Legitimate ASes stay in GREEN/YELLOW zones
- Red stars (★) appear at attack detection points

### ✅ Classification
```bash
# View pie chart
eog experiment_results/attack_experiment_*/classification_distribution.png
```

**Expected:**
- 🔴 RED: 2 ASes (attackers)
- 🟡 YELLOW: 3-4 ASes (neutral/uncertain)
- 🟢 GREEN: 2-3 ASes (legitimate, high trust)

### ✅ Performance
```bash
# Check TPS
cat experiment_results/attack_experiment_*/blockchain_performance_report.json | jq '.metrics.average_tps'
# Target: >1.0 for basic, >10 for good performance
```

---

## 🎯 What to Look For

### Good Results (System Working)
- ✅ Detection rate ≥ 95%
- ✅ AS666 final rating: 30-40 (RED)
- ✅ AS31337 final rating: 35-45 (RED/YELLOW)
- ✅ Legitimate ASes: 50-85 (YELLOW/GREEN)
- ✅ False positive rate < 5%
- ✅ Average TPS > 1.0
- ✅ All 20 attacks detected

### Issues to Investigate
- ❌ Detection rate < 80%
- ❌ Attackers still in GREEN zone
- ❌ Legitimate ASes in RED zone
- ❌ False positive rate > 10%
- ❌ Average TPS < 0.5
- ❌ Ratings not changing

---

## 🔬 Key Metrics Explained

### Detection Rate
```
Detection Rate = (Detected Attacks / Injected Attacks) × 100
```
**Target:** ≥ 95%

### False Positive Rate
```
False Positive Rate = (False Alarms / Legitimate Announcements) × 100
```
**Target:** < 5%

### Classification Accuracy
```
Classification Accuracy = (Correct Classifications / Total ASes) × 100
```
**Target:** ≥ 75%

### Transactions Per Second (TPS)
```
Average TPS = Total Transactions / Duration (seconds)
```
**Scale:**
- 🟢 EXCELLENT: >100 TPS
- 🟢 GOOD: 50-100 TPS
- 🟡 MODERATE: 10-50 TPS
- 🟡 LOW: 1-10 TPS
- 🔴 VERY LOW: <1 TPS

---

## 📂 Result Files Cheat Sheet

All files are in: `/home/anik/code/BGP-Sentry/experiment_results/attack_experiment_YYYYMMDD_HHMMSS/`

| File | What It Contains | How to View |
|------|------------------|-------------|
| `attack_scenarios.json` | Ground truth (20 attacks + 1980 legitimate) | `jq . attack_scenarios.json` |
| `rating_monitoring_data.json` | Time-series rating data | `jq '.time_series' rating_monitoring_data.json` |
| `blockchain_performance_report.json` | TPS and performance metrics | `jq '.metrics' blockchain_performance_report.json` |
| `rating_dashboard.png` | 8-plot visualization | `eog rating_dashboard.png` |
| `rating_summary_table.png` | Statistics table | `eog rating_summary_table.png` |
| `classification_distribution.png` | Pie chart | `eog classification_distribution.png` |
| `detection_accuracy_report.json` | Detection accuracy | `jq . detection_accuracy_report.json` |

---

## 💡 Common Analysis Tasks

### See which attacks were detected
```bash
cat rating_monitoring_data.json | jq '.time_series["666"].attacks_detected[-1]'
# Should show: 12 (for AS666)
```

### Check final rating for AS666
```bash
cat rating_monitoring_data.json | jq '.time_series["666"].ratings[-1]'
# Should show: ~30-40 (RED zone)
```

### Get performance summary
```bash
cat blockchain_performance_report.json | jq '{tps: .metrics.average_tps, total_tx: .metrics.total_transactions}'
```

### List all monitored ASes
```bash
cat rating_monitoring_data.json | jq '.monitored_ases'
```

### Compare initial vs final ratings
```bash
cat rating_monitoring_data.json | jq '.summary.as_summary | to_entries[] | {as: .key, initial: .value.initial_rating, final: .value.final_rating, change: .value.rating_change}'
```

---

## 🎓 Analysis Workflow

**Recommended workflow for analyzing results:**

1. **Run automated analysis** (2 minutes)
   ```bash
   python3 analyze_experiment.py
   ```

2. **View visualizations** (5 minutes)
   ```bash
   eog experiment_results/attack_experiment_*/rating_dashboard.png
   eog experiment_results/attack_experiment_*/rating_summary_table.png
   ```

3. **Review metrics** (3 minutes)
   - Detection rate: Should be ~100%
   - Classification accuracy: Should be ≥75%
   - Average TPS: Should be ≥1.0

4. **Investigate issues** (if any)
   - Use `RESULT_ANALYSIS_GUIDE.md` for deep dive
   - Check time-series data for patterns
   - Compare ground truth with detections

5. **Document findings**
   - Take screenshots of visualizations
   - Save key metrics from analysis report
   - Note any anomalies or unexpected behavior

---

## 🆘 Troubleshooting

### "No experiment results found"
**Solution:** Run an experiment first
```bash
python3 run_attack_experiment.py
```

### "Detection rate is 0%"
**Possible causes:**
- Blockchain consensus not working (need 3+ nodes)
- Attack detection disabled
- Monitoring duration too short

**Check:**
```bash
# Verify nodes are running
ps aux | grep blockchain_node.py

# Check consensus in logs
tail -f nodes/rpki_nodes/as01/blockchain_node/logs/blockchain.log
```

### "All ratings still at 50.0"
**Possible causes:**
- No attacks detected yet
- Rating system not updating
- Blockchain not processing transactions

**Check:**
```bash
# See if rating file exists
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json
```

### "TPS is 0 or very low"
**Possible causes:**
- Blockchain not processing transactions
- Nodes not communicating
- Performance monitoring started too early

**Check:**
```bash
# See if blocks are being created
ls -lt nodes/rpki_nodes/as01/blockchain_node/blockchain_data/blocks/
```

---

## 📚 Additional Resources

- **Complete Analysis Guide**: `RESULT_ANALYSIS_GUIDE.md`
- **Viewing Results**: `HOW_TO_VIEW_RESULTS.md`
- **Quick Start**: `ATTACK_EXPERIMENT_QUICKSTART.md`
- **System Overview**: `ATTACK_EXPERIMENT_SYSTEM.md`
- **Updates Summary**: `UPDATES_SUMMARY.md`

---

## 🎯 Bottom Line

**For most users:**
```bash
# Just run this!
python3 analyze_experiment.py
```

**Or use the interactive viewer:**
```bash
python3 view_rating_results.py
# Then select option 5: Run automated analysis
```

This gives you everything you need to know in 2 minutes! 🚀
