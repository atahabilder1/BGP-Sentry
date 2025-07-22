# --------------------------------------------------------------
# File: run_all_rpki_nodes.py
# Purpose: Auto-discover and launch all RPKI node scripts in parallel
# --------------------------------------------------------------

import subprocess
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
processes = []
scripts_to_run = []

print("🚀 Scanning for RPKI node folders and discovering node scripts...\n")

# Step 1: Discover all matching scripts
for folder in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder)

    if os.path.isdir(folder_path) and folder.startswith("as"):
        for file in os.listdir(folder_path):
            if file.endswith(".py") and file.startswith("rpki"):
                script_path = os.path.join(folder_path, file)
                scripts_to_run.append((file, folder, script_path))

# Step 2: Print summary of scripts found
if scripts_to_run:
    print("🧾 Summary of scripts to launch:")
    for file, folder, _ in scripts_to_run:
        print(f"  - {file} (in folder {folder})")
else:
    print("⚠️ No RPKI node scripts found. Exiting.")
    exit(0)

print("\n🔧 Starting all discovered RPKI node scripts...\n")

# Step 3: Launch scripts in parallel
for file, folder, script_path in scripts_to_run:
    try:
        proc = subprocess.Popen(["python", script_path])
        processes.append(proc)
        print(f"✅ Started: {file} from {folder}")
    except Exception as e:
        print(f"❌ Failed to start {file} from {folder}: {e}")

print("\n🎯 All RPKI node scripts are now running in background.")
