# BGP-Sentry Experiment Report

**Dataset:** `caida_650` | **Date:** 2026-04-13T05:43:04 | **Duration:** 688.1s | **Speed:** 1.0x

## Executive Summary

| Metric | Result | Status |
|--------|--------|--------|
| Detection F1 Score | 0.2692 | LOW |
| Precision | 1.0000 | PASS |
| Recall | 0.1556 | MISSED 38 attacks |
| Network TPS (all nodes combined) | 5.9 | GOOD |
| Consensus Commit Rate | 8.5% | LOW -- increase timeout or reduce threshold |
| Blockchain Integrity | Valid | PASS |
| Message Delivery | 100.0% | PASS |
| Nodes Completed | 0/645 | INCOMPLETE -- increase duration |

## Configuration Used

These are the `.env` parameters that were active for this run. Change these in `.env` and re-run to tune results.

### Consensus & P2P

| Parameter | Value | Description |
|-----------|-------|-------------|
| `CONSENSUS_MIN_SIGNATURES` | 2 | Min votes to commit a block |
| `CONSENSUS_CAP_SIGNATURES` | 2 | Upper cap on required votes |
| Effective Threshold | 2 | max(MIN, min(N/3+1, CAP)) |
| `P2P_REGULAR_TIMEOUT` | 20s | Timeout for regular consensus |
| `P2P_ATTACK_TIMEOUT` | 30s | Timeout for attack consensus |
| `P2P_MAX_BROADCAST_PEERS` | 9 | Peers per vote broadcast |

### Deduplication & Knowledge

| Parameter | Value | Description |
|-----------|-------|-------------|
| `RPKI_DEDUP_WINDOW` | 15s | RPKI skip window (attacks bypass) |
| `NONRPKI_DEDUP_WINDOW` | 10s | Non-RPKI skip window (attacks bypass) |
| `KNOWLEDGE_WINDOW_SECONDS` | 720s | How long nodes remember observations |

### Attack Detection

| Parameter | Value | Description |
|-----------|-------|-------------|
| `FLAP_WINDOW_SECONDS` | 60s | Sliding window for route flapping |
| `FLAP_THRESHOLD` | 5 | State changes to trigger flapping alert |
| `ATTACK_CONSENSUS_MIN_VOTES` | 3 | Min votes for attack verdict |

### Simulation

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SIMULATION_SPEED_MULTIPLIER` | 1.0x | 1.0 = real-time |
| `INGESTION_BUFFER_MAX_SIZE` | 1200 | Per-node buffer cap |

## Dataset

| Metric | Value |
|--------|-------|
| Total ASes | 645 |
| RPKI Validators | 375 |
| Non-RPKI Observers | 270 |
| Total Observations | 1,253,482 |
| Attack Observations | 14,158 (1.1%) |
| Legitimate Observations | 1,239,324 |

## Throughput

| Metric | Value |
|--------|-------|
| Speed Multiplier | 1.0x |
| Wall-Clock Time | 688.1s |
| Total Observations Processed | 4,078 |
| **Network TPS (all nodes combined)** | **5.9** |
| Per-Node TPS (network TPS / node count) | 0.009 |
| RPKI Validators (consensus participants) | 375 |

> **Network TPS** = total observations processed / wall-clock seconds. Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.

## Node Processing

| Metric | Value |
|--------|-------|
| Nodes Completed | 0 / 645 |
| Total Observations Processed | 4,078 |
| Attacks Detected | 1,047 |
| Legitimate Processed | 2,587 |

> **WARNING:** 645 nodes did not finish. Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER`.

## Detection Performance (vs Ground Truth)

| Metric | Value |
|--------|-------|
| Ground Truth Attacks (unique) | 45 |
| Total Detections (unique) | 7 |
| True Positives | 7 |
| False Positives | 0 |
| False Negatives | 38 |
| **Precision** | **1.0000** |
| **Recall** | **0.1556** |
| **F1 Score** | **0.2692** |

> **38 attacks missed (false negatives).** Check if nodes had enough time to process all observations. Try increasing `--duration`.

## Blockchain (Per-Node Independent Chains)

| Metric | Value |
|--------|-------|
| Architecture | Per-node independent blockchains |
| Total Node Chains | 375 |
| Valid Chains | 375/375 |
| Blocks/Node (min/avg/max) | 7/8.9/266 |
| Transactions/Node (min/avg/max) | 6/8.4/266 |
| Total Forks Detected | 130918 |
| All Chains Valid | Yes |

## Cryptographic Signing

| Metric | Value |
|--------|-------|
| Key Algorithm | Ed25519 |
| Signature Scheme | Ed25519 |
| Total Key Pairs | 375 |

## Consensus (Proof of Population)

| Metric | Value |
|--------|-------|
| Consensus Threshold | 2 signatures |
| Transactions Created | 2,861 |
| Committed (consensus reached) | 242 |
| Pending (timed out / not enough votes) | 0 |
| **Commit Rate** | **8.5%** |

> **Low commit rate (8.5%).** Consider: increase `P2P_REGULAR_TIMEOUT` (currently 20s), increase `P2P_MAX_BROADCAST_PEERS` (currently 9), or lower `CONSENSUS_CAP_SIGNATURES` (currently 2).

## BGPCoin Economy

| Metric | Value |
|--------|-------|
| Total Supply | 10,000,000 |
| Treasury Balance | 9,975,245 |
| Total Distributed | 24,755 |
| Circulating Supply | 24,755 |
| Participating Nodes | 375 |
| Distribution Rate | 0.25% of supply |

## Non-RPKI Trust Ratings

| Category | Count |
|----------|-------|
| Malicious (0-29) | 1 |

| Stat | Value |
|------|-------|
| Total Rated ASes | 1 |
| Average Score | 25.00 |
| Lowest Score | 25 |
| Highest Score | 25 |

## Attack Verdicts

| Attack Type | Count |
|-------------|-------|
| BOGON_INJECTION | 97875 |

## Deduplication

| Metric | Value |
|--------|-------|
| RPKI Deduped | 0 |
| Non-RPKI Throttled | 0 |
| Total Skipped | 0 (0.0% of observations) |

## P2P Message Bus

| Metric | Value |
|--------|-------|
| Messages Sent | 36,788,345 |
| Messages Delivered | 36,788,345 |
| Messages Dropped | 0 |
| Delivery Rate | 100.00% |

## System Info

| Metric | Value |
|--------|-------|
| CPU | Intel(R) Xeon(R) Platinum 8358 CPU @ 2.60GHz |
| Cores | 128 |
| RAM | 1007.5 GB |
| Platform | Linux-5.15.0-113-generic-x86_64-with-glibc2.35 |
| Python | 3.10.12 |

## Tuning Recommendations

- **Missed 38 attacks**: Ensure `--duration` is long enough for all nodes to process their observations. Also check `KNOWLEDGE_WINDOW_SECONDS` (currently 720s).
- **Low commit rate (8.5%)**: Increase `P2P_REGULAR_TIMEOUT` (currently 20s) to give voters more time, or increase `P2P_MAX_BROADCAST_PEERS` (currently 9) to query more voters.
- **645 nodes incomplete**: Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER` (currently 1.0x).

## Output Files in This Folder

| File | What to Look For |
|------|-----------------|
| `README.md` | This report -- start here |
| `summary.json` | Overall run summary (dataset, nodes, timing) |
| `performance_metrics.json` | Precision, recall, F1 -- compare across runs |
| `detection_results.json` | Every detection decision by every node |
| `blockchain_stats.json` | Block count, integrity check, per-node replicas |
| `consensus_log.json` | Committed vs pending -- shows consensus health |
| `attack_verdicts.json` | Which attacks were confirmed/rejected by vote |
| `bgpcoin_economy.json` | Token distribution -- who earned what |
| `nonrpki_ratings.json` | Per-AS trust scores -- identify bad actors |
| `dedup_stats.json` | How many observations were skipped (efficiency) |
| `message_bus_stats.json` | P2P health -- any dropped messages? |
| `run_config.json` | Full config + hardware info for reproducibility |
| `crypto_summary.json` | Key algorithm and signature scheme used |

---
*Generated by BGP-Sentry main_experiment.py*