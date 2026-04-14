#!/usr/bin/env python3
"""
Generate a VRP (Validated ROA Payload) JSON file from a CAIDA dataset.

Reads all observation files, extracts legitimate (prefix, origin_asn) pairs,
and produces a StayRTR-compatible JSON file.

Usage:
    python3 scripts/generate_vrp.py dataset/caida_100 stayrtr/vrp_generated.json
"""

import json
import sys
from pathlib import Path


def extract_legitimate_roas(dataset_path: str) -> list:
    """
    Extract unique legitimate (prefix, origin_asn) pairs from observation files.

    Returns list of ROA dicts in StayRTR format.
    """
    dataset_dir = Path(dataset_path)
    observations_dir = dataset_dir / "observations"

    if not observations_dir.exists():
        raise FileNotFoundError(f"Observations directory not found: {observations_dir}")

    seen = set()
    roas = []

    for obs_file in sorted(observations_dir.glob("AS*.json")):
        with open(obs_file, "r") as f:
            data = json.load(f)

        for obs in data.get("observations", []):
            if obs.get("is_attack"):
                continue

            prefix = obs.get("prefix")
            origin_asn = obs.get("origin_asn")

            if not prefix or not origin_asn:
                continue

            key = (prefix, origin_asn)
            if key in seen:
                continue
            seen.add(key)

            # Determine maxLength from prefix
            try:
                prefix_len = int(prefix.split("/")[1])
            except (IndexError, ValueError):
                prefix_len = 24

            # For IPv4, allow up to /24; for IPv6, allow up to /48
            if ":" in prefix:
                max_length = max(prefix_len, 48)
            else:
                max_length = max(prefix_len, 24)

            roas.append({
                "asn": f"AS{origin_asn}",
                "prefix": prefix,
                "maxLength": max_length,
                "ta": "bgpsentry"
            })

    return roas


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/generate_vrp.py <dataset_path> <output_json>")
        print("Example: python3 scripts/generate_vrp.py dataset/caida_100 stayrtr/vrp_generated.json")
        sys.exit(1)

    dataset_path = sys.argv[1]
    output_path = sys.argv[2]

    print(f"Extracting legitimate ROAs from {dataset_path}...")
    roas = extract_legitimate_roas(dataset_path)

    # Write StayRTR-format JSON
    vrp_data = {"roas": roas}

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(vrp_data, f, indent=2)

    print(f"Generated {len(roas)} ROA entries -> {output_path}")


if __name__ == "__main__":
    main()
