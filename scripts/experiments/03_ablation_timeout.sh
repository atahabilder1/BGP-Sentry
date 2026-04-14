#!/bin/bash
# =============================================================================
# 03_ablation_timeout.sh — Consensus signature-collection timeout ablation
# =============================================================================
# Varies P2P_REGULAR_TIMEOUT (seconds to wait for votes before finalizing)
# on caida_200 while holding every other parameter at defaults.
#
# Output:   results/ablation/timeout/timeout_<T>/
# Consumed by: fig_consensus_ablation.py (panel d)
# =============================================================================

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

OUT_BASE="$PROJECT_ROOT/results/ablation/timeout"
mkdir -p "$OUT_BASE"

if [ $# -ge 1 ]; then
    TIMEOUT_VALUES=("$@")
else
    TIMEOUT_VALUES=(5 10 15 30 60)
fi

log "==================================================="
log "03_ablation_timeout.sh — timeouts: ${TIMEOUT_VALUES[*]} s"
log "==================================================="

for T in "${TIMEOUT_VALUES[@]}"; do
    swap_env 200
    override_env P2P_REGULAR_TIMEOUT "$T"
    # Attack timeout scales with regular timeout (kept roughly proportional)
    override_env P2P_ATTACK_TIMEOUT "$((T + 5))"
    run_experiment "caida_200" "$OUT_BASE/timeout_$T"
done

log "03_ablation_timeout.sh DONE. Results in $OUT_BASE"
