# 🎯 BGP-Sentry Attack Experiment - Complete Features Summary

## 🚀 Quick Start

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

That's it! The system handles everything else automatically.

---

## ✨ Key Features

### 1. 🎨 **Live Real-Time Visualization** (NEW!)

**A matplotlib window shows real-time updates during the experiment:**

- **8 rating plots**: One per non-RPKI AS, updating every 10 seconds
- **Color-coded zones**: RED (bad), YELLOW (suspicious), GREEN (good)
- **Attack markers**: Red stars (★) when attacks detected
- **Blockchain performance**: Live TPS graph
- **Detection metrics**: Real-time detection rate display

**Benefits:**
- ✅ Watch ratings change as they happen
- ✅ See if experiment is working correctly
- ✅ Spot issues immediately (e.g., TPS=0, no detections)
- ✅ Take screenshots during experiment
- ✅ More engaging than console output

**See:** `LIVE_VISUALIZATION_GUIDE.md`

---

### 2. 🎯 **Attack Injection with <1% Attack Ratio**

**Automatically generates:**
- 20 attacks (12 to AS666, 8 to AS31337)
- ~1980 legitimate announcements
- Total: 2000 announcements = 1.0% attack ratio

**Attack types:**
- IP prefix hijacking
- Sub-prefix hijacking
- Route leaks

**Customizable:**
```python
runner.run_complete_experiment(
    attacker_ases=[(666, 30), (31337, 20)],  # 50 total attacks
    attack_ratio=0.005  # 0.5% instead of 1%
)
```

---

### 3. ⚡ **Blockchain Performance Monitoring**

**Tracks in real-time:**
- **Average TPS**: Transactions per second
- **Peak TPS**: Maximum TPS observed
- **Total Transactions**: Count of all processed transactions
- **Total Blocks**: Count of blocks created
- **Throughput**: KB/s and MB/s
- **Block Rate**: Blocks per minute

**Performance Classification:**
- 🟢 EXCELLENT: >100 TPS
- 🟢 GOOD: 50-100 TPS
- 🟡 MODERATE: 10-50 TPS
- 🟡 LOW: 1-10 TPS (typical for research setup)
- 🔴 VERY LOW: <1 TPS

---

### 4. 📊 **Post-Hoc Visualizations**

**Automatically generates 3 visualizations:**

**a) Rating Dashboard** (`rating_dashboard.png`)
- 8-plot grid showing rating evolution
- Color-coded background zones
- Attack detection markers
- Final classification badges

**b) Summary Table** (`rating_summary_table.png`)
- Initial vs final ratings
- Rating change (Δ)
- Min/max ratings
- Attacks detected
- Final classification

**c) Classification Pie Chart** (`classification_distribution.png`)
- Distribution of RED/YELLOW/GREEN classifications
- Percentages and counts

---

### 5. 🔬 **Automated Analysis**

**Run automated analyzer:**
```bash
python3 analyze_experiment.py
```

**Provides:**
- ✅ Detection rate (% of attacks detected)
- ✅ False positive rate
- ✅ Classification accuracy
- ✅ Rating change analysis
- ✅ Per-attacker breakdown
- ✅ Overall verdict and recommendations

**Example output:**
```
🎯 ATTACK DETECTION ANALYSIS
   Detection Rate: 100.00%
   Status: ✅ EXCELLENT

📈 RATING CHANGE ANALYSIS
AS666    50.0 → 32.0  (-18.0)  🔴 RED       ATTACKER
AS31337  50.0 → 38.0  (-12.0)  🟡 YELLOW    ATTACKER

✅ OVERALL VERDICT
   🏆 RECOMMENDATION: System is working excellently!
```

---

### 6. 📺 **Interactive Results Viewer**

**View results anytime:**
```bash
python3 view_rating_results.py
```

**Menu options:**
1. Show current non-RPKI ratings (real-time)
2. View latest experiment results (files listing)
3. Regenerate visualizations (if missing)
4. Show blockchain performance (TPS report)
5. Run automated analysis (full report)
6. Exit

---

### 7. 📁 **Complete Result Files**

**Every experiment generates 7 files:**

| File | Purpose |
|------|---------|
| `attack_scenarios.json` | Ground truth (what attacks were injected) |
| `rating_monitoring_data.json` | Time-series rating data |
| `blockchain_performance_report.json` | TPS and performance metrics |
| `rating_dashboard.png` | 8-plot visualization |
| `rating_summary_table.png` | Statistics table |
| `classification_distribution.png` | Pie chart |
| `detection_accuracy_report.json` | Detection accuracy metrics |

**All saved to:** `/home/anik/code/BGP-Sentry/experiment_results/attack_experiment_YYYYMMDD_HHMMSS/`

---

## 🎓 Complete Workflow

### Step 1: Run Experiment (10 minutes)

```bash
python3 run_attack_experiment.py
```

**What happens:**
1. Injects 20 attacks + 1980 legitimate announcements
2. Opens live visualization window
3. Monitors for 5 minutes
4. Shows real-time rating changes
5. Generates all visualizations
6. Calculates detection accuracy

### Step 2: Analyze Results (2 minutes)

```bash
python3 analyze_experiment.py
```

**What you get:**
- Detection rate analysis
- Rating change summary
- Classification accuracy
- Performance metrics
- Overall verdict

### Step 3: View Visualizations (5 minutes)

```bash
eog experiment_results/attack_experiment_*/rating_dashboard.png
```

**Review:**
- 8-plot dashboard
- Summary table
- Pie chart

### Step 4: Write Report

**Use the data from:**
- Automated analysis output
- Visualization screenshots
- JSON files for detailed metrics

---

## 📊 What to Expect

### Expected Results (System Working Correctly)

**Attackers:**
- AS666: 50.0 → ~30-35 (🔴 RED)
- AS31337: 50.0 → ~35-40 (🔴 RED or 🟡 YELLOW)

**Legitimate ASes:**
- Stay around 50-70 (🟡 YELLOW or 🟢 GREEN)
- Minimal rating drops

**Detection:**
- Detection rate: 95-100%
- False positive rate: <5%

**Performance:**
- Average TPS: 3-12 (🟡 LOW but functional for research)
- Peak TPS: 10-20
- No transaction loss

---

## 🎯 Key Metrics Explained

### Detection Rate
```
Detection Rate = (Detected Attacks / Injected Attacks) × 100
```
**Target:** ≥95% (ideally 100%)

### False Positive Rate
```
False Positive Rate = (False Alarms / Legitimate Announcements) × 100
```
**Target:** <5%

### Classification Accuracy
```
Classification Accuracy = (Correct Classifications / Total ASes) × 100
```
**Target:** ≥75%

### Transactions Per Second (TPS)
```
Average TPS = Total Transactions / Duration (seconds)
```
**For research:** >1.0 is acceptable, >10 is good

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `ATTACK_EXPERIMENT_QUICKSTART.md` | Quick start guide |
| `ATTACK_EXPERIMENT_SYSTEM.md` | Complete technical documentation |
| `LIVE_VISUALIZATION_GUIDE.md` | Live visualization details |
| `RESULT_ANALYSIS_GUIDE.md` | Step-by-step analysis guide |
| `ANALYSIS_QUICK_REFERENCE.md` | Quick reference cheat sheet |
| `HOW_TO_VIEW_RESULTS.md` | Viewing results guide |
| `UPDATES_SUMMARY.md` | What's new summary |
| `EXPERIMENT_FEATURES_SUMMARY.md` | This file |

---

## 🛠️ Tools Available

### Experiment Tools

| Tool | Command | Purpose |
|------|---------|---------|
| **Experiment Runner** | `python3 run_attack_experiment.py` | Run complete experiment |
| **Live Monitor Test** | `python3 live_rating_monitor.py` | Test live visualization |
| **Results Viewer** | `python3 view_rating_results.py` | Interactive results browser |
| **Automated Analyzer** | `python3 analyze_experiment.py` | Automated analysis |
| **Dashboard Opener** | `./open_dashboard.sh` | Quick visualization opener |

### Analysis Commands

```bash
# View latest dashboard
eog experiment_results/attack_experiment_*/rating_dashboard.png

# Check detection rate
cat experiment_results/attack_experiment_*/detection_accuracy_report.json | jq '.detection_rate_percent'

# View TPS
cat experiment_results/attack_experiment_*/blockchain_performance_report.json | jq '.metrics.average_tps'

# List all experiments
ls -lt experiment_results/
```

---

## 🎨 Customization Options

### Attack Configuration

```python
# Different attackers
runner.run_complete_experiment(
    attacker_ases=[(666, 20), (31337, 15), (8888, 10)]
)

# Different attack ratio
runner.run_complete_experiment(
    attack_ratio=0.005  # 0.5% instead of 1%
)
```

### Monitoring Configuration

```python
# Longer monitoring duration
runner.run_complete_experiment(
    monitor_duration=600,    # 10 minutes
    monitor_interval=5       # 5 second snapshots
)

# Disable live visualization
runner.run_complete_experiment(
    enable_live_visualization=False
)
```

### Classification Thresholds

Edit `rating_visualization.py`:
```python
THRESHOLDS = {
    "red_max": 30,      # RED zone: 0-30
    "yellow_max": 60,   # YELLOW zone: 31-60
    "green_min": 61     # GREEN zone: 61-100
}
```

---

## ✅ Feature Comparison Matrix

| Feature | Real-Time | Post-Hoc | Best For |
|---------|-----------|----------|----------|
| **Live Visualization** | ✅ Updates every 10s | ❌ N/A | Monitoring experiment |
| **Rating Dashboard** | ❌ N/A | ✅ Static PNG | Final analysis, reports |
| **TPS Monitoring** | ✅ Live graph | ✅ JSON report | Both |
| **Detection Rate** | ✅ Live display | ✅ JSON report | Both |
| **Automated Analysis** | ❌ N/A | ✅ Complete report | Post-experiment analysis |
| **Interactive Viewer** | ❌ N/A | ✅ Menu-driven | Browsing results |

---

## 🎓 Learning Path

**New to the system? Follow this order:**

1. **Read:** `ATTACK_EXPERIMENT_QUICKSTART.md` (5 min)
2. **Run:** `python3 run_attack_experiment.py` (10 min)
3. **Watch:** Live visualization as experiment runs
4. **Analyze:** `python3 analyze_experiment.py` (2 min)
5. **View:** Dashboard and visualizations (5 min)
6. **Learn:** `RESULT_ANALYSIS_GUIDE.md` for deep understanding
7. **Reference:** Use `ANALYSIS_QUICK_REFERENCE.md` as cheat sheet

---

## 🎉 Summary

**You now have a complete attack experiment system with:**

✅ Automated attack injection (<1% ratio)
✅ **Real-time live visualization** (NEW!)
✅ Blockchain performance monitoring (TPS, throughput)
✅ Post-hoc visualizations (8-plot dashboard, tables, charts)
✅ Automated analysis (detection rate, accuracy)
✅ Interactive results viewer
✅ Complete documentation

**Everything you need for:**
- Research papers
- System validation
- Performance benchmarking
- Detection accuracy testing
- Real-time monitoring
- Post-hoc analysis

---

## 🚀 Get Started Now!

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

**Within 10 minutes you'll have:**
- Live visualization of rating changes
- Complete analysis of detection performance
- Beautiful visualizations for your papers
- TPS and performance metrics
- Detection accuracy reports

**Enjoy your enhanced experiment system!** 🎊
