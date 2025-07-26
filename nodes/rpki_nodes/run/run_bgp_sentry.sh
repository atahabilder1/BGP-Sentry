#!/bin/bash

echo "🚀 Starting BGP-Sentry Simulation"

echo "✅ [1/5] Setting up virtual environment"
source venv/bin/activate

echo "✅ [2/5] Deploying smart contract (Blockchain B)"
cd smart_contract
python scripts/deploy_and_test.py
cd ..

echo "✅ [3/5] Generating BGP feed logs"
python bgp_feed/mininet_logs/simulator.py

echo "✅ [4/5] Running all RPKI nodes"
python run_all_rpki_nodes.py

echo "✅ [5/5] Launching Trust Engine"
python nodes/rpki_nodes/shared_blockchain_stack/utils/trust_engine/main.py

echo "🎉 BGP-Sentry system launched successfully"
