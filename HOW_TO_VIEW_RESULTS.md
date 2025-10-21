# 📊 How to View Rating Results

## 🚀 Quick View (3 Methods)

### Method 1: Interactive Viewer (Recommended)

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 view_rating_results.py
```

**Features**:
- ✅ Show current ratings for all non-RPKI ASes
- ✅ View latest experiment results
- ✅ Regenerate visualizations
- ✅ Show blockchain performance metrics
- ✅ Interactive menu

**Menu Options**:
```
1. Show current non-RPKI ratings - Real-time rating table
2. View latest experiment results - List all files
3. Regenerate visualizations - Create new dashboard/charts
4. Show blockchain performance - TPS and throughput
5. Exit
```

### Method 2: Quick Dashboard Opener

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
./open_dashboard.sh
```

**This will**:
- Find latest experiment results
- Open rating dashboard (8-plot visualization)
- Open summary table
- Open classification pie chart

### Method 3: Manual File Browser

```bash
# Open results directory
cd /home/anik/code/BGP-Sentry/experiment_results

# List all experiments
ls -lt

# Open latest experiment folder
cd attack_experiment_YYYYMMDD_HHMMSS/

# View images
eog rating_dashboard.png          # Rating evolution dashboard
eog rating_summary_table.png      # Summary statistics table
eog classification_distribution.png # RED/YELLOW/GREEN pie chart
```

## 📊 What Each Visualization Shows

### 1. Rating Dashboard (`rating_dashboard.png`)

**8-Plot Grid** showing rating evolution over time:

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ AS666 🔴     │ AS31337 🔴   │ AS100 🟢     │ AS200 🟡     │
│ Rating: 30.0 │ Rating: 38.0 │ Rating: 85.0 │ Rating: 65.0 │
│ Attacks: 12  │ Attacks: 8   │ Attacks: 0   │ Attacks: 2   │
│              │              │              │              │
│ [Line Plot]  │ [Line Plot]  │ [Line Plot]  │ [Line Plot]  │
│              │              │              │              │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ AS300 🟢     │ AS400 🟡     │ AS500 🟢     │ AS600 🟢     │
│ (4 more AS plots...)                                      │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**Each subplot shows**:
- Rating line (0-100 scale)
- Background colors (RED/YELLOW/GREEN zones)
- Red stars (★) marking attack detections
- Final classification badge

### 2. Summary Table (`rating_summary_table.png`)

**Tabular Statistics**:

| AS Number | Initial | Final | Change | Min | Max | Attacks | Classification |
|-----------|---------|-------|--------|-----|-----|---------|----------------|
| AS666     | 50.0    | 30.0  | -20.0  | 30.0| 50.0| 12      | 🔴 RED (Malicious) |
| AS31337   | 50.0    | 38.0  | -12.0  | 38.0| 50.0| 8       | 🟡 YELLOW (Suspicious) |
| AS100     | 50.0    | 50.0  | 0.0    | 50.0| 50.0| 0       | 🟡 YELLOW (Suspicious) |

### 3. Classification Distribution (`classification_distribution.png`)

**Pie Chart** showing:
- 🔴 RED (0-40): X ASes
- 🟡 YELLOW (41-70): Y ASes
- 🟢 GREEN (71-100): Z ASes

With percentages and counts.

## 🔍 View Current Non-RPKI Ratings (Real-time)

To see the **current** ratings at any time:

```bash
python3 view_rating_results.py
# Select option 1: Show current non-RPKI ratings
```

**Output Example**:
```
📊 CURRENT NON-RPKI AS RATINGS
══════════════════════════════════════════════════════════════════════

AS Number       Rating     Level           Attacks    Last Updated
──────────────────────────────────────────────────────────────────────
AS666           30.0       🔴 bad          12         2025-10-21 20:30:15
AS31337         38.0       🔴 suspicious   8          2025-10-21 20:30:15
AS100           50.0       ⚪ neutral      0          2025-10-21 20:25:00
AS200           65.0       🟡 suspicious   2          2025-10-21 20:28:10

📊 Total non-RPKI ASes rated: 4

📈 Rating Distribution:
   bad             ██ (2)
   neutral         █ (1)
   suspicious      █ (1)
```

## 📂 File Locations

### Experiment Results
```
/home/anik/code/BGP-Sentry/experiment_results/
└── attack_experiment_YYYYMMDD_HHMMSS/
    ├── attack_scenarios.json              # Ground truth
    ├── rating_monitoring_data.json        # Time-series data
    ├── blockchain_performance_report.json # TPS metrics
    ├── rating_dashboard.png               # 🖼️ 8-plot dashboard
    ├── rating_summary_table.png           # 🖼️ Summary table
    ├── classification_distribution.png    # 🖼️ Pie chart
    └── detection_accuracy_report.json     # Accuracy metrics
```

### Current Ratings (Live Data)
```
/home/anik/code/BGP-Sentry/nodes/rpki_nodes/
└── as01/blockchain_node/blockchain_data/state/
    └── nonrpki_ratings.json               # Current ratings
```

## 📈 View Blockchain Performance

```bash
python3 view_rating_results.py
# Select option 4: Show blockchain performance
```

**Shows**:
- Average TPS (transactions/second)
- Peak TPS
- Total transactions and blocks
- Throughput (KB/s, MB/s)
- Performance classification (EXCELLENT/GOOD/MODERATE/LOW)

**Example Output**:
```
⚡ BLOCKCHAIN PERFORMANCE METRICS
══════════════════════════════════════════════════════════════════════

📊 Performance Summary:
   Duration: 5.20 minutes
   Total Transactions: 2020
   Total Blocks: 145

⚡ Transaction Performance:
   Average TPS: 6.47 transactions/second
   Peak TPS: 12.50 transactions/second
   Avg Tx/Block: 13.93

📦 Block Performance:
   Block Rate: 27.88 blocks/minute

📈 Network Throughput:
   Throughput: 3.24 KB/s
   Throughput: 0.0032 MB/s

   🟡 Performance: LOW (1-10 TPS)
```

## 🔄 Regenerate Visualizations

If visualizations are missing or you want fresh versions:

```bash
python3 view_rating_results.py
# Select option 3: Regenerate visualizations
```

This will:
- Find latest monitoring data
- Create new rating dashboard
- Create new summary table
- Create new pie chart

## 💡 Tips

### View Multiple Experiments

```bash
# List all experiments
ls -lt /home/anik/code/BGP-Sentry/experiment_results/

# View specific experiment
cd /home/anik/code/BGP-Sentry/experiment_results/attack_experiment_20251021_203000/
eog rating_dashboard.png
```

### Compare Experiments

Open dashboards from different runs side-by-side:

```bash
# Experiment 1
eog experiment_results/attack_experiment_20251021_203000/rating_dashboard.png &

# Experiment 2
eog experiment_results/attack_experiment_20251021_205000/rating_dashboard.png &
```

### Check Rating Changes in Real-time

Monitor rating file changes:

```bash
watch -n 5 "cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json | jq '.as_ratings'"
```

### Export Data for External Analysis

All data is in JSON format - easy to process:

```python
import json

# Load monitoring data
with open('experiment_results/attack_experiment_YYYYMMDD_HHMMSS/rating_monitoring_data.json') as f:
    data = json.load(f)

# Extract time series for AS666
as666_ratings = data['time_series']['666']['ratings']
as666_timestamps = data['time_series']['666']['timestamps']

# Plot with your own tools...
```

## 🎨 Custom Visualization

You can create custom plots from the monitoring data:

```python
from rating_visualization import RatingVisualization

# Load your data
viz = RatingVisualization('path/to/rating_monitoring_data.json')

# Create custom dashboard
viz.create_dashboard(output_file='my_custom_dashboard.png')

# Create custom table
viz.create_summary_table(output_file='my_table.png')
```

## ❓ Troubleshooting

### "No experiment results found"

**Problem**: Haven't run experiment yet

**Solution**:
```bash
python3 run_attack_experiment.py
```

### "No rating file found"

**Problem**: No attacks detected yet (ratings only created when attacks found)

**Solution**: Wait for experiment to detect attacks, or check if attack detection is working

### "Visualization files missing"

**Problem**: Experiment didn't complete or visualization failed

**Solution**:
```bash
python3 view_rating_results.py
# Select option 3 to regenerate
```

### "Cannot open image files"

**Problem**: No image viewer installed

**Solution**:
```bash
# Install image viewer
sudo apt install eog

# Or use xdg-open
xdg-open rating_dashboard.png
```

## 📚 Summary of Commands

```bash
# Interactive viewer (recommended)
python3 view_rating_results.py

# Quick dashboard opener
./open_dashboard.sh

# Manual view
cd experiment_results/
ls -lt
cd attack_experiment_*/
eog rating_dashboard.png

# View specific file
eog /home/anik/code/BGP-Sentry/experiment_results/attack_experiment_*/rating_dashboard.png

# View current ratings (JSON)
cat nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json | jq
```

## 🎯 What to Look For

### In the Dashboard:
- ✅ **Attackers** (AS666, AS31337) should show **downward trends** into RED zone
- ✅ **Red stars (★)** should appear when attacks detected
- ✅ **Legitimate ASes** should stay in GREEN/YELLOW zones
- ✅ **Final badges** show correct classification

### In the Summary Table:
- ✅ **Rating Change** should be negative for attackers
- ✅ **Attacks Detected** matches injected attacks
- ✅ **Classification** matches expected (RED for bad, GREEN for good)

### In Performance Report:
- ✅ **TPS** should be >1 for good performance
- ✅ **Total Transactions** should be ~2000 (20 attacks + 1980 legitimate)
- ✅ **No errors** in blockchain processing

---

**Quick Start**: Just run `python3 view_rating_results.py` and select option 1 or 2! 🚀
