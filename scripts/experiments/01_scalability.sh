#!/bin/bash
# =============================================================================
# 01_scalability.sh — Primary scalability runs across all 5 datasets
# =============================================================================
# Runs main_experiment.py with the default consensus config (τ=3, sqrt(N)
# broadcast, 1-hop discovery) on each of the 5 nominal dataset sizes.
#
# Output: results/primary/caida_<N>/   (one directory per size)
# Consumed by: tab_system_performance.py, fig_consensus_breakdown.py,
#              fig_ecdf_error.py, fig_per_attack_metrics.py, fig_trust_recovery.py
# =============================================================================

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

OUT_BASE="$PROJECT_ROOT/results/primary"
mkdir -p "$OUT_BASE"

# Optional: run only one size by passing it as an argument, e.g.:
#   ./01_scalability.sh 100
# With no argument, runs all sizes sequentially.
if [ $# -ge 1 ]; then
    SIZES=("$@")
else
    SIZES=(100 200 350 650 1250)
fi

log "==================================================="
log "01_scalability.sh — sizes: ${SIZES[*]}"
log "==================================================="

for N in "${SIZES[@]}"; do
    swap_env "$N"
    # Duration is read from .env.$N's SIM_DURATION key (set per topology)
    run_experiment "caida_$N" "$OUT_BASE/caida_$N"
done

log "01_scalability.sh DONE. Results in $OUT_BASE"
