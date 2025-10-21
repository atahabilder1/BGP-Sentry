# 🎨 Standalone Live Viewer - Quick Guide

## 🚀 Quick Start

### Run in Two Terminals

**Terminal 1: Run the experiment**
```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 run_attack_experiment.py
```

**Terminal 2: Watch live ratings**
```bash
cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
python3 watch_ratings_live.py
```

**That's it!** The live viewer will automatically open a plot window showing real-time updates.

---

## 📊 What You'll See

The viewer opens a matplotlib window with:

- **8 rating plots** - Real-time rating evolution for each non-RPKI AS
- **Color-coded zones** - RED (0-40), YELLOW (41-70), GREEN (71-100)
- **Attack markers** - Red stars (★) when attacks detected
- **TPS graph** - Live blockchain performance
- **Detection metrics** - Real-time detection rate

**Updates every 10 seconds automatically!**

---

## 🎮 Usage Options

### Basic Usage (Auto-detect ASes)
```bash
python3 watch_ratings_live.py
```

### Custom Refresh Rate
```bash
# Update every 5 seconds
python3 watch_ratings_live.py --refresh 5

# Update every 20 seconds
python3 watch_ratings_live.py --refresh 20
```

### Monitor Specific ASes
```bash
# Only watch AS666 and AS31337
python3 watch_ratings_live.py --ases 666 31337

# Watch specific ASes with custom refresh
python3 watch_ratings_live.py --ases 666 31337 100 200 --refresh 5
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--refresh SECONDS` | How often to update (seconds) | 10 |
| `--ases AS1 AS2 ...` | Specific ASes to monitor | Auto-detect |

---

## 💡 Tips

### 1. Start Viewer Before or After Experiment

**Option A: Start viewer first**
```bash
# Terminal 2: Start viewer (will wait for ratings)
python3 watch_ratings_live.py

# Terminal 1: Then start experiment
python3 run_attack_experiment.py
```

**Option B: Start experiment first**
```bash
# Terminal 1: Start experiment
python3 run_attack_experiment.py

# Terminal 2: Start viewer anytime during experiment
python3 watch_ratings_live.py
```

Both work! The viewer waits for rating files to appear.

### 2. Multiple Viewers

You can run multiple viewers with different settings:

```bash
# Terminal 2: Watch all ASes
python3 watch_ratings_live.py

# Terminal 3: Watch only attackers with fast refresh
python3 watch_ratings_live.py --ases 666 31337 --refresh 5
```

### 3. Screenshot While Running

- Resize the plot window as needed
- Use your screenshot tool (gnome-screenshot, flameshot, etc.)
- Or click the matplotlib save icon (💾)

### 4. Close Anytime

- Close the plot window to exit
- Or press Ctrl+C in the terminal
- The experiment continues in Terminal 1

---

## 🎯 What to Watch For

### Attackers (AS666, AS31337)

✅ **Expected behavior:**
- Lines trending **downward** over time
- Moving into **RED zone** (0-40)
- **Red stars appearing** as attacks detected
- Attack count increasing

❌ **Issues to investigate:**
- Lines staying flat (no detections)
- Staying in GREEN zone (detection not working)
- No red stars (attacks not being flagged)

### Legitimate ASes

✅ **Expected behavior:**
- Lines **stable or increasing**
- Staying in **GREEN/YELLOW zones**
- Few or no red stars
- Low attack count (0-2)

❌ **Issues to investigate:**
- Lines dropping significantly (false positives)
- Moving into RED zone (legitimate AS flagged)
- Many red stars (too many false alarms)

### Blockchain Performance

✅ **Expected:**
- TPS **> 1.0** (basic functionality)
- TPS **> 10** (good performance)
- Steady or increasing graph

❌ **Issues:**
- TPS = 0 (blockchain not processing)
- TPS < 0.5 (very low performance)
- Decreasing trend (performance degrading)

### Detection Rate

✅ **Expected:**
- Increasing over time
- Reaching **95-100%** by end
- Green status box

❌ **Issues:**
- Stuck at 0% (no detections)
- Low rate < 50% (many missed attacks)
- Red status box

---

## 📋 Example Session

**Complete workflow:**

1. **Start experiment** (Terminal 1)
   ```bash
   cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
   python3 run_attack_experiment.py
   ```

2. **Start live viewer** (Terminal 2)
   ```bash
   cd /home/anik/code/BGP-Sentry/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils
   python3 watch_ratings_live.py
   ```

3. **Watch the experiment**
   - See attackers' ratings drop
   - Monitor TPS performance
   - Watch detection rate increase

4. **Take screenshots** (optional)
   - Capture interesting moments
   - Save for documentation

5. **Let it run**
   - Experiment runs for 5 minutes
   - Viewer updates every 10 seconds
   - Close viewer when done (or keep watching)

6. **Analyze results** (Terminal 1 or 3)
   ```bash
   python3 analyze_experiment.py
   ```

---

## 🔧 Troubleshooting

### "Waiting for ratings..."

**Cause:** Rating file doesn't exist yet

**Solutions:**
- Wait for experiment to start detecting attacks
- Check experiment is running in Terminal 1
- Ratings appear after first attack detected

### Window doesn't open

**Cause:** No display or matplotlib issue

**Solutions:**
```bash
# Set display
export DISPLAY=:0

# Try different backend
export MPLBACKEND=TkAgg

# Run again
python3 watch_ratings_live.py
```

### No ASes detected

**Cause:** No ratings in file yet

**Solution:**
- Wait a bit longer (until first attack detected)
- Or specify ASes manually:
  ```bash
  python3 watch_ratings_live.py --ases 666 31337
  ```

### Plot not updating

**Cause:** Various matplotlib issues

**Solution:**
- Check refresh rate (increase if too fast)
- Try different refresh interval:
  ```bash
  python3 watch_ratings_live.py --refresh 20
  ```

---

## 🎓 Comparison: Standalone vs Integrated

| Feature | Standalone Viewer | Integrated (Old) |
|---------|------------------|------------------|
| **Run separately** | ✅ Yes | ❌ No |
| **Start/stop anytime** | ✅ Yes | ❌ Only with experiment |
| **Multiple viewers** | ✅ Yes | ❌ One only |
| **Custom refresh** | ✅ Yes (--refresh) | ❌ Fixed at 10s |
| **Select ASes** | ✅ Yes (--ases) | ❌ Auto only |
| **No experiment impact** | ✅ Independent | ⚠️ Slight overhead |

**Recommendation:** Use the **standalone viewer** - it's more flexible!

---

## 📚 Related Commands

```bash
# Run experiment
python3 run_attack_experiment.py

# Watch live ratings (basic)
python3 watch_ratings_live.py

# Watch with fast refresh
python3 watch_ratings_live.py --refresh 5

# Watch specific ASes
python3 watch_ratings_live.py --ases 666 31337 100 200

# Analyze results
python3 analyze_experiment.py

# View results interactively
python3 view_rating_results.py
```

---

## ✅ Summary

**The standalone live viewer:**

✅ Runs independently in a separate terminal
✅ Updates automatically every 10 seconds (customizable)
✅ Auto-detects ASes or monitors specific ones
✅ Shows real-time rating changes, TPS, and detection rate
✅ Can be started/stopped anytime without affecting experiment
✅ Supports multiple viewers running simultaneously
✅ Zero impact on experiment performance

**Perfect for:**
- Watching experiments in real-time
- Monitoring system health
- Taking screenshots during runs
- Quick visual feedback
- Debugging and validation

---

## 🚀 Get Started Now!

**Terminal 1:**
```bash
python3 run_attack_experiment.py
```

**Terminal 2:**
```bash
python3 watch_ratings_live.py
```

**Enjoy watching your experiment live!** 🎨📊
