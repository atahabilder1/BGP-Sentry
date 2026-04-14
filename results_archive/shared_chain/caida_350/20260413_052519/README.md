# BGP-Sentry Experiment Report

**Dataset:** `caida_350` | **Date:** 2026-04-13T05:30:56 | **Duration:** 336.4s | **Speed:** 1.0x

## Executive Summary

| Metric | Result | Status |
|--------|--------|--------|
| Detection F1 Score | 0.5581 | REVIEW |
| Precision | 0.7500 | LOW -- false positives: 4 |
| Recall | 0.4444 | MISSED 15 attacks |
| Network TPS (all nodes combined) | 124.8 | GOOD |
| Consensus Commit Rate | 22.9% | LOW -- increase timeout or reduce threshold |
| Blockchain Integrity | Valid | PASS |
| Message Delivery | 100.0% | PASS |
| Nodes Completed | 0/347 | INCOMPLETE -- increase duration |

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
| Total ASes | 347 |
| RPKI Validators | 207 |
| Non-RPKI Observers | 140 |
| Total Observations | 514,585 |
| Attack Observations | 4,583 (0.9%) |
| Legitimate Observations | 510,002 |

## Throughput

| Metric | Value |
|--------|-------|
| Speed Multiplier | 1.0x |
| Wall-Clock Time | 336.4s |
| Total Observations Processed | 41,974 |
| **Network TPS (all nodes combined)** | **124.8** |
| Per-Node TPS (network TPS / node count) | 0.36 |
| RPKI Validators (consensus participants) | 207 |

> **Network TPS** = total observations processed / wall-clock seconds. Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.

## Node Processing

| Metric | Value |
|--------|-------|
| Nodes Completed | 0 / 347 |
| Total Observations Processed | 41,974 |
| Attacks Detected | 1,859 |
| Legitimate Processed | 39,341 |

> **WARNING:** 347 nodes did not finish. Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER`.

## Detection Performance (vs Ground Truth)

| Metric | Value |
|--------|-------|
| Ground Truth Attacks (unique) | 27 |
| Total Detections (unique) | 16 |
| True Positives | 12 |
| False Positives | 4 |
| False Negatives | 15 |
| **Precision** | **0.7500** |
| **Recall** | **0.4444** |
| **F1 Score** | **0.5581** |

> **4 false positives detected.** Most are from route flapping. To reduce: increase `FLAP_THRESHOLD` (currently 5) or increase `FLAP_WINDOW_SECONDS`.

> **15 attacks missed (false negatives).** Check if nodes had enough time to process all observations. Try increasing `--duration`.

## Blockchain (Per-Node Independent Chains)

| Metric | Value |
|--------|-------|
| Architecture | Per-node independent blockchains |
| Total Node Chains | 207 |
| Valid Chains | 207/207 |
| Blocks/Node (min/avg/max) | 6/31.8/69 |
| Transactions/Node (min/avg/max) | 5/32.3/72 |
| Total Forks Detected | 906004 |
| All Chains Valid | Yes |

## Cryptographic Signing

| Metric | Value |
|--------|-------|
| Key Algorithm | Ed25519 |
| Signature Scheme | Ed25519 |
| Total Key Pairs | 207 |

## Consensus (Proof of Population)

| Metric | Value |
|--------|-------|
| Consensus Threshold | 2 signatures |
| Transactions Created | 24,487 |
| Committed (consensus reached) | 5,601 |
| Pending (timed out / not enough votes) | 0 |
| **Commit Rate** | **22.9%** |

> **Low commit rate (22.9%).** Consider: increase `P2P_REGULAR_TIMEOUT` (currently 20s), increase `P2P_MAX_BROADCAST_PEERS` (currently 9), or lower `CONSENSUS_CAP_SIGNATURES` (currently 2).

## BGPCoin Economy

| Metric | Value |
|--------|-------|
| Total Supply | 10,000,000 |
| Treasury Balance | 9,914,185 |
| Total Distributed | 85,815 |
| Circulating Supply | 85,815 |
| Participating Nodes | 207 |
| Distribution Rate | 0.86% of supply |

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
| RPKI Deduped | 0 |
| Non-RPKI Throttled | 0 |
| Total Skipped | 0 (0.0% of observations) |

## P2P Message Bus

| Metric | Value |
|--------|-------|
| Messages Sent | 1,064,434 |
| Messages Delivered | 1,064,434 |
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

- **Missed 15 attacks**: Ensure `--duration` is long enough for all nodes to process their observations. Also check `KNOWLEDGE_WINDOW_SECONDS` (currently 720s).
- **Low commit rate (22.9%)**: Increase `P2P_REGULAR_TIMEOUT` (currently 20s) to give voters more time, or increase `P2P_MAX_BROADCAST_PEERS` (currently 9) to query more voters.
- **347 nodes incomplete**: Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER` (currently 1.0x).

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