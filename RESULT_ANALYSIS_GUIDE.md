# 📊 Attack Experiment Results - Analysis Guide

## 🎯 Quick Analysis Checklist

Run through this checklist to validate your experiment:

- [ ] **Attack Detection**: Were all 20 attacks detected?
- [ ] **Rating Decay**: Did AS666 and AS31337 ratings go down?
- [ ] **Classification**: Are attackers in RED zone, legitimate ASes in GREEN?
- [ ] **Performance**: Is TPS > 1.0 for reasonable blockchain performance?
- [ ] **Attack Ratio**: Is attack ratio approximately 1.0%?

---

## 📂 Step 1: Locate Your Results

```bash
cd /home/anik/code/BGP-Sentry/experiment_results
ls -lt  # Find latest experiment directory
cd attack_experiment_20251021_*/  # Go to latest (use tab completion)
ls -lh  # See all result files
```

**You should see 7 files**:
```
attack_scenarios.json              - Ground truth (what you injected)
rating_monitoring_data.json        - Time-series rating data
blockchain_performance_report.json - TPS and performance metrics
rating_dashboard.png               - 8-plot visualization
rating_summary_table.png           - Statistics table
classification_distribution.png    - Pie chart
detection_accuracy_report.json     - Detection accuracy
```

---

## 🔍 Step 2: Verify Attack Injection

**Check ground truth file:**
```bash
cat attack_scenarios.json | jq '.summary'
```

**What to look for:**
```json
{
  "total_attacks": 20,
  "total_legitimate": 1980,
  "total_announcements": 2000,
  "attack_ratio_percent": 1.0,
  "attacker_ases": {
    "666": 12,
    "31337": 8
  }
}
```

**Validation:**
- ✅ Total attacks = 20
- ✅ Attack ratio ≈ 1.0%
- ✅ AS666 has 12 attacks, AS31337 has 8 attacks
- ✅ Legitimate announcements ≈ 1980 (99%)

---

## 📈 Step 3: Analyze Rating Evolution

**View the 8-plot dashboard:**
```bash
eog rating_dashboard.png
# OR
xdg-open rating_dashboard.png
```

**What to analyze in each plot:**

### For Attacker ASes (AS666, AS31337):

**Expected behavior:**
- ✅ **Downward trend**: Rating should decrease over time
- ✅ **Red stars (★)**: Should see multiple attack detection markers
- ✅ **Final classification**: Should be 🔴 RED (0-40) or 🟡 YELLOW (41-70)
- ✅ **Starting point**: Should start around 50 (neutral)
- ✅ **Ending point**: AS666 should be ~30-40, AS31337 should be ~38-45

**Red flags (issues to investigate):**
- ❌ Rating stays at 50 (no attacks detected)
- ❌ Rating increases (system malfunction)
- ❌ No red stars visible (detection not working)
- ❌ Final classification is GREEN (false negative)

### For Legitimate ASes (AS100, AS200, etc.):

**Expected behavior:**
- ✅ **Stable or upward trend**: Rating should stay steady or increase
- ✅ **Few/no red stars**: Should have 0-2 attack markers (false positives)
- ✅ **Final classification**: Should be 🟢 GREEN (71-100) or 🟡 YELLOW (41-70)
- ✅ **Starting point**: Around 50 (neutral)
- ✅ **Ending point**: Should be 50-85

**Red flags:**
- ❌ Rating drops significantly (false positive detections)
- ❌ Many red stars (too many false alarms)
- ❌ Final classification is RED (legitimate AS wrongly classified)

---

## 📊 Step 4: Review Summary Statistics

**View summary table:**
```bash
eog rating_summary_table.png
```

**Key columns to analyze:**

| Column | What to Check |
|--------|---------------|
| **Initial Rating** | Should all start around 50.0 |
| **Final Rating** | Attackers should be low (30-45), legitimate high (50-85) |
| **Rating Change** | Attackers should have **negative** change (-10 to -20) |
| **Min Rating** | Attackers should hit low values (25-40) |
| **Max Rating** | Legitimate ASes should reach high values (60-90) |
| **Attacks Detected** | Should match ground truth (AS666=12, AS31337=8, others=0) |
| **Classification** | Attackers=RED/YELLOW, Legitimate=GREEN/YELLOW |

**Example analysis:**
```
AS666:
  Initial: 50.0 → Final: 32.0 → Change: -18.0
  Attacks: 12 (matches ground truth!)
  Classification: 🔴 RED (Malicious)
  ✅ CORRECT DETECTION

AS31337:
  Initial: 50.0 → Final: 38.0 → Change: -12.0
  Attacks: 8 (matches ground truth!)
  Classification: 🟡 YELLOW (Suspicious)
  ✅ CORRECT DETECTION

AS100 (legitimate):
  Initial: 50.0 → Final: 50.0 → Change: 0.0
  Attacks: 0
  Classification: 🟡 YELLOW (Neutral/Suspicious)
  ✅ CORRECT (no false positives)
```

---

## 🎯 Step 5: Calculate Detection Accuracy

**Check detection report:**
```bash
cat detection_accuracy_report.json | jq
```

**Key metrics:**

### Detection Rate (Recall)
```
Detection Rate = (Detected Attacks / Total Injected Attacks) × 100
```

**Target**: > 90% (ideally 100%)

**Example:**
```json
{
  "total_injected_attacks": 20,
  "total_detected_attacks": 20,
  "detection_rate_percent": 100.0
}
```
✅ **Perfect detection!**

### False Positive Rate
```
False Positive Rate = (False Alarms / Total Legitimate) × 100
```

**Target**: < 5%

**Example:**
```json
{
  "total_legitimate_announcements": 1980,
  "false_positives": 15,
  "false_positive_rate_percent": 0.76
}
```
✅ **Excellent! Only 0.76% false positives**

### Classification Accuracy
```
Accuracy = (Correctly Classified / Total ASes) × 100
```

**Example:**
```json
{
  "correctly_classified_ases": 7,
  "total_ases": 8,
  "classification_accuracy_percent": 87.5
}
```
✅ **Good classification accuracy**

---

## ⚡ Step 6: Assess Blockchain Performance

**View performance report:**
```bash
cat blockchain_performance_report.json | jq '.metrics'
```

**Key metrics to analyze:**

### 1. Transactions Per Second (TPS)
```json
{
  "average_tps": 6.47,
  "peak_tps": 12.50
}
```

**Performance scale:**
- 🟢 **EXCELLENT** (>100 TPS): Production-ready
- 🟢 **GOOD** (50-100 TPS): High performance
- 🟡 **MODERATE** (10-50 TPS): Acceptable for research
- 🟡 **LOW** (1-10 TPS): Basic functionality
- 🔴 **VERY LOW** (<1 TPS): Performance issues

**Your result (6.47 TPS):** 🟡 LOW - Basic but functional for research

### 2. Transaction Throughput
```json
{
  "throughput_kb_per_second": 3.24,
  "throughput_mb_per_second": 0.0032
}
```

**What this means:**
- Your blockchain processes ~3.24 KB/s of transaction data
- For 2000 transactions over 5 minutes, this is reasonable

### 3. Block Production Rate
```json
{
  "average_blocks_per_minute": 27.88,
  "average_tx_per_block": 13.93
}
```

**Analysis:**
- ✅ Blocks created regularly (27.88/minute ≈ 1 block every 2 seconds)
- ✅ Each block contains ~14 transactions on average
- ✅ Good block packing efficiency

### 4. Overall Performance
```json
{
  "total_transactions": 2020,
  "total_blocks": 145,
  "duration_minutes": 5.20
}
```

**Validation:**
- ✅ Processed all 2000 injected announcements + 20 rating updates
- ✅ Created 145 blocks in 5 minutes
- ✅ No transaction loss

---

## 📉 Step 7: Analyze Time-Series Data

**Load monitoring data for detailed analysis:**

```bash
cat rating_monitoring_data.json | jq '.time_series["666"]'
```

**What you'll see:**
```json
{
  "as_number": 666,
  "timestamps": ["2025-10-21T20:15:00", "2025-10-21T20:15:10", ...],
  "ratings": [50.0, 50.0, 48.0, 46.0, 44.0, ..., 32.0],
  "attacks_detected": [0, 0, 2, 4, 6, ..., 12],
  "rating_levels": ["neutral", "neutral", "suspicious", ..., "bad"]
}
```

**Key patterns to look for:**

### 1. Rating Decay Pattern
- **Immediate drop**: Rating drops right after first attack detected
- **Gradual decline**: Rating decreases with each new attack
- **Stabilization**: Rating stabilizes after all attacks detected

### 2. Attack Detection Timeline
```json
"attacks_detected": [0, 0, 2, 4, 6, 8, 10, 12, 12, 12]
```

**Analysis:**
- Attacks detected incrementally over time
- All 12 attacks for AS666 detected by end of monitoring
- Detection happens within monitoring period (good responsiveness)

### 3. Rating Recovery (or lack thereof)
- Attackers should **NOT** recover (rating stays low)
- Legitimate ASes may recover if falsely flagged

---

## 🎨 Step 8: Interpret Classification Distribution

**View pie chart:**
```bash
eog classification_distribution.png
```

**Expected distribution** (for 8 monitored ASes):

```
🔴 RED (0-40):       2 ASes (25%)  ← AS666, AS31337
🟡 YELLOW (41-70):   3 ASes (37.5%)  ← Neutral/uncertain
🟢 GREEN (71-100):   3 ASes (37.5%)  ← Legitimate, high trust
```

**Analysis questions:**

1. **Are attackers in RED?**
   - ✅ Both AS666 and AS31337 should be in RED zone
   - If not, detection sensitivity may be too low

2. **Are legitimate ASes in GREEN?**
   - ✅ Most legitimate ASes should be GREEN or YELLOW
   - If many are RED, too many false positives

3. **Distribution balance?**
   - ✅ Expect more GREEN/YELLOW than RED (only 2 attackers out of 8)
   - ⚠️ If >50% are RED, system may be too aggressive

---

## 🧮 Step 9: Calculate Custom Metrics

**You can extract and calculate additional metrics:**

### Attack Impact Score
```
Impact = (Initial Rating - Final Rating) / Attacks Detected
```

**Example for AS666:**
```
Impact = (50.0 - 32.0) / 12 = 1.5 points per attack
```

**What this tells you:**
- Each detected attack reduces rating by ~1.5 points
- Consistent penalty system

### Detection Latency
```bash
# Find time between attack injection and first detection
cat rating_monitoring_data.json | jq '.time_series["666"].timestamps[2]'
```

**Analysis:**
- How quickly did the system detect the first attack?
- Shorter latency = better real-time protection

### Rating Volatility
```
Volatility = Standard Deviation of ratings over time
```

**Interpretation:**
- High volatility for attackers = rating fluctuates (uncertain)
- Low volatility for legitimate = stable trust

---

## 🔬 Step 10: Deep Dive Analysis (Advanced)

### Compare with Ground Truth

**Extract ground truth:**
```bash
cat attack_scenarios.json | jq '.attacks[] | select(.attacker_asn == 666)'
```

**Compare with detections:**
```bash
cat rating_monitoring_data.json | jq '.time_series["666"].attacks_detected[-1]'
```

**Calculate:**
- True Positives: Correctly detected attacks
- False Negatives: Missed attacks
- False Positives: Incorrectly flagged legitimate traffic

### Analyze Attack Types

**Check what types of attacks were injected:**
```bash
cat attack_scenarios.json | jq '[.attacks[].attack_type] | group_by(.) | map({type: .[0], count: length})'
```

**Example output:**
```json
[
  {"type": "prefix_hijacking", "count": 12},
  {"type": "sub_prefix_hijacking", "count": 6},
  {"type": "route_leak", "count": 2}
]
```

**Analysis:**
- Does detection rate vary by attack type?
- Are certain attacks harder to detect?

### Time-to-Detection Analysis

**For each attack, calculate how long it took to detect:**

```python
import json
from datetime import datetime

with open('attack_scenarios.json') as f:
    scenarios = json.load(f)

with open('rating_monitoring_data.json') as f:
    monitoring = json.load(f)

# Compare injection timestamps with detection timestamps
for attack in scenarios['attacks']:
    injection_time = datetime.fromisoformat(attack['timestamp'])
    # Find when attack count increased in monitoring data
    # Calculate delta...
```

---

## ✅ Final Analysis Report Template

**Create your own summary:**

```markdown
# Experiment Results Summary

**Date:** 2025-10-21
**Duration:** 5.2 minutes
**Total Announcements:** 2000 (20 attacks + 1980 legitimate)

## Detection Performance
- Detection Rate: 100% (20/20 attacks detected)
- False Positive Rate: 0.76% (15/1980)
- Classification Accuracy: 87.5% (7/8 ASes correctly classified)

## Rating Analysis
### Attackers
- AS666: 50.0 → 32.0 (-18.0) 🔴 RED [12 attacks detected]
- AS31337: 50.0 → 38.0 (-12.0) 🟡 YELLOW [8 attacks detected]

### Legitimate ASes
- AS100: 50.0 → 50.0 (0.0) 🟡 YELLOW [0 attacks]
- AS200: 50.0 → 65.0 (+15.0) 🟢 GREEN [0 attacks]
- ...

## Blockchain Performance
- Average TPS: 6.47 tx/s (🟡 LOW but functional)
- Peak TPS: 12.50 tx/s
- Total Transactions: 2020
- Block Rate: 27.88 blocks/minute

## Conclusions
✅ System correctly detected all injected attacks
✅ Attackers classified as malicious (RED/YELLOW)
✅ Low false positive rate (<1%)
✅ Blockchain processed all transactions successfully
⚠️ TPS is low (6.47) - consider optimization for production use

## Recommendations
1. Investigate why AS31337 is YELLOW instead of RED (may need lower threshold)
2. Optimize blockchain for higher TPS (target >10 TPS)
3. Run longer experiments (10-15 minutes) to observe rating stabilization
```

---

## 🎓 Key Takeaways

**Your analysis should answer these questions:**

1. **Did the system detect the attacks?**
   - Check detection_accuracy_report.json for detection rate

2. **Did ratings go down for attackers?**
   - Check rating_dashboard.png for downward trends
   - Verify final ratings are in RED/YELLOW zones

3. **Are legitimate ASes protected?**
   - Verify low false positive rate (<5%)
   - Check legitimate ASes stay in GREEN/YELLOW

4. **Is blockchain performing well?**
   - TPS > 1.0 = functional
   - TPS > 10 = good for research
   - TPS > 50 = production-ready

5. **Is the experiment valid?**
   - Attack ratio ≈ 1.0%
   - All 20 attacks injected
   - Monitoring duration sufficient (5+ minutes)

---

## 🛠️ Interactive Analysis Commands

**Quick analysis script:**

```bash
#!/bin/bash
# Save as analyze_latest.sh

LATEST=$(ls -dt experiment_results/attack_experiment_* | head -1)

echo "=== EXPERIMENT ANALYSIS ==="
echo "Directory: $LATEST"
echo ""

echo "=== ATTACK SUMMARY ==="
cat "$LATEST/attack_scenarios.json" | jq '.summary'
echo ""

echo "=== DETECTION ACCURACY ==="
cat "$LATEST/detection_accuracy_report.json" | jq '{detection_rate, false_positive_rate, classification_accuracy}'
echo ""

echo "=== BLOCKCHAIN PERFORMANCE ==="
cat "$LATEST/blockchain_performance_report.json" | jq '.metrics | {average_tps, peak_tps, total_transactions}'
echo ""

echo "=== RATING CHANGES (Top 5 ASes by rating change) ==="
cat "$LATEST/rating_monitoring_data.json" | jq -r '.summary.as_summary | to_entries | sort_by(.value.rating_change) | .[:5] | .[] | "AS\(.key): \(.value.rating_change) (\(.value.final_classification))"'
```

**Run it:**
```bash
chmod +x analyze_latest.sh
./analyze_latest.sh
```

---

## 📞 Need Help?

**Common analysis issues:**

- **No data in monitoring file**: Experiment may not have run long enough
- **All ratings at 50.0**: Blockchain consensus may not be working (need 3+ nodes)
- **TPS = 0**: Blockchain not processing transactions
- **Detection rate = 0%**: Attack detection system may be disabled

**Check:**
1. Are all 9 RPKI nodes running? (`ps aux | grep blockchain`)
2. Is consensus enabled? (need 3+ nodes voting)
3. Did monitoring run for full duration? (check timestamps)

---

**Next Step:** Run the analysis using the methods above and share your findings! 🚀
