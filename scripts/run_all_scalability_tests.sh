#!/bin/bash
# ============================================================================
# BGP-Sentry Scalability Test Suite
# Runs 150 → 400 → 800 node experiments sequentially with real-time pacing
# Duration set to match dataset timestamp span + 300s buffer for drain
# ============================================================================

set -e

DATASET_BASE="/data/anik/BGP-Sentry/dataset/bfsTopology"
LOG_DIR="/data/anik/BGP-Sentry/results/run_logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_LOG="$LOG_DIR/scalability_suite_${TIMESTAMP}.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MASTER_LOG"
}

run_experiment() {
    local nodes=$1
    local duration=$2
    local dataset="caida_bfs_174_${nodes}"
    local dataset_path="${DATASET_BASE}/${dataset}"
    local run_log="${LOG_DIR}/${dataset}_${TIMESTAMP}.log"

    log "=========================================="
    log "STARTING: ${nodes} nodes | duration=${duration}s"
    log "Dataset: ${dataset_path}"
    log "Log: ${run_log}"
    log "=========================================="

    python3 /data/anik/BGP-Sentry/main_experiment.py \
        --dataset "$dataset_path" \
        --duration "$duration" \
        2>&1 | tee "$run_log"

    local exit_code=${PIPESTATUS[0]}

    if [ $exit_code -eq 0 ]; then
        log "COMPLETED: ${nodes} nodes (exit code 0)"
    else
        log "FAILED: ${nodes} nodes (exit code ${exit_code})"
    fi

    log ""
    return $exit_code
}

log "============================================"
log "BGP-Sentry Scalability Test Suite"
log "Start time: $(date)"
log "Speed multiplier: 1.0 (real-time)"
log "============================================"
log ""

# Dataset timestamp spans (all ~37 min ≈ 2200-2330s)
# Duration = span + 300s buffer for consensus drain

# Run 1: 150 nodes (span=2252s)
run_experiment 150 2600

# Run 2: 400 nodes (span=2330s)
run_experiment 400 2700

# Run 3: 800 nodes (span=2237s)
run_experiment 800 2600

log "============================================"
log "ALL RUNS COMPLETE"
log "End time: $(date)"
log "============================================"

# Summary of results
log ""
log "Results stored in:"
for d in 150 400 800; do
    latest=$(ls -td /data/anik/BGP-Sentry/results/caida_bfs_174_${d}/*/ 2>/dev/null | head -1)
    if [ -n "$latest" ]; then
        elapsed=$(python3 -c "import json; d=json.load(open('${latest}summary.json')); print(f\"{d['elapsed_seconds']:.0f}s\")" 2>/dev/null || echo "unknown")
        log "  ${d} nodes: ${latest} (${elapsed})"
    fi
done
