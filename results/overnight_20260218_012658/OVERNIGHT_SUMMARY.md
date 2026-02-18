# BGP-Sentry Overnight Test Report

**Generated:** 2026-02-18 01:26:58

## Phase 1: Full Experiments

| Dataset | Duration | Status | TPS | F1 | Blocks | Integrity |
|---------|----------|--------|-----|------|--------|-----------|
| caida_100 | 600s | PASS (1098s) | 0.0 | 0.0000 | N/A | INVALID |
| caida_200 | 600s | PASS (1072s) | 0.0 | 0.0000 | N/A | INVALID |
| caida_500 | 900s | PASS (3599s) | 0.0 | 0.4000 | N/A | INVALID |
| caida_1000 | 1200s | PASS (5627s) | 0.0 | 1.0000 | N/A | INVALID |

## Phase 2: Throughput Benchmark (caida_100)

| Speed | Wall Time | Network TPS | Precision | Recall | F1 |
|-------|-----------|-------------|-----------|--------|------|

## Phase 3: Blockchain Integrity Verification

| Dataset | Blocks | Hash Chain | Merkle Roots | Status |
|---------|--------|------------|--------------|--------|
| caida_100 | - | - | - | NO DATA |
| caida_200 | - | - | - | NO DATA |
| caida_500 | - | - | - | NO DATA |
| caida_1000 | - | - | - | NO DATA |

## Phase 4: Attack Verdicts

## Phase 5: Block Type Distribution

## Phase 6: Post-Hoc Analysis

### caida_100
- posthoc_analysis: see posthoc_caida_100.txt
- blockchain_forensics: see forensics_caida_100.txt
- targeted_attack_analyzer: see targeted_caida_100.txt

### caida_200
- posthoc_analysis: see posthoc_caida_200.txt
- blockchain_forensics: see forensics_caida_200.txt
- targeted_attack_analyzer: see targeted_caida_200.txt

### caida_500
- posthoc_analysis: see posthoc_caida_500.txt
- blockchain_forensics: see forensics_caida_500.txt
- targeted_attack_analyzer: see targeted_caida_500.txt

### caida_1000
- posthoc_analysis: see posthoc_caida_1000.txt
- blockchain_forensics: see forensics_caida_1000.txt
- targeted_attack_analyzer: see targeted_caida_1000.txt

## Phase 7: Plots

Plot generation failed.

## Phase 8: Python Syntax Verification

All modules pass syntax verification.

---

## Test Complete

**Finished:** 2026-02-18 05:46:22

### Output Files

| File | Description |
|------|-------------|
| OVERNIGHT_SUMMARY.md | This report |
| overnight_log.txt | Full console output |
| report_caida_*.md | Per-dataset experiment reports |
| verify_caida_*.txt | Blockchain verification output |
| posthoc_caida_*.txt | Post-hoc analysis output |
| forensics_caida_*.txt | Blockchain forensics output |
| targeted_caida_*.txt | Targeted attack analysis output |
| benchmark_caida_100.json | Throughput benchmark raw data |
| fig_*.png | Throughput plots |

