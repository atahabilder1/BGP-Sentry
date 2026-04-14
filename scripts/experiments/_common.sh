#!/bin/bash
# =============================================================================
# BGP-Sentry Experiment Drivers — Shared Helpers
# =============================================================================
# Source this from every driver script. Provides:
#   - swap_env SIZE             : copy .env.SIZE → .env
#   - override_env KEY VALUE    : edit .env in-place
#   - run_experiment DATASET OUT_DIR [DURATION]
#                               : run main_experiment.py and archive results
#   - log MSG                   : timestamped log line
# =============================================================================

# Resolve the project root (parent of scripts/experiments/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

swap_env() {
    local size=$1
    local src="$PROJECT_ROOT/.env.$size"
    if [ ! -f "$src" ]; then
        log "ERROR: $src does not exist"
        return 1
    fi
    cp "$src" "$PROJECT_ROOT/.env"
    log "swap_env: loaded .env.$size"
}

override_env() {
    local key=$1
    local val=$2
    local envfile="$PROJECT_ROOT/.env"
    if grep -q "^${key}=" "$envfile"; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$envfile"
    else
        echo "${key}=${val}" >> "$envfile"
    fi
    log "override_env: set $key=$val"
}

# run_experiment DATASET OUT_DIR [DURATION_OVERRIDE]
#
# Runs main_experiment.py with the active .env, then moves the produced
# result directory and blockchain_data folder into OUT_DIR.
#
# Duration is read from the active .env file's SIM_DURATION key (the
# per-topology wall-clock cap). Pass an explicit duration as the third
# argument to override. If neither is set, defaults to 600s.
#
# Writes a .done marker file when complete so re-running skips finished work.
run_experiment() {
    local dataset=$1
    local out_dir=$2
    local duration_override=${3:-}

    # Read SIM_DURATION from active .env (line of form SIM_DURATION=NNN)
    local env_duration
    env_duration=$(grep -E "^SIM_DURATION=" "$PROJECT_ROOT/.env" 2>/dev/null \
                   | head -1 | cut -d= -f2 | tr -d '[:space:]')

    local duration
    if [ -n "$duration_override" ]; then
        duration=$duration_override
    elif [ -n "$env_duration" ]; then
        duration=$env_duration
    else
        duration=600
    fi

    # Also log the multiplier so it's visible in the run log
    local multiplier
    multiplier=$(grep -E "^SIMULATION_SPEED_MULTIPLIER=" "$PROJECT_ROOT/.env" 2>/dev/null \
                 | head -1 | cut -d= -f2 | tr -d '[:space:]')
    multiplier=${multiplier:-1.0}

    mkdir -p "$out_dir"

    if [ -f "$out_dir/.done" ]; then
        log "SKIP: $out_dir already completed"
        return 0
    fi

    log "START: dataset=$dataset out_dir=$out_dir duration=${duration}s multiplier=${multiplier}x"

    # Snapshot the active .env so the archive contains what was actually used
    cp "$PROJECT_ROOT/.env" "$out_dir/env.used"

    # Reset blockchain_data so the run starts clean
    rm -rf "$PROJECT_ROOT/blockchain_data"

    # Run the simulation, streaming output to log.txt
    local start_ts=$(date +%s)
    (
        cd "$PROJECT_ROOT" && \
        python3 main_experiment.py --dataset "$dataset" --duration "$duration"
    ) 2>&1 | tee "$out_dir/log.txt"
    local rc=${PIPESTATUS[0]}
    local end_ts=$(date +%s)

    if [ "$rc" -ne 0 ]; then
        log "ERROR: main_experiment.py exited $rc (out_dir=$out_dir)"
        return $rc
    fi

    # main_experiment.py writes to results/<dataset_name>/<timestamp>/
    # Find the newest subdirectory under results/<dataset_name>/
    local src_results_dir
    src_results_dir=$(find "$PROJECT_ROOT/results/$dataset" -mindepth 1 -maxdepth 1 -type d 2>/dev/null \
                     | sort | tail -1)
    if [ -z "$src_results_dir" ]; then
        log "ERROR: no results directory found under $PROJECT_ROOT/results/$dataset"
        return 2
    fi

    # Move the experiment output files into OUT_DIR (not nested under a timestamp)
    # We copy instead of move so the original path stays intact if something goes wrong
    cp -r "$src_results_dir"/* "$out_dir/"

    # Archive blockchain_data if produced
    if [ -d "$PROJECT_ROOT/blockchain_data" ]; then
        rm -rf "$out_dir/blockchain_data"
        mv "$PROJECT_ROOT/blockchain_data" "$out_dir/blockchain_data"
    fi

    # Write a metadata file with run provenance
    cat > "$out_dir/metadata.json" <<EOF
{
  "dataset": "$dataset",
  "out_dir": "$out_dir",
  "duration": $duration,
  "start_ts": $start_ts,
  "end_ts": $end_ts,
  "elapsed_seconds": $((end_ts - start_ts)),
  "hostname": "$(hostname)",
  "completed_at": "$(date -Iseconds)"
}
EOF

    touch "$out_dir/.done"
    log "DONE: $out_dir (elapsed $((end_ts - start_ts))s)"
}
