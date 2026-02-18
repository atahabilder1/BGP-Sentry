# BGP-Sentry Documentation Index

This directory contains detailed technical documentation for the BGP-Sentry blockchain-based BGP security framework. Each document covers a specific aspect of the system in depth.

## Documents

| Document | Description |
|----------|-------------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Full system architecture: data flow, RPKI validator pipeline, non-RPKI observer pipeline, key classes, consensus model, results format, and configuration reference |
| [OPTIMIZATIONS.md](OPTIMIZATIONS.md) | All 9 performance optimizations implemented to achieve real-time processing: consensus tuning, async message bus, Ed25519 signatures, early-skip dedup, buffer sampling, and more. Includes before/after measurements and configuration reference |
| [THROUGHPUT_ANALYSIS.md](THROUGHPUT_ANALYSIS.md) | Throughput benchmark results (1x-10x speed), TPS comparison with Bitcoin/Ethereum/Solana/Hyperledger, bottleneck analysis, and scaling strategies |
| [CONSENSUS_ESCALATION_EXPLAINED.md](CONSENSUS_ESCALATION_EXPLAINED.md) | How the system detects "learning attackers" whose BGP hijack attempts get progressively more consensus votes over time. Step-by-step examples, detection logic, and mitigation strategies |

## Quick Reference

### System Overview
- **What:** Distributed blockchain network where RPKI-enabled ASes act as validators and non-RPKI ASes act as observers
- **How:** Each BGP announcement becomes a blockchain transaction processed through BFT consensus (5 signatures required)
- **Why:** Detect and record BGP hijack attacks with cryptographic proof and decentralized trust

### Key Metrics (100-node network, caida_100 dataset)
- **Network TPS:** 4.2 (1x real-time) to 36.8 (10x speed)
- **Detection Accuracy:** F1 = 1.000 at all speeds
- **Consensus:** 5-signature BFT threshold, 3-5 second timeouts
- **Crypto:** Ed25519 (0.05ms sign, 0.1ms verify)
- **Message Delivery:** 100% (zero P2P message drops)

### Configuration
All 40+ tunable hyperparameters are in the `.env` file at the project root, organized into 8 groups (A-H). See the main [README.md](../README.md) for the full parameter reference table.

### Running Experiments
```bash
python3 main_experiment.py --dataset caida_100 --duration 1800
```
Results are written to `results/<dataset>/<timestamp>/` with 13 JSON files + a human-readable README.md summary.

### Reproducing Benchmarks
```bash
python3 scripts/benchmark_throughput.py --dataset caida_100
```
