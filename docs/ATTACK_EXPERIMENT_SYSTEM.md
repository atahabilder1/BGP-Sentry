

# Attack Experiment System - Complete Documentation

## 📋 Overview

This system provides a complete framework for injecting controlled attack scenarios, monitoring rating changes, and analyzing detection accuracy in the BGP-Sentry blockchain system.

## 🎯 Purpose

Test the attack detection and rating system by:
1. Injecting 20 attack scenarios into 2 specific non-RPKI ASes
2. Monitoring rating changes in real-time as attacks are detected
3. Generating comprehensive visualizations showing rating evolution
4. Classifying ASes into RED/YELLOW/GREEN categories
5. Calculating detection accuracy and effectiveness

## 🗂️ System Components

### 1. **Attack Injection System**
**File**: `attack_injection_system.py`

**Purpose**: Generate and inject controlled attack scenarios

**Features**:
- Inject customizable number of attacks per AS
- Support 3 attack types:
  - IP Prefix Hijacking (50%)
  - Sub-Prefix Hijacking (30%)
  - Route Leak (20%)
- Ground truth tracking for accuracy calculation
- ROA database integration

**Usage**:
```python
from attack_injection_system import AttackInjectionSystem

injector = AttackInjectionSystem()

# Inject 12 attacks to AS666, 8 to AS31337
results = injector.inject_attack_scenarios([
    (666, 12),
    (31337, 8)
])
```

### 2. **Rating Monitor**
**File**: `rating_monitor.py`

**Purpose**: Track rating changes in real-time

**Features**:
- Real-time rating snapshots
- Time-series data collection
- Attack detection event logging
- Export data for visualization

**Usage**:
```python
from rating_monitor import RatingMonitor

monitor = RatingMonitor()

# Start monitoring AS666 and AS31337
monitor.start_monitoring([666, 31337])

# Run monitoring loop (5 minutes, 10 second intervals)
monitor.monitor_loop(duration_seconds=300, interval_seconds=10)

# Export for visualization
monitor.export_for_visualization()
```

### 3. **Rating Visualization**
**File**: `rating_visualization.py`

**Purpose**: Generate visual analysis and reports

**Features**:
- **8-Plot Dashboard**: Shows rating evolution for up to 8 ASes on one page
- **Color Classification**:
  - 🔴 **RED (0-40)**: Malicious / Bad behavior
  - 🟡 **YELLOW (41-70)**: Medium / Suspicious
  - 🟢 **GREEN (71-100)**: Good / Trustworthy
- **Summary Table**: Detailed statistics for all monitored ASes
- **Classification Distribution**: Pie chart showing RED/YELLOW/GREEN distribution

**Usage**:
```python
from rating_visualization import RatingVisualization

viz = RatingVisualization("rating_monitoring_data.json")

# Create 8-plot dashboard
viz.create_dashboard(output_file="dashboard.png")

# Create summary table
viz.create_summary_table(output_file="summary.png")

# Create classification pie chart
viz.create_classification_pie_chart(output_file="distribution.png")
```

### 4. **Complete Experiment Runner**
**File**: `run_attack_experiment.py`

**Purpose**: Orchestrate complete experiment workflow

**Features**:
- Automated experiment execution
- Integrated attack injection, monitoring, and visualization
- Detection accuracy calculation
- Comprehensive result reports

## 🚀 Quick Start

### Step 1: Run Complete Experiment

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

**What happens**:
1. ✅ Injects 20 attack scenarios (12 to AS666, 8 to AS31337)
2. ✅ Prompts you to start your BGP-Sentry simulation
3. ✅ Monitors ratings every 10 seconds for 5 minutes
4. ✅ Generates 6 output files (see below)

### Step 2: View Results

All results are saved to timestamped directory:
```
/home/anik/code/BGP-Sentry/experiment_results/attack_experiment_YYYYMMDD_HHMMSS/
```

**Generated Files**:
1. `attack_scenarios.json` - Ground truth attack data
2. `rating_monitoring_data.json` - Time-series rating data
3. `rating_dashboard.png` - 8-plot visualization
4. `rating_summary_table.png` - Summary statistics table
5. `classification_distribution.png` - Pie chart
6. `detection_accuracy_report.json` - Detection metrics

## 📊 Visualization Examples

### 8-Plot Dashboard Layout
```
┌────────────────────────────────────────────────────────────┐
│  Non-RPKI AS Rating Evolution Dashboard                   │
│  Color Classification: RED (0-40) | YELLOW (41-70) | GREEN (71-100)│
├─────────────┬─────────────┬─────────────┬─────────────────┤
│  AS666 🔴   │  AS31337🔴  │  AS100 🟢   │  AS200 🟡      │
│  Rating:32.0│  Rating:38.0│  Rating:85.0│  Rating:65.0   │
│  Attacks:12 │  Attacks:8  │  Attacks:0  │  Attacks:2     │
│             │             │             │                │
│ [Plot]      │ [Plot]      │ [Plot]      │ [Plot]         │
│             │             │             │                │
├─────────────┼─────────────┼─────────────┼────────────────┤
│  AS300 🟢   │  AS400 🟡   │  AS500 🟢   │  AS600 🟢      │
│  Rating:90.0│  Rating:55.0│  Rating:95.0│  Rating:80.0   │
│  Attacks:0  │  Attacks:3  │  Attacks:0  │  Attacks:1     │
│             │             │             │                │
│ [Plot]      │ [Plot]      │ [Plot]      │ [Plot]         │
│             │             │             │                │
└─────────────┴─────────────┴─────────────┴────────────────┘
```

### Each Plot Shows:
- **Line Graph**: Rating evolution over time
- **Background Colors**: RED/YELLOW/GREEN zones
- **Red Stars**: Attack detection events
- **Final Badge**: Current classification

### Summary Table Structure
| AS Number | Initial Rating | Final Rating | Rating Change | Attacks Detected | Classification |
|-----------|---------------|--------------|---------------|------------------|----------------|
| AS666     | 50.0          | 30.0         | -20.0         | 12               | RED (Malicious) |
| AS31337   | 50.0          | 38.0         | -12.0         | 8                | YELLOW (Suspicious) |
| AS100     | 50.0          | 50.0         | 0.0           | 0                | YELLOW (Suspicious) |

## 🎨 Color Classification System

### Thresholds
- **RED (0-40)**: Malicious behavior detected, multiple attacks confirmed
- **YELLOW (41-70)**: Suspicious behavior, some attacks or irregular patterns
- **GREEN (71-100)**: Trustworthy, legitimate behavior

### Rating Penalties
- **IP Prefix Hijacking**: -20 points (CRITICAL)
- **Sub-Prefix Hijacking**: -15 points (HIGH)
- **Route Leak**: -10 points (MEDIUM)

## 📈 Detection Accuracy Metrics

### Calculated Metrics
1. **Detection Efficiency**: `(Actual Rating Drop / Expected Rating Drop) × 100%`
2. **Average Rating Drop Per Attack**: Total rating change / number of attacks
3. **Final Classification**: RED/YELLOW/GREEN category

### Example Report
```json
{
  "total_attacks_injected": 20,
  "average_rating_drop_per_attack": "7.5",
  "attackers": [
    {
      "as_number": 666,
      "attacks_injected": 12,
      "rating_change": -20.0,
      "final_rating": 30.0,
      "final_classification": "RED (Malicious)",
      "detection_efficiency": "85.5%"
    }
  ]
}
```

## 🔧 Customization

### Modify Attack Distribution

Edit `run_attack_experiment.py`:
```python
runner.run_complete_experiment(
    attacker_ases=[
        (666, 20),      # 20 attacks to AS666
        (31337, 10),    # 10 attacks to AS31337
        (8888, 5)       # 5 attacks to AS8888
    ],
    monitor_duration=600,   # Monitor for 10 minutes
    monitor_interval=5      # Snapshot every 5 seconds
)
```

### Modify Classification Thresholds

Edit `rating_visualization.py`:
```python
THRESHOLDS = {
    "red_max": 30,       # Change RED threshold to 0-30
    "yellow_max": 60,    # Change YELLOW threshold to 31-60
    "green_min": 61      # Change GREEN threshold to 61-100
}
```

### Modify Attack Type Distribution

Edit `attack_injection_system.py`:
```python
def _distribute_attack_types(self, total_count: int):
    return {
        "ip_prefix_hijacking": int(total_count * 0.7),    # 70%
        "sub_prefix_hijacking": int(total_count * 0.2),   # 20%
        "route_leak": int(total_count * 0.1)              # 10%
    }
```

## 🧪 Manual Step-by-Step Execution

### Option 1: Complete Automated Experiment
```bash
python3 run_attack_experiment.py
```

### Option 2: Manual Step-by-Step

**Step 1 - Inject Attacks**:
```python
from attack_injection_system import AttackInjectionSystem

injector = AttackInjectionSystem()
results = injector.inject_attack_scenarios([(666, 12), (31337, 8)])
```

**Step 2 - Start BGP-Sentry Simulation**:
```bash
# In separate terminal, run your simulation
python main_experiment.py
```

**Step 3 - Monitor Ratings**:
```python
from rating_monitor import RatingMonitor

monitor = RatingMonitor()
monitor.start_monitoring([666, 31337])
monitor.monitor_loop(duration_seconds=300, interval_seconds=10)
viz_file = monitor.export_for_visualization()
```

**Step 4 - Generate Visualizations**:
```python
from rating_visualization import RatingVisualization

viz = RatingVisualization(viz_file)
viz.create_dashboard()
viz.create_summary_table()
viz.create_classification_pie_chart()
```

## 📂 File Structure

```
BGP-Sentry/
├── nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils/
│   ├── attack_injection_system.py      # Attack injection
│   ├── rating_monitor.py                # Real-time monitoring
│   ├── rating_visualization.py          # Visualization dashboard
│   └── run_attack_experiment.py         # Complete orchestration
│
├── nodes/rpki_nodes/shared_blockchain_stack/shared_data/state/
│   ├── attack_scenarios_injected.json   # Injected attacks
│   ├── rating_monitor_data.json         # Monitoring snapshots
│   └── rating_visualization_data.json   # Export for visualization
│
└── experiment_results/
    └── attack_experiment_YYYYMMDD_HHMMSS/
        ├── attack_scenarios.json
        ├── rating_monitoring_data.json
        ├── rating_dashboard.png         # 8-plot dashboard
        ├── rating_summary_table.png     # Summary table
        ├── classification_distribution.png
        └── detection_accuracy_report.json
```

## 🔍 Ground Truth Data

### Attack Scenarios JSON Structure
```json
{
  "injection_timestamp": "2025-10-21T20:00:00",
  "total_attacks": 20,
  "attackers": {
    "666": {
      "total_attacks": 12,
      "attack_breakdown": {
        "ip_prefix_hijacking": 6,
        "sub_prefix_hijacking": 4,
        "route_leak": 2
      }
    }
  },
  "ground_truth": {
    "attack_666_001": {
      "attacker_as": 666,
      "attack_type": "ip_prefix_hijacking",
      "victim_as": 15169,
      "hijacked_prefix": "8.8.8.0/24",
      "should_detect": true
    }
  }
}
```

## 📊 Understanding the Dashboard

### Reading the 8-Plot Dashboard

**Each subplot shows**:
- **Title**: AS number, classification emoji, current rating, attacks detected
- **Line**: Rating evolution over time (0-100 scale)
- **Background zones**:
  - Light RED: Malicious zone (0-40)
  - Light YELLOW: Suspicious zone (41-70)
  - Light GREEN: Good zone (71-100)
- **Red stars (★)**: Points where attacks were detected
- **Badge**: Final classification label

### Interpreting Results

**Good Detection**:
- AS starts at 50 (neutral)
- Rating drops sharply when attacks detected
- Ends in RED zone (<40) for attackers
- Red stars align with attack events

**Poor Detection**:
- Rating remains high despite attacks
- Few or no red stars
- Stays in YELLOW/GREEN zones

## ⚙️ Dependencies

Required packages:
```bash
pip install matplotlib numpy
```

Already available in BGP-Sentry project.

## 🎯 Expected Results

### For AS666 (12 Attacks Injected)

**Expected Behavior**:
- Initial Rating: 50.0
- Expected Final Rating: ~30.0 (RED zone)
- Rating Drop: -20.0 to -40.0
- Classification: RED (Malicious)

### For AS31337 (8 Attacks Injected)

**Expected Behavior**:
- Initial Rating: 50.0
- Expected Final Rating: ~38.0 (YELLOW/RED border)
- Rating Drop: -12.0 to -25.0
- Classification: YELLOW (Suspicious) or RED (Malicious)

## 🐛 Troubleshooting

### No Rating Changes Observed

**Problem**: Ratings stay at 50.0 despite attacks

**Solutions**:
1. Verify BGP-Sentry simulation is running
2. Check attack detection system is enabled
3. Ensure consensus voting is working (need 3+ nodes)
4. Verify ROA database has entries for hijacked prefixes

### Visualization Shows No Data

**Problem**: Dashboard plots are empty

**Solutions**:
1. Run monitoring for longer duration
2. Check `rating_monitor_data.json` exists
3. Verify rating files exist in AS folders
4. Ensure monitoring happened AFTER attacks injected

### Import Errors

**Problem**: `ModuleNotFoundError` for components

**Solutions**:
```bash
# Ensure you're in correct directory
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils

# Run with python3
python3 run_attack_experiment.py
```

## 📝 Next Steps

After running experiment:

1. **Analyze Results**: Review detection accuracy report
2. **Tune Thresholds**: Adjust RED/YELLOW/GREEN boundaries if needed
3. **Increase Attacks**: Test with more attack scenarios
4. **Long-term Study**: Run monitoring for hours/days
5. **Compare Methods**: Test different detection algorithms

## 🎓 Research Use Cases

This system supports:
- **Detection Rate Studies**: Calculate true positive/false positive rates
- **Threshold Optimization**: Find optimal RED/YELLOW/GREEN boundaries
- **Behavioral Analysis**: Study long-term attacker patterns
- **Consensus Effectiveness**: Test voting threshold impact
- **Rating System Validation**: Verify penalties align with severity

## ✅ Summary

**You now have a complete attack experiment system that**:
1. ✅ Injects 20 controlled attacks (12 to AS666, 8 to AS31337)
2. ✅ Monitors rating changes in real-time
3. ✅ Generates 8-plot dashboard with RED/YELLOW/GREEN classification
4. ✅ Creates summary tables and distribution charts
5. ✅ Calculates detection accuracy metrics
6. ✅ Stores all data for post-hoc analysis

**Run now**:
```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

**Questions?** Check the individual script files for detailed docstrings and examples!
