#!/bin/bash
# =============================================================================
# BGP-Sentry-RS — Run all datasets at hop=1 and hop=2
# =============================================================================
# Usage: bash run_all.sh          (run inside tmux)
# Estimated time: ~4-5 hours total (8 runs × ~30-40 min each)
# =============================================================================

set -e

BINARY="./target/release/bgp-sentry"
DATASETS=(
    "904_afrinic_transit_mh"
    "2030_arin_transit"
    "3152_lacnic_afrinic_transit"
    "5008_lacnic_5plus_mh"
)
HOPS=(1 2)

# Ensure binary is built
echo "Building release binary..."
cargo build --release 2>&1 | tail -3

echo ""
echo "========================================================"
echo "BGP-SENTRY-RS FULL EXPERIMENT SUITE"
echo "Datasets: ${#DATASETS[@]}"
echo "Hop configs: ${HOPS[*]}"
echo "Total runs: $(( ${#DATASETS[@]} * ${#HOPS[@]} ))"
echo "========================================================"
echo ""

SUITE_START=$(date +%s)
RUN_NUM=0
TOTAL_RUNS=$(( ${#DATASETS[@]} * ${#HOPS[@]} ))

for HOP in "${HOPS[@]}"; do
    for DATASET in "${DATASETS[@]}"; do
        RUN_NUM=$((RUN_NUM + 1))
        echo "========================================================"
        echo "[$RUN_NUM/$TOTAL_RUNS] Dataset: $DATASET | Hops: $HOP"
        echo "Started: $(date)"
        echo "========================================================"

        RUN_START=$(date +%s)

        # Set MAX_OBSERVATION_RECORDING_HOPS via environment variable
        # (env vars override .env file values in Config::load)
        MAX_OBSERVATION_RECORDING_HOPS=$HOP \
            $BINARY --dataset "$DATASET" 2>&1 | tee "/tmp/bgp_sentry_${DATASET}_hop${HOP}.log"

        RUN_END=$(date +%s)
        RUN_ELAPSED=$((RUN_END - RUN_START))
        echo ""
        echo "[$RUN_NUM/$TOTAL_RUNS] Completed in ${RUN_ELAPSED}s ($(( RUN_ELAPSED / 60 ))m $(( RUN_ELAPSED % 60 ))s)"
        echo ""
    done
done

SUITE_END=$(date +%s)
SUITE_ELAPSED=$((SUITE_END - SUITE_START))

echo "========================================================"
echo "ALL RUNS COMPLETED"
echo "Total time: ${SUITE_ELAPSED}s ($(( SUITE_ELAPSED / 60 ))m $(( SUITE_ELAPSED % 60 ))s)"
echo "========================================================"

# Print summary of results
echo ""
echo "Results directories:"
for HOP in "${HOPS[@]}"; do
    for DATASET in "${DATASETS[@]}"; do
        LATEST=$(ls -td results/$DATASET/*/ 2>/dev/null | head -1)
        if [ -n "$LATEST" ]; then
            echo "  $DATASET (hop=$HOP): $LATEST"
        fi
    done
done
