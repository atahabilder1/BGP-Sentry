#!/bin/bash
# =============================================================================
# BGP-Sentry Overnight Test Suite
# =============================================================================
# Runs all experiments, benchmarks, analysis tools, and generates reports.
# Estimated runtime: 3-5 hours depending on hardware.
#
# Usage:
#   chmod +x scripts/run_overnight_tests.sh
#   nohup ./scripts/run_overnight_tests.sh > overnight_test.log 2>&1 &
#
# Or in a tmux/screen session:
#   ./scripts/run_overnight_tests.sh 2>&1 | tee overnight_test.log
# =============================================================================

# Do NOT use set -e: we want to continue on errors and report them
ERRORS=0

# Activate virtual environment
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Create overnight results directory
OVERNIGHT_DIR="results/overnight_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OVERNIGHT_DIR"

# Alarm function: plays terminal bell 5 times on error
alarm() {
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "  ERROR: $1"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    # Terminal bell (works in most terminals)
    for i in 1 2 3 4 5; do
        printf '\a'
        sleep 0.3
    done
    # Also try paplay/aplay for audible sound
    if command -v paplay &>/dev/null; then
        paplay /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga 2>/dev/null &
    elif command -v aplay &>/dev/null; then
        # Generate a beep via aplay
        python3 -c "
import struct, sys
rate=8000; dur=0.5; freq=800
samples=int(rate*dur)
import math
data=b''.join(struct.pack('<h',int(32767*math.sin(2*math.pi*freq*i/rate))) for i in range(samples))
sys.stdout.buffer.write(data)
" | aplay -f S16_LE -r 8000 -c 1 2>/dev/null &
    fi
    ERRORS=$((ERRORS + 1))
}

LOG="$OVERNIGHT_DIR/overnight_log.txt"
SUMMARY="$OVERNIGHT_DIR/OVERNIGHT_SUMMARY.md"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

# Initialize summary report
cat > "$SUMMARY" << 'HEADER'
# BGP-Sentry Overnight Test Report

HEADER
echo "**Generated:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY"
echo "" >> "$SUMMARY"

log "=========================================="
log "BGP-Sentry Overnight Test Suite"
log "=========================================="
log "Project dir: $PROJECT_DIR"
log "Results dir: $OVERNIGHT_DIR"
log ""

# =============================================================================
# PHASE 1: Full experiments on all datasets
# =============================================================================
log "PHASE 1: Running full experiments on all 4 datasets"
echo "## Phase 1: Full Experiments" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "| Dataset | Duration | Status | TPS | F1 | Blocks | Integrity |" >> "$SUMMARY"
echo "|---------|----------|--------|-----|------|--------|-----------|" >> "$SUMMARY"

for DATASET in caida_100 caida_200 caida_500 caida_1000; do
    # Duration scales with dataset size
    case $DATASET in
        caida_100)  DURATION=600 ;;
        caida_200)  DURATION=600 ;;
        caida_500)  DURATION=900 ;;
        caida_1000) DURATION=1200 ;;
    esac

    log "--- Running $DATASET (duration=${DURATION}s) ---"
    START_TIME=$(date +%s)

    if python3 main_experiment.py --dataset "$DATASET" --duration "$DURATION" >> "$LOG" 2>&1; then
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        log "$DATASET completed in ${ELAPSED}s"

        # Find the latest result directory for this dataset
        RESULT_DIR=$(ls -td results/${DATASET}/*/ 2>/dev/null | head -1)

        if [ -n "$RESULT_DIR" ] && [ -f "${RESULT_DIR}summary.json" ]; then
            # Extract key metrics from summary.json
            TPS=$(python3 -c "
import json
with open('${RESULT_DIR}summary.json') as f:
    d = json.load(f)
    tps = d.get('throughput', {}).get('network_tps', 0)
    print(f'{tps:.1f}')
" 2>/dev/null || echo "N/A")

            F1=$(python3 -c "
import json
with open('${RESULT_DIR}performance_metrics.json') as f:
    d = json.load(f)
    print(f'{d.get(\"f1_score\", 0):.4f}')
" 2>/dev/null || echo "N/A")

            BLOCKS=$(python3 -c "
import json
with open('${RESULT_DIR}blockchain_stats.json') as f:
    d = json.load(f)
    print(d.get('total_blocks', 'N/A'))
" 2>/dev/null || echo "N/A")

            INTEGRITY=$(python3 -c "
import json
with open('${RESULT_DIR}blockchain_stats.json') as f:
    d = json.load(f)
    print('Valid' if d.get('integrity_valid', False) else 'INVALID')
" 2>/dev/null || echo "N/A")

            echo "| $DATASET | ${DURATION}s | PASS (${ELAPSED}s) | $TPS | $F1 | $BLOCKS | $INTEGRITY |" >> "$SUMMARY"

            # Copy the README report
            cp "${RESULT_DIR}README.md" "$OVERNIGHT_DIR/report_${DATASET}.md" 2>/dev/null || true
        else
            echo "| $DATASET | ${DURATION}s | PASS (${ELAPSED}s) | N/A | N/A | N/A | N/A |" >> "$SUMMARY"
        fi
    else
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        log "ERROR: $DATASET failed after ${ELAPSED}s"
        echo "| $DATASET | ${DURATION}s | FAIL (${ELAPSED}s) | - | - | - | - |" >> "$SUMMARY"
        alarm "$DATASET experiment failed"
    fi

    log ""
done

echo "" >> "$SUMMARY"

# =============================================================================
# PHASE 2: Throughput benchmark (caida_100 at multiple speeds)
# =============================================================================
log "PHASE 2: Throughput benchmark (caida_100, speeds 1x-10x)"
echo "## Phase 2: Throughput Benchmark (caida_100)" >> "$SUMMARY"
echo "" >> "$SUMMARY"

START_TIME=$(date +%s)
if python3 scripts/benchmark_throughput.py --dataset caida_100 --duration 300 >> "$LOG" 2>&1; then
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    log "Benchmark completed in ${ELAPSED}s"

    # Copy benchmark results
    if [ -f "results/benchmark_caida_100.json" ]; then
        cp results/benchmark_caida_100.json "$OVERNIGHT_DIR/"

        # Extract benchmark table
        python3 -c "
import json
with open('results/benchmark_caida_100.json') as f:
    data = json.load(f)

print('| Speed | Wall Time | Network TPS | Precision | Recall | F1 |')
print('|-------|-----------|-------------|-----------|--------|------|')
for run in data.get('runs', []):
    speed = run.get('speed', 'N/A')
    wall = run.get('wall_time', 0)
    tps = run.get('network_tps', 0)
    prec = run.get('precision', 0)
    rec = run.get('recall', 0)
    f1 = run.get('f1', 0)
    print(f'| {speed}x | {wall:.0f}s | {tps:.1f} | {prec:.3f} | {rec:.3f} | {f1:.3f} |')
" >> "$SUMMARY" 2>/dev/null || echo "Benchmark results could not be parsed." >> "$SUMMARY"
    fi
    echo "" >> "$SUMMARY"
else
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    log "ERROR: Benchmark failed after ${ELAPSED}s"
    echo "Benchmark failed after ${ELAPSED}s" >> "$SUMMARY"
    alarm "Throughput benchmark failed"
    echo "" >> "$SUMMARY"
fi

log ""

# =============================================================================
# PHASE 3: Blockchain explorer verification on all results
# =============================================================================
log "PHASE 3: Blockchain integrity verification via explorer"
echo "## Phase 3: Blockchain Integrity Verification" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "| Dataset | Blocks | Hash Chain | Merkle Roots | Status |" >> "$SUMMARY"
echo "|---------|--------|------------|--------------|--------|" >> "$SUMMARY"

for DATASET in caida_100 caida_200 caida_500 caida_1000; do
    RESULT_DIR=$(ls -td results/${DATASET}/*/ 2>/dev/null | head -1)
    BLOCKCHAIN_FILE="${RESULT_DIR}blockchain.json"

    if [ -f "$BLOCKCHAIN_FILE" ]; then
        log "Verifying blockchain for $DATASET..."
        VERIFY_OUTPUT=$(python3 analysis/blockchain_explorer.py "$BLOCKCHAIN_FILE" --verify 2>&1) || true

        # Parse verification output
        BLOCK_COUNT=$(echo "$VERIFY_OUTPUT" | grep -oP 'Total blocks: \K[0-9]+' || echo "N/A")
        HASH_OK=$(echo "$VERIFY_OUTPUT" | grep -c "Hash chain: VALID" || echo "0")
        MERKLE_OK=$(echo "$VERIFY_OUTPUT" | grep -c "Merkle roots: VALID" || echo "0")

        if [ "$HASH_OK" -gt 0 ] && [ "$MERKLE_OK" -gt 0 ]; then
            STATUS="PASS"
        else
            STATUS="FAIL"
        fi

        echo "| $DATASET | $BLOCK_COUNT | $([ "$HASH_OK" -gt 0 ] && echo 'VALID' || echo 'INVALID') | $([ "$MERKLE_OK" -gt 0 ] && echo 'VALID' || echo 'INVALID') | $STATUS |" >> "$SUMMARY"

        # Save full verification output
        echo "$VERIFY_OUTPUT" > "$OVERNIGHT_DIR/verify_${DATASET}.txt"
    else
        echo "| $DATASET | - | - | - | NO DATA |" >> "$SUMMARY"
    fi
done

echo "" >> "$SUMMARY"
log ""

# =============================================================================
# PHASE 4: Blockchain explorer - search for attack verdicts
# =============================================================================
log "PHASE 4: Attack verdict analysis via explorer"
echo "## Phase 4: Attack Verdicts" >> "$SUMMARY"
echo "" >> "$SUMMARY"

for DATASET in caida_100 caida_200 caida_500 caida_1000; do
    RESULT_DIR=$(ls -td results/${DATASET}/*/ 2>/dev/null | head -1)
    BLOCKCHAIN_FILE="${RESULT_DIR}blockchain.json"

    if [ -f "$BLOCKCHAIN_FILE" ]; then
        log "Checking verdicts for $DATASET..."
        VERDICT_OUTPUT=$(python3 analysis/blockchain_explorer.py "$BLOCKCHAIN_FILE" --verdicts 2>&1) || true
        echo "### $DATASET" >> "$SUMMARY"
        echo '```' >> "$SUMMARY"
        echo "$VERDICT_OUTPUT" >> "$SUMMARY"
        echo '```' >> "$SUMMARY"
        echo "" >> "$SUMMARY"
    fi
done

log ""

# =============================================================================
# PHASE 5: Block type distribution
# =============================================================================
log "PHASE 5: Block type distribution"
echo "## Phase 5: Block Type Distribution" >> "$SUMMARY"
echo "" >> "$SUMMARY"

for DATASET in caida_100 caida_200 caida_500 caida_1000; do
    RESULT_DIR=$(ls -td results/${DATASET}/*/ 2>/dev/null | head -1)
    BLOCKCHAIN_FILE="${RESULT_DIR}blockchain.json"

    if [ -f "$BLOCKCHAIN_FILE" ]; then
        TYPES_OUTPUT=$(python3 analysis/blockchain_explorer.py "$BLOCKCHAIN_FILE" --types 2>&1) || true
        echo "### $DATASET" >> "$SUMMARY"
        echo '```' >> "$SUMMARY"
        echo "$TYPES_OUTPUT" >> "$SUMMARY"
        echo '```' >> "$SUMMARY"
        echo "" >> "$SUMMARY"
    fi
done

log ""

# =============================================================================
# PHASE 6: Post-hoc analysis on all results
# =============================================================================
log "PHASE 6: Post-hoc analysis"
echo "## Phase 6: Post-Hoc Analysis" >> "$SUMMARY"
echo "" >> "$SUMMARY"

for DATASET in caida_100 caida_200 caida_500 caida_1000; do
    RESULT_DIR=$(ls -td results/${DATASET}/*/ 2>/dev/null | head -1)

    if [ -n "$RESULT_DIR" ]; then
        log "Running posthoc analysis for $DATASET..."

        # Posthoc analysis
        if python3 analysis/posthoc_analysis.py "$RESULT_DIR" > "$OVERNIGHT_DIR/posthoc_${DATASET}.txt" 2>&1; then
            log "  posthoc_analysis.py: OK"
        else
            log "  posthoc_analysis.py: FAILED"
        fi

        # Blockchain forensics
        if python3 analysis/blockchain_forensics.py "$RESULT_DIR" > "$OVERNIGHT_DIR/forensics_${DATASET}.txt" 2>&1; then
            log "  blockchain_forensics.py: OK"
        else
            log "  blockchain_forensics.py: FAILED"
        fi

        # Targeted attack analyzer
        if python3 analysis/targeted_attack_analyzer.py "$RESULT_DIR" > "$OVERNIGHT_DIR/targeted_${DATASET}.txt" 2>&1; then
            log "  targeted_attack_analyzer.py: OK"
        else
            log "  targeted_attack_analyzer.py: FAILED"
        fi

        echo "### $DATASET" >> "$SUMMARY"
        echo "- posthoc_analysis: see posthoc_${DATASET}.txt" >> "$SUMMARY"
        echo "- blockchain_forensics: see forensics_${DATASET}.txt" >> "$SUMMARY"
        echo "- targeted_attack_analyzer: see targeted_${DATASET}.txt" >> "$SUMMARY"
        echo "" >> "$SUMMARY"
    fi
done

log ""

# =============================================================================
# PHASE 7: Generate plots
# =============================================================================
log "PHASE 7: Generating throughput plots"
echo "## Phase 7: Plots" >> "$SUMMARY"
echo "" >> "$SUMMARY"

if python3 scripts/plot_throughput.py >> "$LOG" 2>&1; then
    log "Plots generated successfully"
    # Copy plots to overnight dir
    for PLOT in results/fig_*.png; do
        if [ -f "$PLOT" ]; then
            cp "$PLOT" "$OVERNIGHT_DIR/" 2>/dev/null || true
        fi
    done
    echo "Plots generated. See fig_*.png files in this directory." >> "$SUMMARY"
else
    log "Plot generation failed (may need benchmark data first)"
    echo "Plot generation failed." >> "$SUMMARY"
fi

echo "" >> "$SUMMARY"

# =============================================================================
# PHASE 8: Quick syntax verification of all Python modules
# =============================================================================
log "PHASE 8: Python syntax verification"
echo "## Phase 8: Python Syntax Verification" >> "$SUMMARY"
echo "" >> "$SUMMARY"

SYNTAX_ERRORS=0
cd "$PROJECT_DIR/nodes/rpki_nodes/shared_blockchain_stack/blockchain_utils"
for MODULE in config.py blockchain_interface.py p2p_transaction_pool.py attack_consensus.py nonrpki_rating.py message_bus.py rpki_node_registry.py bgpcoin_ledger.py signature_utils.py attack_detector.py; do
    if [ -f "$MODULE" ]; then
        if python3 -c "import py_compile; py_compile.compile('$MODULE', doraise=True)" 2>/dev/null; then
            true  # OK
        else
            log "SYNTAX ERROR: $MODULE"
            echo "- **FAIL**: $MODULE" >> "$PROJECT_DIR/$SUMMARY"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    fi
done
cd "$PROJECT_DIR"

if [ $SYNTAX_ERRORS -eq 0 ]; then
    echo "All modules pass syntax verification." >> "$SUMMARY"
else
    echo "$SYNTAX_ERRORS modules have syntax errors!" >> "$SUMMARY"
fi

echo "" >> "$SUMMARY"

# =============================================================================
# FINAL SUMMARY
# =============================================================================
END_TOTAL=$(date +%s)
log "=========================================="
log "OVERNIGHT TEST SUITE COMPLETE"
log "=========================================="
log "Results saved to: $OVERNIGHT_DIR"
log "Summary report: $SUMMARY"

echo "---" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "## Test Complete" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "**Finished:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "### Output Files" >> "$SUMMARY"
echo "" >> "$SUMMARY"
echo "| File | Description |" >> "$SUMMARY"
echo "|------|-------------|" >> "$SUMMARY"
echo "| OVERNIGHT_SUMMARY.md | This report |" >> "$SUMMARY"
echo "| overnight_log.txt | Full console output |" >> "$SUMMARY"
echo "| report_caida_*.md | Per-dataset experiment reports |" >> "$SUMMARY"
echo "| verify_caida_*.txt | Blockchain verification output |" >> "$SUMMARY"
echo "| posthoc_caida_*.txt | Post-hoc analysis output |" >> "$SUMMARY"
echo "| forensics_caida_*.txt | Blockchain forensics output |" >> "$SUMMARY"
echo "| targeted_caida_*.txt | Targeted attack analysis output |" >> "$SUMMARY"
echo "| benchmark_caida_100.json | Throughput benchmark raw data |" >> "$SUMMARY"
echo "| fig_*.png | Throughput plots |" >> "$SUMMARY"

echo "" >> "$SUMMARY"
if [ $ERRORS -gt 0 ]; then
    echo "**$ERRORS error(s) occurred during testing.**" >> "$SUMMARY"
fi

echo ""
echo "=========================================="
echo "OVERNIGHT TESTS COMPLETE"
echo "Results: $OVERNIGHT_DIR"
echo "Summary: $SUMMARY"
if [ $ERRORS -gt 0 ]; then
    echo "ERRORS: $ERRORS"
    alarm "Overnight tests finished with $ERRORS error(s)"
else
    echo "ALL TESTS PASSED"
fi
echo "=========================================="
