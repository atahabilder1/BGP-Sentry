# /home/anik/code/BGP_Announcement_Recorder/tests/01_staking/test_staking_mechanism.py

import subprocess
import os

def deduct_stake_js(address, amount):
    env = os.environ.copy()
    env["ADDRESS"] = address
    env["AMOUNT"] = str(amount)

    try:
        result = subprocess.run(
            ["npx", "hardhat", "run", "scripts/check_deduction.js", "--network", "localhost"],
            cwd="/home/anik/code/BGP_Announcement_Recorder/smart_contract",
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("❌ JS script failed:")
        print(e.stderr)

# Example usage
if __name__ == "__main__":
    target_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    amount_eth = 0.5
    deduct_stake_js(target_address, amount_eth)
