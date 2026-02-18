# BGP-Sentry Experiment Report

**Dataset:** `caida_100` | **Date:** 2026-02-18T05:46:00 | **Duration:** 176.6s | **Speed:** 10.0x

## Executive Summary

| Metric | Result | Status |
|--------|--------|--------|
| Detection F1 Score | 1.0000 | PASS |
| Precision | 1.0000 | PASS |
| Recall | 1.0000 | PASS |
| Network TPS (all nodes combined) | 40.0 | GOOD |
| Consensus Commit Rate | 93.3% | GOOD |
| Blockchain Integrity | Valid | PASS |
| Message Delivery | 30.0% | PASS |
| Nodes Completed | 100/100 | PASS |

## Configuration Used

These are the `.env` parameters that were active for this run. Change these in `.env` and re-run to tune results.

### Consensus & P2P

| Parameter | Value | Description |
|-----------|-------|-------------|
| `CONSENSUS_MIN_SIGNATURES` | 3 | Min votes to commit a block |
| `CONSENSUS_CAP_SIGNATURES` | 5 | Upper cap on required votes |
| Effective Threshold | 5 | max(MIN, min(N/3+1, CAP)) |
| `P2P_REGULAR_TIMEOUT` | 3s | Timeout for regular consensus |
| `P2P_ATTACK_TIMEOUT` | 5s | Timeout for attack consensus |
| `P2P_MAX_BROADCAST_PEERS` | 5 | Peers per vote broadcast |

### Deduplication & Knowledge

| Parameter | Value | Description |
|-----------|-------|-------------|
| `RPKI_DEDUP_WINDOW` | 300s | RPKI skip window (attacks bypass) |
| `NONRPKI_DEDUP_WINDOW` | 120s | Non-RPKI skip window (attacks bypass) |
| `KNOWLEDGE_WINDOW_SECONDS` | 480s | How long nodes remember observations |

### Attack Detection

| Parameter | Value | Description |
|-----------|-------|-------------|
| `FLAP_WINDOW_SECONDS` | 60s | Sliding window for route flapping |
| `FLAP_THRESHOLD` | 5 | State changes to trigger flapping alert |
| `ATTACK_CONSENSUS_MIN_VOTES` | 3 | Min votes for attack verdict |

### Simulation

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SIMULATION_SPEED_MULTIPLIER` | 10.0x | 1.0 = real-time |
| `INGESTION_BUFFER_MAX_SIZE` | 1000 | Per-node buffer cap |

## Dataset

| Metric | Value |
|--------|-------|
| Total ASes | 100 |
| RPKI Validators | 58 |
| Non-RPKI Observers | 42 |
| Total Observations | 7,069 |
| Attack Observations | 333 (4.7%) |
| Legitimate Observations | 6,736 |

## Throughput

| Metric | Value |
|--------|-------|
| Speed Multiplier | 10.0x |
| Wall-Clock Time | 176.6s |
| Total Observations Processed | 7,069 |
| **Network TPS (all nodes combined)** | **40.0** |
| Per-Node TPS (network TPS / node count) | 0.4 |
| RPKI Validators (consensus participants) | 58 |

> **Network TPS** = total observations processed / wall-clock seconds. Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.

## Node Processing

| Metric | Value |
|--------|-------|
| Nodes Completed | 100 / 100 |
| Total Observations Processed | 7,069 |
| Attacks Detected | 265 |
| Legitimate Processed | 4,600 |

## Detection Performance (vs Ground Truth)

| Metric | Value |
|--------|-------|
| Ground Truth Attacks (unique) | 4 |
| Total Detections (unique) | 4 |
| True Positives | 4 |
| False Positives | 0 |
| False Negatives | 0 |
| **Precision** | **1.0000** |
| **Recall** | **1.0000** |
| **F1 Score** | **1.0000** |

## Blockchain

| Metric | Value |
|--------|-------|
| Total Blocks | 2,646 |
| Total Transactions | 2,645 |
| Latest Block # | 2645 |
| Integrity Valid | Yes |
| Node Replicas | 58 |
| All Replicas Valid | Yes |
| Valid Replicas | 58/58 |

## Cryptographic Signing

| Metric | Value |
|--------|-------|
| Key Algorithm | Ed25519 |
| Signature Scheme | Ed25519 |
| Total Key Pairs | 58 |

## Consensus (Proof of Population)

| Metric | Value |
|--------|-------|
| Consensus Threshold | 5 signatures |
| Transactions Created | 2,864 |
| Committed (consensus reached) | 2,673 |
| Pending (timed out / not enough votes) | 249 |
| **Commit Rate** | **93.3%** |

## BGPCoin Economy

| Metric | Value |
|--------|-------|
| Total Supply | 10,000,000 |
| Treasury Balance | 9,991,725 |
| Total Distributed | 8,275 |
| Circulating Supply | 8,275 |
| Participating Nodes | 58 |
| Distribution Rate | 0.08% of supply |

## Non-RPKI Trust Ratings

| Category | Count |
|----------|-------|

| Stat | Value |
|------|-------|
| Total Rated ASes | 0 |
| Average Score | 0.00 |
| Lowest Score | 0 |
| Highest Score | 0 |

## Attack Verdicts

No attack verdicts recorded in this run.

## Deduplication

| Metric | Value |
|--------|-------|
| RPKI Deduped | 1,219 |
| Non-RPKI Throttled | 917 |
| Total Skipped | 2,136 (30.2% of observations) |

## P2P Message Bus

| Metric | Value |
|--------|-------|
| Messages Sent | 174,784 |
| Messages Delivered | 52,484 |
| Messages Dropped | 0 |
| Delivery Rate | 30.03% |

## System Info

| Metric | Value |
|--------|-------|
| CPU | Intel(R) Core(TM) i7-9700 CPU @ 3.00GHz |
| Cores | 8 |
| RAM | 62.6 GB |
| Platform | Linux-6.17.0-14-generic-x86_64-with-glibc2.39 |
| Python | 3.10.19 |

## Tuning Recommendations

- All metrics look good. No changes needed for this configuration.

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