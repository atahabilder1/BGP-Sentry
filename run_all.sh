#!/bin/bash
# Run all 6 datasets sequentially — clean state between runs
# Common settings in .env.common, dataset-specific in .env.N

cd /data/anik/BGP-Sentry

# Save common env
cp .env .env.common

for N in 100 200 400 800 1600; do
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

    # Run experiment
    python3 main_experiment.py --dataset caida_$N --duration $(grep "^SIM_DURATION=" .env.$N | cut -d= -f2)

    echo "Finished caida_$N at $(date)"
    echo ""
done

# Restore common env
cp .env.common .env

echo "ALL DONE at $(date)"
