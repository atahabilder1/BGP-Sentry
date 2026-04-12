#!/usr/bin/env bash
# =============================================================================
# BGP-Sentry Sequential Scalability Runner
# =============================================================================
# Runs experiments for the 4 smallest datasets (50, 100, 150, 200 nodes)
# sequentially, swapping the per-dataset .env before each run.
#
# Usage:  ./run_scalability_suite.sh
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Activate virtualenv if present
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Backup original .env
if [ -f .env ]; then
    cp .env .env.backup
    echo "✓ Backed up original .env → .env.backup"
fi

# Dataset configs: (node_count, dataset_arg, duration)
DATASETS=(
    "50|bfsTopology/caida_bfs_174_50|300"
    "100|bfsTopology/caida_bfs_174_100|400"
    "150|bfsTopology/caida_bfs_174_150|500"
    "200|bfsTopology/caida_bfs_174_200|600"
)

TOTAL=${#DATASETS[@]}
PASSED=0
FAILED=0

echo "=============================================="
echo " BGP-Sentry Scalability Suite"
echo " Datasets: 50, 100, 150, 200 nodes"
echo " Started: $(date)"
echo "=============================================="

for i in "${!DATASETS[@]}"; do
    IFS='|' read -r NODES DATASET DURATION <<< "${DATASETS[$i]}"
    RUN_NUM=$((i + 1))
    ENV_FILE=".env.${NODES}"

    echo ""
    echo "----------------------------------------------"
    echo " [$RUN_NUM/$TOTAL] Running ${NODES}-node experiment"
    echo " Dataset: $DATASET"
    echo " Duration: ${DURATION}s"
    echo " Config:  $ENV_FILE"
    echo " Time:    $(date)"
    echo "----------------------------------------------"

    # Swap .env
    if [ ! -f "$ENV_FILE" ]; then
        echo "ERROR: $ENV_FILE not found, skipping."
        FAILED=$((FAILED + 1))
        continue
    fi
    cp "$ENV_FILE" .env
    echo "✓ Loaded $ENV_FILE → .env"

    # Run experiment
    if python3 main_experiment.py --dataset "$DATASET" --duration "$DURATION" --clean; then
        echo "✓ ${NODES}-node experiment completed successfully"
        PASSED=$((PASSED + 1))
    else
        echo "✗ ${NODES}-node experiment FAILED (exit code $?)"
        FAILED=$((FAILED + 1))
    fi
done

# Restore original .env
if [ -f .env.backup ]; then
    cp .env.backup .env
    rm .env.backup
    echo ""
    echo "✓ Restored original .env"
fi

echo ""
echo "=============================================="
echo " Suite Complete: $(date)"
echo " Passed: $PASSED / $TOTAL"
echo " Failed: $FAILED / $TOTAL"
echo "=============================================="

exit $FAILED
