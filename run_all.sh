#!/bin/bash
# Run all 6 datasets sequentially — clean state between runs
# Common settings in .env.common, dataset-specific in .env.N
#
# Runtime note:
#   - main_experiment.py runs under PyPy 7.3.17 (Python 3.10) for a CPU boost
#     at large scale (caida_800 / caida_1600). Small scales see negligible
#     change because they are BGP-replay-bound, not CPU-bound.
#   - Setup scripts (build_as_relationships, build_observer_map) stay on
#     CPython — they are short one-shots and PyPy JIT has no time to warm up.
#
# Failure behavior: stop on first error (set -e + pipefail). Remaining
# datasets will NOT run so the operator can inspect the failure.

set -euo pipefail

cd /data/anik/BGP-Sentry

PYPY=/data/anik/BGP-Sentry/.pypy/pypy3.10-v7.3.17-linux64/bin/pypy3
if [ ! -x "$PYPY" ]; then
    echo "ERROR: PyPy not found at $PYPY"
    echo "Install it with: see project setup notes"
    exit 1
fi

# Save common env
cp .env .env.common

for N in 50 100 200 400 800 1600; do
    echo "================================================"
    echo "Starting caida_$N at $(date)"
    echo "================================================"

    # Clean state from previous run
    rm -f nodes/rpki_nodes/shared_blockchain_stack/network_stack/relevant_neighbor_cache.json
    rm -rf blockchain_data/
    echo "Cleaned stale state"

    # Setup: common + dataset-specific overrides
    cp .env.common .env
    cat .env.$N >> .env
    python3 scripts/build_as_relationships.py dataset/caida_$N
    python3 scripts/build_observer_map.py dataset/caida_$N

    # Run experiment under PyPy. set -e aborts the whole script if this fails.
    if ! "$PYPY" main_experiment.py --dataset caida_$N \
            --duration $(grep "^SIM_DURATION=" .env.$N | cut -d= -f2); then
        echo "❌ caida_$N FAILED at $(date) — stopping. Remaining datasets skipped."
        exit 1
    fi

    echo "✅ Finished caida_$N at $(date)"
    echo ""
done

# Restore common env
cp .env.common .env

echo "ALL DONE at $(date)"
