#!/bin/bash
# =============================================================================
# 05_ablation_discovery.sh — Peer-discovery depth ablation on caida_200
# =============================================================================
# Varies the peer-discovery strategy used when selecting voters for a
# transaction. Default is 1-hop (topology-aware). The paper also reports
# 0-hop (random) and 2-hop/3-hop (broader topology-aware) variants.
#
# NOTE — LIMITATION:
#   Peer-discovery depth is NOT currently exposed via .env. The default
#   1-hop logic lives in
#       nodes/rpki_nodes/shared_blockchain_stack/network_stack/
#       relevant_neighbor_cache.py
#   Running this ablation end-to-end requires either:
#     (a) adding a PEER_DISCOVERY_DEPTH env var to config.py and plumbing
#         it through relevant_neighbor_cache.py, or
#     (b) branching and running separately against modified code.
#
# This script is a SCAFFOLD. It records what was intended and falls
# through to the default (1-hop) baseline for now.
#
# Output:   results/ablation/discovery/depth_<N>/
# Consumed by: tab_discovery_depth.py
# =============================================================================

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

OUT_BASE="$PROJECT_ROOT/results/ablation/discovery"
mkdir -p "$OUT_BASE"

if [ $# -ge 1 ]; then
    DEPTH_VALUES=("$@")
else
    DEPTH_VALUES=(0 1 2 3)
fi

log "==================================================="
log "05_ablation_discovery.sh — depths: ${DEPTH_VALUES[*]}"
log "WARNING: PEER_DISCOVERY_DEPTH is not yet plumbed through config."
log "         Runs will execute at the hard-coded 1-hop default."
log "         See script header for the limitation."
log "==================================================="

for D in "${DEPTH_VALUES[@]}"; do
    swap_env 200
    override_env PEER_DISCOVERY_DEPTH "$D"   # ignored for now; written for future use
    run_experiment "caida_200" "$OUT_BASE/depth_$D"
done

log "05_ablation_discovery.sh DONE. Results in $OUT_BASE"
log "NOTE: All runs used the 1-hop default. See script header."
