# BGP-Sentry Experiment Report

**Dataset:** `caida_200` | **Date:** 2026-02-18T01:55:19 | **Duration:** 602.9s | **Speed:** 1.0x

## Executive Summary

| Metric | Result | Status |
|--------|--------|--------|
| Detection F1 Score | 0.0000 | LOW |
| Precision | 0.0000 | LOW -- false positives: 0 |
| Recall | 0.0000 | MISSED 4 attacks |
| Network TPS (all nodes combined) | 24.2 | GOOD |
| Consensus Commit Rate | 26.0% | LOW -- increase timeout or reduce threshold |
| Blockchain Integrity | INVALID | FAIL |
| Message Delivery | 67.7% | PASS |
| Nodes Completed | 0/200 | INCOMPLETE -- increase duration |

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
| Total ASes | 200 |
| RPKI Validators | 101 |
| Non-RPKI Observers | 99 |
| Total Observations | 15,038 |
| Attack Observations | 476 (3.2%) |
| Legitimate Observations | 14,562 |

## Throughput

| Metric | Value |
|--------|-------|
| Speed Multiplier | 1.0x |
| Wall-Clock Time | 602.9s |
| Total Observations Processed | 14,562 |
| **Network TPS (all nodes combined)** | **24.2** |
| Per-Node TPS (network TPS / node count) | 0.121 |
| RPKI Validators (consensus participants) | 101 |

> **Network TPS** = total observations processed / wall-clock seconds. Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.

## Node Processing

| Metric | Value |
|--------|-------|
| Nodes Completed | 0 / 200 |
| Total Observations Processed | 14,562 |
| Attacks Detected | 0 |
| Legitimate Processed | 11,095 |

> **WARNING:** 200 nodes did not finish. Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER`.

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
| Total Blocks | 4,523 |
| Total Transactions | 4,522 |
| Latest Block # | 4522 |
| Integrity Valid | No |
| Integrity Errors | Block 1314: Hash mismatch; Block 1314: Merkle root mismatch |
| Node Replicas | 101 |
| All Replicas Valid | Yes |
| Valid Replicas | 101/101 |

## Cryptographic Signing

| Metric | Value |
|--------|-------|
| Key Algorithm | Ed25519 |
| Signature Scheme | Ed25519 |
| Total Key Pairs | 101 |

## Consensus (Proof of Population)

| Metric | Value |
|--------|-------|
| Consensus Threshold | 5 signatures |
| Transactions Created | 5,354 |
| Committed (consensus reached) | 1,392 |
| Pending (timed out / not enough votes) | 920 |
| **Commit Rate** | **26.0%** |

> **Low commit rate (26.0%).** Consider: increase `P2P_REGULAR_TIMEOUT` (currently 3s), increase `P2P_MAX_BROADCAST_PEERS` (currently 5), or lower `CONSENSUS_CAP_SIGNATURES` (currently 5).

## BGPCoin Economy

| Metric | Value |
|--------|-------|
| Total Supply | 10,000,000 |
| Treasury Balance | 9,966,487 |
| Total Distributed | 33,513 |
| Circulating Supply | 33,493 |
| Participating Nodes | 101 |
| Distribution Rate | 0.34% of supply |

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
| ROUTE_FLAPPING | 412 |

## Deduplication

| Metric | Value |
|--------|-------|
| RPKI Deduped | 1,500 |
| Non-RPKI Throttled | 1,967 |
| Total Skipped | 3,467 (23.1% of observations) |

## P2P Message Bus

| Metric | Value |
|--------|-------|
| Messages Sent | 538,535 |
| Messages Delivered | 364,492 |
| Messages Dropped | 0 |
| Delivery Rate | 67.68% |

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
- **Low commit rate (26.0%)**: Increase `P2P_REGULAR_TIMEOUT` (currently 3s) to give voters more time, or increase `P2P_MAX_BROADCAST_PEERS` (currently 5) to query more voters.
- **200 nodes incomplete**: Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER` (currently 1.0x).
- **Blockchain integrity FAILED**: This is a critical error. Check `blockchain_stats.json` for details.

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