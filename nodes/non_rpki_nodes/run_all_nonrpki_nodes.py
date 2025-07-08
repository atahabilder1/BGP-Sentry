# --------------------------------------------------------------
# File: run_all_nonrpki_nodes.py
# Purpose: Launch all non-RPKI node scripts in background or foreground
# Usage:
#   - Foreground: python nodes/non_rpki_nodes/run_all_nonrpki_nodes.py
#   - Background: python nodes/non_rpki_nodes/run_all_nonrpki_nodes.py --background
# --------------------------------------------------------------

import subprocess
import time
import argparse
import os

# Define all non-RPKI node scripts to run
NON_RPKI_SCRIPTS = [
    "nonrpki_65010.py",
    "nonrpki_65012.py",
    "nonrpki_65014.py",
    "nonrpki_65016.py",
    "nonrpki_65018.py",
]

def launch_nodes(background=False):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for script in NON_RPKI_SCRIPTS:
        script_path = os.path.join(current_dir, script)
        if background:
            print(f"🚀 Launching in background: {script}")
            subprocess.Popen(["python", script_path])
        else:
            print(f"🚀 Launching in foreground: {script}")
            subprocess.call(["python", script_path])
            time.sleep(2)  # Optional delay between foreground runs

    if background:
        print("✅ All non-RPKI nodes are now running in background.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", action="store_true", help="Run all nodes in background")
    args = parser.parse_args()
    launch_nodes(background=args.background)
