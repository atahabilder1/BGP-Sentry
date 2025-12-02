#!/bin/bash
# BGP-Sentry Experiment Cleanup Script
# Cleans blockchain data, state files, and results between experiments

echo "🧹 Cleaning BGP-Sentry Experiment Data..."
echo ""

# 1. Clean blockchain data
echo "[1/5] Removing blockchain files..."
find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/chain/ -type f -name "*.json" -delete 2>/dev/null
count1=$(find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/chain/ -type f 2>/dev/null | wc -l)
echo "      Cleaned blockchain files (${count1} remaining)"

# 2. Clean state directories
echo "[2/5] Removing state files..."
find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/state/ -type f -name "*.json" -delete 2>/dev/null
count2=$(find nodes/rpki_nodes/as*/blockchain_node/blockchain_data/state/ -type f 2>/dev/null | wc -l)
echo "      Cleaned state files (${count2} remaining)"

# 3. Clean experiment results
echo "[3/5] Removing old results..."
rm -rf test_experiment_results/ 2>/dev/null
rm -f experiment_test_run.log experiment_pid.txt 2>/dev/null
echo "      Cleaned experiment results"

# 4. Clean backup directories
echo "[4/5] Removing backups..."
rm -rf backup_blockchain_* 2>/dev/null
backup_count=$(ls -d backup_blockchain_* 2>/dev/null | wc -l)
echo "      Cleaned backup directories (${backup_count} remaining)"

# 5. Clean analysis outputs
echo "[5/5] Removing analysis outputs..."
rm -rf analysis/__pycache__/ 2>/dev/null
echo "      Cleaned analysis cache"

echo ""
echo "✅ Cleanup complete! Ready for new experiment."
echo ""
echo "Next steps:"
echo "  1. (Optional) Edit duration: nano simulation_helpers/shared_data/experiment_config.json"
echo "  2. Run experiment: python3 main_experiment.py"
echo "  3. Analyze results: python3 analysis/targeted_attack_analyzer.py test_experiment_results/"
