# BGP-Sentry Experiment Report

**Dataset:** `caida_100` | **Date:** 2026-02-18T01:37:00 | **Duration:** 601.5s | **Speed:** 1.0x

## Executive Summary

| Metric | Result | Status |
|--------|--------|--------|
| Detection F1 Score | 0.0000 | LOW |
| Precision | 0.0000 | LOW -- false positives: 0 |
| Recall | 0.0000 | MISSED 4 attacks |
| Network TPS (all nodes combined) | 11.2 | GOOD |
| Consensus Commit Rate | 93.5% | GOOD |
| Blockchain Integrity | Valid | PASS |
| Message Delivery | 100.0% | PASS |
| Nodes Completed | 0/100 | INCOMPLETE -- increase duration |

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
| Total ASes | 100 |
| RPKI Validators | 58 |
| Non-RPKI Observers | 42 |
| Total Observations | 7,069 |
| Attack Observations | 333 (4.7%) |
| Legitimate Observations | 6,736 |

## Throughput

| Metric | Value |
|--------|-------|
| Speed Multiplier | 1.0x |
| Wall-Clock Time | 601.5s |
| Total Observations Processed | 6,736 |
| **Network TPS (all nodes combined)** | **11.2** |
| Per-Node TPS (network TPS / node count) | 0.112 |
| RPKI Validators (consensus participants) | 58 |

> **Network TPS** = total observations processed / wall-clock seconds. Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.

## Node Processing

| Metric | Value |
|--------|-------|
| Nodes Completed | 0 / 100 |
| Total Observations Processed | 6,736 |
| Attacks Detected | 0 |
| Legitimate Processed | 4,642 |

> **WARNING:** 100 nodes did not finish. Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER`.

## Detection Performance (vs Ground Truth)

| Metric | Value |
|--------|-------|
| Ground Truth Attacks (unique) | 4 |
| Total Detections (unique) | 0 |
| True Positives | 0 |
| False Positives | 0 |
| False Negatives | 4 |
| **Precision** | **0.0000** |
| **Recall** | **0.0000** |
| **F1 Score** | **0.0000** |

> **4 attacks missed (false negatives).** Check if nodes had enough time to process all observations. Try increasing `--duration`.

## Blockchain

| Metric | Value |
|--------|-------|
| Total Blocks | 2,676 |
| Total Transactions | 2,675 |
| Latest Block # | 2675 |
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
| Transactions Created | 2,668 |
| Committed (consensus reached) | 2,494 |
| Pending (timed out / not enough votes) | 0 |
| **Commit Rate** | **93.5%** |

## BGPCoin Economy

| Metric | Value |
|--------|-------|
| Total Supply | 10,000,000 |
| Treasury Balance | 9,959,820 |
| Total Distributed | 40,180 |
| Circulating Supply | 40,040 |
| Participating Nodes | 58 |
| Distribution Rate | 0.40% of supply |

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

| Attack Type | Count |
|-------------|-------|
| ROUTE_FLAPPING | 406 |

## Deduplication

| Metric | Value |
|--------|-------|
| RPKI Deduped | 1,219 |
| Non-RPKI Throttled | 875 |
| Total Skipped | 2,094 (29.6% of observations) |

## P2P Message Bus

| Metric | Value |
|--------|-------|
| Messages Sent | 202,297 |
| Messages Delivered | 202,297 |
| Messages Dropped | 0 |
| Delivery Rate | 100.00% |

## System Info

| Metric | Value |
|--------|-------|
| CPU | Intel(R) Core(TM) i7-9700 CPU @ 3.00GHz |
| Cores | 8 |
| RAM | 62.6 GB |
| Platform | Linux-6.17.0-14-generic-x86_64-with-glibc2.39 |
| Python | 3.10.19 |

## Tuning Recommendations

- **Missed 4 attacks**: Ensure `--duration` is long enough for all nodes to process their observations. Also check `KNOWLEDGE_WINDOW_SECONDS` (currently 480s).
- **100 nodes incomplete**: Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER` (currently 1.0x).

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