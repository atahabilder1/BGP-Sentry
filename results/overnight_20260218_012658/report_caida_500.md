# BGP-Sentry Experiment Report

**Dataset:** `caida_500` | **Date:** 2026-02-18T02:18:13 | **Duration:** 903.5s | **Speed:** 1.0x

## Executive Summary

| Metric | Result | Status |
|--------|--------|--------|
| Detection F1 Score | 0.4000 | LOW |
| Precision | 1.0000 | PASS |
| Recall | 0.2500 | MISSED 3 attacks |
| Network TPS (all nodes combined) | 40.6 | GOOD |
| Consensus Commit Rate | 10.4% | LOW -- increase timeout or reduce threshold |
| Blockchain Integrity | Valid | PASS |
| Message Delivery | 71.9% | PASS |
| Nodes Completed | 0/500 | INCOMPLETE -- increase duration |

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
| `SIMULATION_SPEED_MULTIPLIER` | 1.0x | 1.0 = real-time |
| `INGESTION_BUFFER_MAX_SIZE` | 1000 | Per-node buffer cap |

## Dataset

| Metric | Value |
|--------|-------|
| Total ASes | 500 |
| RPKI Validators | 206 |
| Non-RPKI Observers | 294 |
| Total Observations | 38,499 |
| Attack Observations | 2,364 (6.1%) |
| Legitimate Observations | 36,135 |

## Throughput

| Metric | Value |
|--------|-------|
| Speed Multiplier | 1.0x |
| Wall-Clock Time | 903.5s |
| Total Observations Processed | 36,726 |
| **Network TPS (all nodes combined)** | **40.6** |
| Per-Node TPS (network TPS / node count) | 0.081 |
| RPKI Validators (consensus participants) | 206 |

> **Network TPS** = total observations processed / wall-clock seconds. Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.

## Node Processing

| Metric | Value |
|--------|-------|
| Nodes Completed | 0 / 500 |
| Total Observations Processed | 36,726 |
| Attacks Detected | 591 |
| Legitimate Processed | 28,500 |

> **WARNING:** 500 nodes did not finish. Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER`.

## Detection Performance (vs Ground Truth)

| Metric | Value |
|--------|-------|
| Ground Truth Attacks (unique) | 4 |
| Total Detections (unique) | 1 |
| True Positives | 1 |
| False Positives | 0 |
| False Negatives | 3 |
| **Precision** | **1.0000** |
| **Recall** | **0.2500** |
| **F1 Score** | **0.4000** |

> **3 attacks missed (false negatives).** Check if nodes had enough time to process all observations. Try increasing `--duration`.

## Blockchain

| Metric | Value |
|--------|-------|
| Total Blocks | 5,960 |
| Total Transactions | 5,959 |
| Latest Block # | 5959 |
| Integrity Valid | Yes |
| Node Replicas | 206 |
| All Replicas Valid | Yes |
| Valid Replicas | 206/206 |

## Cryptographic Signing

| Metric | Value |
|--------|-------|
| Key Algorithm | Ed25519 |
| Signature Scheme | Ed25519 |
| Total Key Pairs | 206 |

## Consensus (Proof of Population)

| Metric | Value |
|--------|-------|
| Consensus Threshold | 5 signatures |
| Transactions Created | 11,980 |
| Committed (consensus reached) | 1,248 |
| Pending (timed out / not enough votes) | 6,176 |
| **Commit Rate** | **10.4%** |

> **Low commit rate (10.4%).** Consider: increase `P2P_REGULAR_TIMEOUT` (currently 3s), increase `P2P_MAX_BROADCAST_PEERS` (currently 5), or lower `CONSENSUS_CAP_SIGNATURES` (currently 5).

## BGPCoin Economy

| Metric | Value |
|--------|-------|
| Total Supply | 10,000,000 |
| Treasury Balance | 9,989,751 |
| Total Distributed | 10,249 |
| Circulating Supply | 10,249 |
| Participating Nodes | 206 |
| Distribution Rate | 0.10% of supply |

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
| RPKI Deduped | 2,861 |
| Non-RPKI Throttled | 4,774 |
| Total Skipped | 7,635 (19.8% of observations) |

## P2P Message Bus

| Metric | Value |
|--------|-------|
| Messages Sent | 1,308,430 |
| Messages Delivered | 941,328 |
| Messages Dropped | 0 |
| Delivery Rate | 71.94% |

## System Info

| Metric | Value |
|--------|-------|
| CPU | Intel(R) Core(TM) i7-9700 CPU @ 3.00GHz |
| Cores | 8 |
| RAM | 62.6 GB |
| Platform | Linux-6.17.0-14-generic-x86_64-with-glibc2.39 |
| Python | 3.10.19 |

## Tuning Recommendations

- **Missed 3 attacks**: Ensure `--duration` is long enough for all nodes to process their observations. Also check `KNOWLEDGE_WINDOW_SECONDS` (currently 480s).
- **Low commit rate (10.4%)**: Increase `P2P_REGULAR_TIMEOUT` (currently 3s) to give voters more time, or increase `P2P_MAX_BROADCAST_PEERS` (currently 5) to query more voters.
- **500 nodes incomplete**: Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER` (currently 1.0x).

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