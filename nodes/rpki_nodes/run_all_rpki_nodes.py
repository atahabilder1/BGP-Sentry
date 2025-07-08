# --------------------------------------------------------------
# File: run_all_rpki_nodes.py
# Purpose: Launch all RPKI node scripts in parallel
# Used By:
#   - project root or directly inside rpki_nodes/ folder
# Calls:
#   - rpki_65001.py, rpki_65003.py, rpki_65005.py
# Notes:
#   - Ensure you're in the project virtual environment before running
# --------------------------------------------------------------

import subprocess
import os

# List of RPKI node scripts to launch
rpki_scripts = [
    "rpki_65001.py",
    "rpki_65003.py",
    "rpki_65005.py"
]

# Get the full path to the current script's directory
base_dir = os.path.dirname(os.path.abspath(__file__))

processes = []

print("🚀 Launching RPKI nodes...")

for script in rpki_scripts:
    script_path = os.path.join(base_dir, script)
    try:
        proc = subprocess.Popen(["python", script_path])
        processes.append(proc)
        print(f"✅ Started: {script}")
    except Exception as e:
        print(f"❌ Failed to start {script}: {e}")

print("🎯 All RPKI nodes are now running in background.")
