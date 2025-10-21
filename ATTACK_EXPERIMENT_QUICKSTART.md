# 🚀 Attack Experiment System - Quick Start Guide

## ✅ What's Been Created

I've built a complete attack injection, monitoring, and visualization system for your BGP-Sentry project:

### 📦 5 New Tools

1. **`attack_injection_system.py`** - Inject controlled attacks (<1% ratio) with legitimate traffic
2. **`rating_monitor.py`** - Track rating changes in real-time
3. **`rating_visualization.py`** - Generate 8-plot dashboard with RED/YELLOW/GREEN classification
4. **`blockchain_performance_monitor.py`** - Measure TPS and blockchain performance
5. **`run_attack_experiment.py`** - Complete automated experiment runner

### 🎯 What It Does

✅ Injects **20 attack scenarios** (12 to AS666, 8 to AS31337)
✅ Generates **~2000 legitimate announcements** (attack ratio <1%)
✅ Monitors rating changes every 10 seconds
✅ **Measures blockchain performance (TPS, throughput, latency)**
✅ Generates **8-plot dashboard** showing rating evolution
✅ Classifies ASes into **RED/YELLOW/GREEN** categories:
- 🔴 **RED (0-40)**: Malicious
- 🟡 **YELLOW (41-70)**: Suspicious
- 🟢 **GREEN (71-100)**: Trustworthy

✅ Creates **summary table** with statistics
✅ Generates **pie chart** showing classification distribution
✅ Calculates **detection accuracy** metrics
✅ Reports **blockchain performance** (TPS, throughput)

## 🏃 Run Complete Experiment (5 Minutes)

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

**The script will**:
1. Inject 20 attacks into AS666 (12) and AS31337 (8)
2. Prompt you to start your BGP-Sentry simulation
3. **Open live visualization window** showing real-time rating changes
4. Monitor ratings for 5 minutes (10-second intervals)
5. Display TPS and detection rate live
6. Generate all visualizations automatically

**NEW: Live Visualization!** 🎨
- A plot window opens showing real-time rating changes
- Updates every 10 seconds as experiment runs
- See attackers' ratings drop in real-time
- Monitor blockchain TPS and detection rate live
- Color-coded zones (RED/YELLOW/GREEN)

## 📊 Output Files

All results saved to:
```
/home/anik/code/BGP-Sentry/experiment_results/attack_experiment_YYYYMMDD_HHMMSS/
```

**Generated files**:
- ✅ `attack_scenarios.json` - Ground truth (20 attacks + ~2000 legitimate)
- ✅ `rating_monitoring_data.json` - Time-series rating data
- ✅ `blockchain_performance_report.json` - **TPS, throughput, latency metrics**
- ✅ `rating_dashboard.png` - **8-plot visualization**
- ✅ `rating_summary_table.png` - Statistics table
- ✅ `classification_distribution.png` - Pie chart
- ✅ `detection_accuracy_report.json` - Accuracy metrics

## 🎨 What the Dashboard Looks Like

```
┌─────────────────────────────────────────────────────────┐
│  8-Plot Rating Evolution Dashboard                     │
│  RED (0-40) | YELLOW (41-70) | GREEN (71-100)         │
├──────────────┬──────────────┬──────────────┬──────────┤
│ AS666 🔴     │ AS31337 🔴   │ AS100 🟢     │ AS200🟡 │
│ Rating: 30.0 │ Rating: 38.0 │ Rating: 85.0 │ Rating:65│
│ Attacks: 12  │ Attacks: 8   │ Attacks: 0   │Attacks:2│
│              │              │              │          │
│ [Time plot]  │ [Time plot]  │ [Time plot]  │[Plot]   │
│   with red   │   with red   │   clean      │ medium  │
│   stars ★    │   stars ★    │   line       │ drop    │
├──────────────┼──────────────┼──────────────┼─────────┤
│ (4 more AS plots in second row...)                    │
└─────────────────────────────────────────────────────────┘
```

Each plot shows:
- Rating line (0-100)
- Background colors (RED/YELLOW/GREEN zones)
- Red stars (★) at attack detection points
- Final classification badge

## 🔧 Customize (Optional)

### Change Attack Distribution

Edit `run_attack_experiment.py`, line 205:
```python
attacker_ases=[(666, 20), (31337, 15), (8888, 10)]  # 45 total attacks
```

### Change Monitoring Duration

Edit `run_attack_experiment.py`, line 206-207:
```python
monitor_duration=600,    # 10 minutes instead of 5
monitor_interval=5       # 5 second snapshots instead of 10
```

### Change Color Thresholds

Edit `rating_visualization.py`, lines 33-37:
```python
THRESHOLDS = {
    "red_max": 30,      # RED zone: 0-30
    "yellow_max": 60,   # YELLOW zone: 31-60
    "green_min": 61     # GREEN zone: 61-100
}
```

## 📋 Ground Truth System

### How Non-RPKI Announcements Are Populated

The system uses **ROA Database** as ground truth:

**Location**:
```
nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/roa_database.json
```

**Structure**:
```json
{
  "roas": [
    {"prefix": "8.8.8.0/24", "asn": 15169, "source": "rpki"},
    {"prefix": "192.168.100.0/24", "asn": 100, "source": "irr"}
  ]
}
```

**Attack injection reads this to**:
- Select victim prefixes (e.g., 8.8.8.0/24 owned by AS15169)
- Generate hijacking attacks (AS666 announces 8.8.8.0/24)
- Track ground truth for detection validation

## 🎯 Expected Results

### AS666 (12 Attacks)
- Initial: 50.0 (neutral)
- Expected Final: ~30.0 (RED)
- Classification: 🔴 Malicious

### AS31337 (8 Attacks)
- Initial: 50.0 (neutral)
- Expected Final: ~38.0 (RED/YELLOW border)
- Classification: 🟡 Suspicious or 🔴 Malicious

## 📚 Full Documentation

See detailed guide: `docs/ATTACK_EXPERIMENT_SYSTEM.md`

## ❓ Troubleshooting

### No rating changes?
- Ensure BGP-Sentry simulation is running
- Check consensus system is active (need 3+ nodes voting)
- Verify attack detection is enabled

### Empty visualizations?
- Run monitoring for longer (increase `monitor_duration`)
- Check rating files exist: `nodes/rpki_nodes/as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json`

### Import errors?
```bash
# Make sure you're in the right directory
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

## ⚡ Blockchain Performance Report

The experiment also measures blockchain performance:

**Metrics Collected**:
- **Average TPS**: Transactions per second (average)
- **Peak TPS**: Maximum TPS observed
- **Block Rate**: Blocks per minute/second
- **Throughput**: KB/s and MB/s
- **Tx per Block**: Average transactions per block

**Example Output**:
```json
{
  "average_tps": 15.32,
  "peak_tps": 28.45,
  "total_transactions": 2020,
  "total_blocks": 145,
  "average_tx_per_block": 13.93,
  "throughput_kb_per_second": 7.66,
  "duration_minutes": 5.2
}
```

**Performance Classification**:
- ✅ **EXCELLENT**: >100 TPS
- ✅ **GOOD**: 50-100 TPS
- 🟡 **MODERATE**: 10-50 TPS
- 🟡 **LOW**: 1-10 TPS
- 🔴 **VERY LOW**: <1 TPS

## 🎉 You're Ready!

**Everything is set up and ready to use!**

Run this now:
```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

**Within 10 minutes you'll have**:
- ✅ 20 attacks injected with ~2000 legitimate announcements (<1% attack ratio)
- ✅ 8-plot dashboard showing rating evolution
- ✅ Color-coded classification (RED/YELLOW/GREEN)
- ✅ Summary table and pie charts
- ✅ Detection accuracy report
- ✅ **Blockchain performance metrics (TPS, throughput)**

Have fun experimenting! 🚀
