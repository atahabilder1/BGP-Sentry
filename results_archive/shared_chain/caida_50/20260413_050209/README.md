# BGP-Sentry Experiment Report

**Dataset:** `caida_50` | **Date:** 2026-04-13T05:07:12 | **Duration:** 302.7s | **Speed:** 1.0x

## Executive Summary

| Metric | Result | Status |
|--------|--------|--------|
| Detection F1 Score | 0.6000 | REVIEW |
| Precision | 1.0000 | PASS |
| Recall | 0.4286 | MISSED 8 attacks |
| Network TPS (all nodes combined) | 16.7 | GOOD |
| Consensus Commit Rate | 38.3% | LOW -- increase timeout or reduce threshold |
| Blockchain Integrity | Valid | PASS |
| Message Delivery | 100.0% | PASS |
| Nodes Completed | 0/48 | INCOMPLETE -- increase duration |

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
| Total ASes | 48 |
| RPKI Validators | 26 |
| Non-RPKI Observers | 22 |
| Total Observations | 22,329 |
| Attack Observations | 363 (1.6%) |
| Legitimate Observations | 21,966 |

## Throughput

| Metric | Value |
|--------|-------|
| Speed Multiplier | 1.0x |
| Wall-Clock Time | 302.7s |
| Total Observations Processed | 5,052 |
| **Network TPS (all nodes combined)** | **16.7** |
| Per-Node TPS (network TPS / node count) | 0.348 |
| RPKI Validators (consensus participants) | 26 |

> **Network TPS** = total observations processed / wall-clock seconds. Standard blockchain metric: Bitcoin ~7, Ethereum ~15-30, BGP-Sentry peak 36.8.

## Node Processing

| Metric | Value |
|--------|-------|
| Nodes Completed | 0 / 48 |
| Total Observations Processed | 5,052 |
| Attacks Detected | 113 |
| Legitimate Processed | 4,803 |

> **WARNING:** 48 nodes did not finish. Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER`.

## Detection Performance (vs Ground Truth)

| Metric | Value |
|--------|-------|
| Ground Truth Attacks (unique) | 14 |
| Total Detections (unique) | 6 |
| True Positives | 6 |
| False Positives | 0 |
| False Negatives | 8 |
| **Precision** | **1.0000** |
| **Recall** | **0.4286** |
| **F1 Score** | **0.6000** |

> **8 attacks missed (false negatives).** Check if nodes had enough time to process all observations. Try increasing `--duration`.

## Blockchain (Per-Node Independent Chains)

| Metric | Value |
|--------|-------|
| Architecture | Per-node independent blockchains |
| Total Node Chains | 26 |
| Valid Chains | 26/26 |
| Blocks/Node (min/avg/max) | 8/45.5/62 |
| Transactions/Node (min/avg/max) | 7/47.8/67 |
| Total Forks Detected | 23079 |
| All Chains Valid | Yes |

## Cryptographic Signing

| Metric | Value |
|--------|-------|
| Key Algorithm | Ed25519 |
| Signature Scheme | Ed25519 |
| Total Key Pairs | 26 |

## Consensus (Proof of Population)

| Metric | Value |
|--------|-------|
| Consensus Threshold | 2 signatures |
| Transactions Created | 2,643 |
| Committed (consensus reached) | 1,011 |
| Pending (timed out / not enough votes) | 0 |
| **Commit Rate** | **38.3%** |

> **Low commit rate (38.3%).** Consider: increase `P2P_REGULAR_TIMEOUT` (currently 20s), increase `P2P_MAX_BROADCAST_PEERS` (currently 9), or lower `CONSENSUS_CAP_SIGNATURES` (currently 2).

## BGPCoin Economy

| Metric | Value |
|--------|-------|
| Total Supply | 10,000,000 |
| Treasury Balance | 9,982,832 |
| Total Distributed | 17,168 |
| Circulating Supply | 17,168 |
| Participating Nodes | 26 |
| Distribution Rate | 0.17% of supply |

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
| Messages Sent | 33,410 |
| Messages Delivered | 33,410 |
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

- **Missed 8 attacks**: Ensure `--duration` is long enough for all nodes to process their observations. Also check `KNOWLEDGE_WINDOW_SECONDS` (currently 720s).
- **Low commit rate (38.3%)**: Increase `P2P_REGULAR_TIMEOUT` (currently 20s) to give voters more time, or increase `P2P_MAX_BROADCAST_PEERS` (currently 9) to query more voters.
- **48 nodes incomplete**: Increase `--duration` or reduce `SIMULATION_SPEED_MULTIPLIER` (currently 1.0x).

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