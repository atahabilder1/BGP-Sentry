#!/bin/bash
# =============================================================================
# run_all.sh — Master orchestrator for all paper experiments
# =============================================================================
# Runs every experiment in dependency order. Individual driver scripts are
# idempotent (they skip completed runs via .done marker files), so this
# script is safe to re-run after a crash or partial completion.
#
# Usage:
#   ./run_all.sh                  # run everything
#   ./run_all.sh --primary-only   # only the 5 primary scalability runs
#   ./run_all.sh --ablation-only  # only the ablation runs (needs primary to exist)
#   ./run_all.sh --render-only    # only re-render figures/tables from existing results
# =============================================================================

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

MODE="${1:-all}"

run_primary() {
    log "=== STAGE 1: Primary scalability (5 datasets) ==="
    "$SCRIPT_DIR/01_scalability.sh"
}

run_ablations() {
    log "=== STAGE 2: Ablation studies (caida_200 base) ==="
    "$SCRIPT_DIR/02_ablation_tau.sh"
    "$SCRIPT_DIR/03_ablation_timeout.sh"
    "$SCRIPT_DIR/04_ablation_broadcast.sh"
    "$SCRIPT_DIR/05_ablation_discovery.sh"
}

render_figures() {
    log "=== STAGE 3: Render all figures and tables ==="
    local pyscript="$PROJECT_ROOT/analysis/paper_figures/make_all.py"
    if [ -f "$pyscript" ]; then
        (cd "$PROJECT_ROOT" && python3 "$pyscript")
    else
        log "WARNING: $pyscript not found — skipping render stage"
    fi
}

case "$MODE" in
    all)
        run_primary
        run_ablations
        render_figures
        ;;
    --primary-only)
        run_primary
        render_figures
        ;;
    --ablation-only)
        run_ablations
        render_figures
        ;;
    --render-only)
        render_figures
        ;;
    *)
        log "Unknown mode: $MODE"
        log "Usage: $0 [all|--primary-only|--ablation-only|--render-only]"
        exit 1
        ;;
esac

log "==================================================="
log "run_all.sh DONE — mode=$MODE"
log "Figures: $PROJECT_ROOT/results/figures/"
log "Tables:  $PROJECT_ROOT/results/tables/"
log "==================================================="
