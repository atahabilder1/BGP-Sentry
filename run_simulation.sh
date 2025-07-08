#!/bin/bash

# --------------------------------------------------
# BGP TrustChain Run Script
# Purpose: Automate launching all components
# --------------------------------------------------
# Components Launched:
#   - One non-RPKI node
#   - One RPKI node
#   - Instant trust engine
#   - Periodic trust engine
#
# Notes:
#   - This script assumes the virtual environment is named 'venv'
#   - Shared data files will be auto-created if missing
#   - Processes will be stopped gracefully on Ctrl+C
# --------------------------------------------------

# Exit on any error
set -e

echo "🔧 Setting up environment..."

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run: python3 -m venv venv && source venv/bin/activate"
    exit 1
fi

# Ensure shared_data files and directory exist
mkdir -p shared_data

touch shared_data/bgp_stream.jsonl
touch shared_data/blockchain.json
touch shared_data/trust_log.jsonl
touch shared_data/trust_state.json

echo "✅ Files and environment prepared."

# Start non-RPKI node in background
echo "🚀 Starting non-RPKI node..."
python3 nodes/non_rpki_nodes/nonrpki_65010.py &
NONRPKI_PID=$!

# Start RPKI node in background
echo "🔐 Starting RPKI node..."
python3 nodes/rpki_nodes/rpki_65001.py &
RPKI_PID=$!

# Start instant trust engine in background
echo "⚖️  Starting real-time trust engine..."
python3 trust_engine/trust_engine_instant.py &
INSTANT_PID=$!

# Start periodic trust engine in background
echo "🕒 Starting periodic trust engine..."
python3 trust_engine/trust_engine_periodic.py &
PERIODIC_PID=$!

# Display and wait
echo "✅ All components started. Press Ctrl+C to stop."

# Handle Ctrl+C to stop all
trap "echo '🛑 Stopping all processes...'; kill $NONRPKI_PID $RPKI_PID $INSTANT_PID $PERIODIC_PID; exit" INT
wait
