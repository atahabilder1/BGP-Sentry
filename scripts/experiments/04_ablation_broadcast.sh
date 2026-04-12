#!/bin/bash
# =============================================================================
# 04_ablation_broadcast.sh — P2P broadcast-size ablation on caida_200
# =============================================================================
# Varies P2P_MAX_BROADCAST_PEERS (how many peers each vote request hits)
# on caida_200 to validate the sqrt(N) adaptive-broadcast design.
#
# N=200 → sqrt(N) ≈ 14, so the sweep brackets the default on both sides.
#
# Output:   results/ablation/broadcast/broadcast_<K>/
# Consumed by: fig_consensus_ablation.py (panel b)
# =============================================================================

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

OUT_BASE="$PROJECT_ROOT/results/ablation/broadcast"
mkdir -p "$OUT_BASE"

# Default caida_200 broadcast size is 8. The sweep explores a range from
# "threshold*2" up to "all peers" (as in the paper's ablation figure caption).
if [ $# -ge 1 ]; then
    BROADCAST_VALUES=("$@")
else
    BROADCAST_VALUES=(4 8 14 28 126)
fi

log "==================================================="
log "04_ablation_broadcast.sh — peer counts: ${BROADCAST_VALUES[*]}"
log "==================================================="

for K in "${BROADCAST_VALUES[@]}"; do
    swap_env 200
    override_env P2P_MAX_BROADCAST_PEERS "$K"
    run_experiment "caida_200" "$OUT_BASE/broadcast_$K"
done

log "04_ablation_broadcast.sh DONE. Results in $OUT_BASE"
