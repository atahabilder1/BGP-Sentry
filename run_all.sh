#!/bin/bash
# Run all 6 datasets sequentially — no interaction needed
# Cleans state between runs to prevent cross-contamination

cd /data/anik/BGP-Sentry

for N in 50 100 200 350 650 1250; do
    echo "================================================"
    echo "Starting caida_$N at $(date)"
    echo "================================================"

    # Clean state from previous run
    rm -f nodes/rpki_nodes/shared_blockchain_stack/network_stack/relevant_neighbor_cache.json
    rm -rf blockchain_data/
    echo "Cleaned stale state"

    # Setup for this dataset
    cp .env.$N .env
    python3 scripts/build_as_relationships.py dataset/caida_$N

    # Run experiment
    python3 main_experiment.py --dataset caida_$N --duration $(grep "^SIM_DURATION=" .env.$N | cut -d= -f2)

    echo "Finished caida_$N at $(date)"
    echo ""
done

echo "ALL DONE at $(date)"
