#!/bin/bash
# =============================================================================
# 02_ablation_tau.sh — Consensus threshold (τ) ablation on caida_200
# =============================================================================
# Varies CONSENSUS_MIN_SIGNATURES (the PoP threshold) while holding every
# other parameter at the caida_200 defaults.
#
# Output:   results/ablation/tau/tau_<N>/
# Consumed by: fig_consensus_ablation.py (panel c)
# =============================================================================

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

OUT_BASE="$PROJECT_ROOT/results/ablation/tau"
mkdir -p "$OUT_BASE"

# τ values explored (must include the default 3 so the primary run is the baseline)
if [ $# -ge 1 ]; then
    TAU_VALUES=("$@")
else
    TAU_VALUES=(1 2 3 5 7)
fi

log "==================================================="
log "02_ablation_tau.sh — τ values: ${TAU_VALUES[*]}"
log "==================================================="

for TAU in "${TAU_VALUES[@]}"; do
    swap_env 200
    override_env CONSENSUS_MIN_SIGNATURES "$TAU"
    # Keep the cap >= min so PoP math is consistent
    override_env CONSENSUS_CAP_SIGNATURES "$TAU"
    run_experiment "caida_200" "$OUT_BASE/tau_$TAU"
done

log "02_ablation_tau.sh DONE. Results in $OUT_BASE"
