#!/bin/bash
# Quick script to open the rating dashboard and visualizations

echo "🖼️  Opening Rating Visualizations..."

# Find the latest experiment directory
RESULTS_DIR="/home/anik/code/BGP-Sentry/experiment_results"

if [ ! -d "$RESULTS_DIR" ]; then
    echo "❌ No experiment results found!"
    echo "Run the experiment first: python3 run_attack_experiment.py"
    exit 1
fi

# Get the most recent experiment directory
LATEST_EXP=$(ls -dt "$RESULTS_DIR"/attack_experiment_* 2>/dev/null | head -1)

if [ -z "$LATEST_EXP" ]; then
    echo "❌ No experiment directories found!"
    exit 1
fi

echo "📁 Latest Experiment: $(basename "$LATEST_EXP")"
echo ""

# Check which files exist
DASHBOARD="$LATEST_EXP/rating_dashboard.png"
TABLE="$LATEST_EXP/rating_summary_table.png"
PIE="$LATEST_EXP/classification_distribution.png"

# Open dashboard with default image viewer
if [ -f "$DASHBOARD" ]; then
    echo "✅ Opening: rating_dashboard.png"
    xdg-open "$DASHBOARD" 2>/dev/null || eog "$DASHBOARD" 2>/dev/null || echo "Please open manually: $DASHBOARD"
else
    echo "❌ Dashboard not found: $DASHBOARD"
fi

# Wait a bit
sleep 1

# Open summary table
if [ -f "$TABLE" ]; then
    echo "✅ Opening: rating_summary_table.png"
    xdg-open "$TABLE" 2>/dev/null || eog "$TABLE" 2>/dev/null
else
    echo "❌ Table not found: $TABLE"
fi

# Wait a bit
sleep 1

# Open pie chart
if [ -f "$PIE" ]; then
    echo "✅ Opening: classification_distribution.png"
    xdg-open "$PIE" 2>/dev/null || eog "$PIE" 2>/dev/null
else
    echo "❌ Pie chart not found: $PIE"
fi

echo ""
echo "🎨 Visualizations opened in image viewer!"
echo "📁 All files are in: $LATEST_EXP"
