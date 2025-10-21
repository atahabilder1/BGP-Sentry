# 🎨 Live Rating Visualization - Real-time Monitoring

## 🚀 What is Live Visualization?

The live visualization feature shows **real-time rating changes** as they happen during your experiment. A matplotlib window pops up and updates every 10 seconds, displaying:

- ✅ **8 rating plots** - One for each non-RPKI AS being monitored
- ✅ **Color-coded zones** - RED (0-40), YELLOW (41-70), GREEN (71-100)
- ✅ **Attack detection markers** - Red stars (★) when attacks detected
- ✅ **Blockchain performance** - Live TPS graph
- ✅ **Detection metrics** - Real-time detection rate

## 📊 What You'll See

### Live Plot Window Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│          🔴 LIVE NON-RPKI RATING MONITOR 🔴                        │
│      Real-time Rating Evolution During Attack Experiment            │
├─────────────┬─────────────┬─────────────┬─────────────────────────┤
│             │             │             │                         │
│   AS666     │  AS31337    │   AS100     │   AS200                │
│   Rating    │   Rating    │   Rating    │   Rating               │
│   Plot      │   Plot      │   Plot      │   Plot                 │
│             │             │             │                         │
├─────────────┼─────────────┼─────────────┼─────────────────────────┤
│             │             │             │                         │
│   AS300     │  AS400      │   AS500     │   AS600                │
│   Plot      │   Plot      │   Plot      │   Plot                 │
│             │             │             │                         │
├─────────────┴─────────────┼─────────────┴─────────────────────────┤
│                           │                                       │
│  Blockchain Performance   │    Attack Detection Metrics          │
│  (TPS Graph)             │    (Detection Rate Display)          │
│                           │                                       │
└───────────────────────────┴───────────────────────────────────────┘
```

### Rating Plot Features

Each AS rating plot shows:
- **Line graph**: Rating value over time (0-100 scale)
- **Background colors**:
  - Light red background: RED zone (0-40) = Bad/Malicious
  - Light yellow background: YELLOW zone (41-70) = Suspicious
  - Light green background: GREEN zone (71-100) = Trustworthy
- **Red stars (★)**: Appear when new attack detected
- **Info box**: Current rating, attacks detected, classification

### Performance Plot

Bottom-left panel shows:
- **TPS over time**: Transactions per second
- **Color zones**:
  - Red (0-1): Very Low
  - Yellow (1-10): Low
  - Light green (10-50): Moderate
  - Green (50+): Good
- **Stats box**: Total transactions, blocks, avg/peak TPS

### Detection Metrics

Bottom-right panel displays:
- **Total attacks injected**: 20
- **Total attacks detected**: Updates in real-time
- **Detection rate**: Percentage (0-100%)
- **Status**: Color-coded (Green=Excellent, Yellow=Moderate, Red=Low)

## 🎯 How to Use

### Automatic (Default)

Live visualization is **enabled by default** when running the experiment:

```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

**When prompted:**
```
Enable live visualization? (y/n) [default: y]:
```

Just press **Enter** or type **y** to enable.

### Manual Control

**Disable live visualization:**
```
Enable live visualization? (y/n) [default: y]: n
```

**Test live monitor (standalone):**
```bash
python3 live_rating_monitor.py
```

This runs a 30-second demo with dummy data to test the visualization.

## 📈 What to Watch For

### During Experiment

**Attackers (AS666, AS31337):**
- ✅ Lines should **trend downward** over time
- ✅ Rating should **drop into RED/YELLOW zones**
- ✅ **Red stars should appear** as attacks are detected
- ✅ Info box should show increasing attack count

**Legitimate ASes (AS100, AS200, etc.):**
- ✅ Lines should **stay stable or trend upward**
- ✅ Should remain in **GREEN/YELLOW zones**
- ✅ **Few or no red stars** (minimal false positives)
- ✅ Attack count should stay at 0 or very low

**Performance:**
- ✅ TPS should be **> 1.0** for basic functionality
- ✅ TPS **> 10** indicates good performance
- ✅ Graph should show steady or increasing TPS

**Detection:**
- ✅ Detection rate should **increase over time**
- ✅ Should reach **95-100%** by end of experiment
- ✅ Status box should turn **green** when detection rate high

### Red Flags

**Issues to investigate if you see:**
- ❌ Attacker ratings **not decreasing** (detection not working)
- ❌ Legitimate AS ratings **dropping** (too many false positives)
- ❌ **No red stars appearing** (attacks not being detected)
- ❌ TPS **= 0 or very low** (blockchain not processing)
- ❌ Detection rate **stuck at 0%** (consensus not working)

## 🎮 Interactive Features

### During Monitoring

**The plot updates automatically every 10 seconds**

You can:
- ✅ **Resize the window** - Drag corners to resize
- ✅ **Zoom in/out** - Use matplotlib toolbar
- ✅ **Pan around** - Use matplotlib pan tool
- ✅ **Save snapshot** - Use matplotlib save button

### After Monitoring

**When monitoring completes:**
```
💡 Keeping live visualization window open...
   You can review the final state before proceeding.
   Press Enter to continue with post-processing...
```

**Take your time to:**
- Review final ratings
- Check all plots
- Take screenshots if needed
- Then press **Enter** to continue

## 💡 Tips

### Screenshot for Documentation

**During experiment:**
1. Let the experiment run for a few minutes
2. Resize window for best view
3. Use screenshot tool: `gnome-screenshot` or `flameshot`
4. Save for your report/paper

**From matplotlib toolbar:**
1. Click the **save icon** (💾)
2. Choose PNG format
3. Save to your desired location

### Troubleshooting

**Window doesn't appear:**
- Check if `DISPLAY` environment variable is set
- Try running: `export DISPLAY=:0`
- Or disable live viz and use post-hoc visualizations

**Window freezes or lags:**
- Normal if system is under heavy load
- Reduce monitoring frequency (increase interval to 20s)
- Disable live viz and use post-hoc analysis instead

**Plot not updating:**
- Check if matplotlib backend supports interactive mode
- Try: `export MPLBACKEND=TkAgg`
- Or use post-hoc visualizations

**Colors not showing correctly:**
- This is cosmetic - data is still being collected
- Post-hoc visualizations will have correct colors

## 🔧 Advanced Configuration

### Custom AS List

Monitor specific ASes:

```python
from live_rating_monitor import LiveRatingMonitor

# Monitor custom ASes
monitor = LiveRatingMonitor(
    monitored_ases=[666, 31337, 100, 200, 300, 400, 500, 600],
    project_root="/path/to/BGP-Sentry"
)
```

### Update Rating Data

```python
# Update rating for AS666
monitor.update_rating(
    as_num=666,
    rating=42.5,
    attacks_detected=8,
    timestamp=datetime.now()
)

# Update performance
monitor.update_performance(
    tps=12.5,
    total_tx=1500,
    total_blocks=120,
    elapsed_seconds=180
)

# Update detection metrics
monitor.update_detection(
    total_detected=18,
    total_injected=20
)

# Refresh plot
monitor.refresh_plot()
```

### Keep Window Open

```python
# Keep plot open after monitoring
monitor.keep_open()  # Blocks until window closed
```

## 📊 Comparison: Live vs Post-hoc

| Feature | Live Visualization | Post-hoc Dashboard |
|---------|-------------------|-------------------|
| **Timing** | During experiment | After experiment |
| **Updates** | Real-time (every 10s) | Static |
| **Use Case** | Monitoring progress | Final analysis |
| **Interactivity** | High (zoom, pan) | Low (static image) |
| **Performance Impact** | Slight | None |
| **Best For** | Watching experiment | Reports/papers |

**Recommendation:** Use **both**!
- Live visualization to **monitor** experiment
- Post-hoc dashboard for **analysis** and **documentation**

## 🎓 Example Workflow

**Recommended workflow with live visualization:**

1. **Start experiment**
   ```bash
   python3 run_attack_experiment.py
   ```

2. **Enable live visualization**
   ```
   Enable live visualization? (y/n) [default: y]: y
   ```

3. **Watch the live plot**
   - Observe attackers' ratings dropping
   - See detection rate increasing
   - Monitor TPS performance

4. **Take screenshots** (optional)
   - Capture interesting moments
   - Save for documentation

5. **Review final state**
   - When monitoring ends, review final plot
   - Check all metrics
   - Press Enter to continue

6. **Analyze post-hoc results**
   ```bash
   python3 analyze_experiment.py
   eog experiment_results/attack_experiment_*/rating_dashboard.png
   ```

## ✅ Benefits

**Why use live visualization?**

1. **Immediate feedback**: See if experiment is working correctly
2. **Early detection**: Spot issues early (e.g., TPS=0, no detections)
3. **Confidence**: Watch ratings change as expected
4. **Debugging**: Identify problems during experiment, not after
5. **Engagement**: More interesting than staring at console output
6. **Documentation**: Easy to screenshot for presentations

## 🚫 When to Disable

**Disable live visualization if:**

- Running on headless server (no display)
- Low system resources
- Running batch experiments (multiple runs)
- Prefer post-hoc analysis only
- Matplotlib not installed

**How to disable:**
```bash
# When prompted:
Enable live visualization? (y/n) [default: y]: n
```

Or in code:
```python
runner.run_complete_experiment(
    enable_live_visualization=False
)
```

## 📚 Related Documentation

- **Analysis Guide**: `RESULT_ANALYSIS_GUIDE.md`
- **Quick Start**: `ATTACK_EXPERIMENT_QUICKSTART.md`
- **Viewing Results**: `HOW_TO_VIEW_RESULTS.md`
- **Quick Reference**: `ANALYSIS_QUICK_REFERENCE.md`

---

**🎉 Enjoy watching your experiment live!**

The live visualization makes monitoring much more engaging and helps you spot issues immediately. Combined with post-hoc analysis, you get the best of both worlds! 🚀
