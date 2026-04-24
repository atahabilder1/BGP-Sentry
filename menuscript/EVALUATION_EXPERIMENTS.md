# Evaluation Experiments TODO

## Design Rule
- **Representative topology: caida_200** — all detailed figures use 200-node topology
- **Summary table (Table 4):** columns for all scales (50, 100, 150, 200, 400, 800, 1200)
- No figure duplicates what's in the table; figures show depth, table shows breadth

## Finalized Assets
- Table 3 (dataset stats) ✓
- Fig 7 (per-attack detection + confusion matrix) ✓ — **200-node topology**
- Fig 10 (observer coverage scenarios, appendix) ✓
- Table 6 (forensic audit) ✓ — all scales
- Table 5 (throughput) — partial (100–1K only)

## Figure & Table Assignment

| Element | Content | Topology | Section |
|---|---|---|---|
| Table 3 | Dataset stats | All scales | §5.1 Setup |
| Fig 7 | Detection bar + confusion matrix | **200 only** | §5.2 Detection |
| Table 4 | Scalability metrics (consensus, P2P, TPS) + F1 per attack across scales | **All scales (50–1200)** | §5.3 Scalability |
| Fig 9 | Pipeline: cumulative data flow + time breakdown | **200 only** | §5.3 Scalability |
| Fig 6 | Trust trajectories (3 AS types) | **200 only** | §5.4 Trust Scoring |
| Table 6 | Forensic audit (attacker identification) | All scales | §5.4 Trust Scoring |
| Fig 8 | Non-RPKI coverage over time | **200 primary** (other scales as extra lines) | §5.4 Trust Scoring |

## Experiments Needed

### EXP-1: Trust Score Trajectory (replaces Fig 6 placeholder)
**Purpose:** Validate Reactive + Adaptive Trust Engines and demonstrate recovery.
**Topology:** caida_200

**Setup:** Run simulation with 3 designated non-RPKI ASes:
1. **Always dishonest** — AS commits attacks every round (e.g., PREFIX_HIJACK repeatedly)
2. **Always honest** — AS only makes legitimate announcements throughout
3. **Misconfigured → reformed** — AS commits 1–2 attacks early, then stops and behaves cleanly for the remainder

**Expected trajectories (demo data for now):**
- Dishonest: 50 → 30 (−20 prefix hijack) → 0 (−30 repeat penalty) → stays 0
- Honest: 50 → 51 (+1 per 100 legit) → 56 (+5 monthly) → ... → 70+ (Trusted tier)
- Reformed: 50 → 30 (−20 attack) → 35 (+5 monthly) → 40 → 45 → ... → 50+ (Neutral recovery)

**Data source:** Extract from `rating_history.jsonl` — already logs every score change with timestamp.

**What it validates:**
- Reactive Trust Engine: penalties accumulate correctly
- Adaptive Trust Engine: monthly +5 reward for clean behavior works
- Recovery: system is not a permanent blacklist (differentiator from prior work)
- OAL is truly longitudinal, not a snapshot

**Where it goes:** Move Fig 6 from §3 to §5.4 (Trust Scoring). Replace placeholder with 3-line plot + tier boundaries.

---

### EXP-2: Complete Table 4 for scales 400, 800, 1200
**Purpose:** Validate scalability claims. Currently columns for 400, 800, 1200 are all 0.00.

**Setup:** Run `main_experiment.py` at scales 400, 800, 1200 using existing CAIDA BFS subgraphs.

**Metrics to collect per scale:**
- Detection: F1 per attack type (4 rows)
- Consensus: TX created, confirmed %, endorsed %, observed %, fork resolution, valid chains %
- P2P: message count, delivery rate
- TPS: network TPS, per-node TPS
- Wall-clock time

**Note:** BGPCOIN rows move to appendix table. Detection rows stay in Table 4 as a compact summary (F1 only, one row per attack type) even though Fig 7 shows 200-node detail — the table shows whether it generalizes.

---

### EXP-3: Per-Transaction Consensus Latency
**Purpose:** Validate the abstract's "<3.2 seconds" consensus latency claim. Currently zero data.
**Topology:** Measure at caida_200, report across all scales in Table 4.

**Setup:** Instrument `attack_consensus.py` or `virtual_node.py` to log timestamp at TX creation and at block commit. Compute delta per TX.

**Metrics:**
- Median, P95, P99 consensus latency per scale
- Add as rows in Table 4

**Where it goes:** Table 4 rows + one sentence in §5.3 prose.

---

### EXP-4: Observer Discovery Cost (optional, strengthens contribution ii)
**Purpose:** Validate sub-linear O(k) claim for observer discovery.

**Setup:** Log number of peers queried per transaction across scales.

**Metrics:**
- Avg peers queried per TX vs total N
- Compare with broadcast-to-all baseline (O(N))

---

## Proposed §5 Structure

### §5.1 Experimental Setup
- Table 3 (dataset stats) ✓
- One sentence: single-machine caveat
- One sentence: reference Appendix D for end-to-end verification

### §5.2 Detection Correctness
- **Fig 7** (200-node): per-attack bar chart + confusion matrix ✓
- Prose: 100% recall at ≥200, flapping FP trade-off (tunable FLAP_THRESHOLD)
- Reference Table 4 for cross-scale F1 summary

### §5.3 Consensus and Scalability
- **Table 4** (all scales): F1 per attack, consensus breakdown, P2P, TPS, latency
- **Fig 9** (200-node): pipeline data flow + time breakdown
- Prose: commit rate vs scale trade-off, fork resolution = 100%

### §5.4 Trust Scoring and Forensic Audit
- **Fig 6** (200-node): 3 trust trajectories (dishonest / honest / reformed)
- **Table 6** (all scales): forensic attacker identification ✓
- **Fig 8** (200-node primary): non-RPKI coverage over time
- Prose: scores match expected penalties, tier assignments correct, recovery works

### Appendix additions
- BGPCOIN economy table (moved from Table 4)
- Trust recovery details (if space)

---

## Redundancy Cleanup (editing only, no experiments)

| Redundant content | Appears in | Keep in | Remove from |
|---|---|---|---|
| "100% observation coverage" | §3, §5 setup, Appendix E | §5 setup | §3 (just reference) |
| "Zero data loss" | §3, §5.1, §5.3, §5b, Fig caption, Appendix D | Appendix D + one line in §5 | everywhere else |
| Consensus threshold formula | §3 Alg1, §4 ×2, §5b, §5.3 | §3 Alg1 (definition) | reference by name elsewhere |
| SHA-256 integrity check | §5.1, §5.3, Appendix D | Appendix D | §5.1 and §5.3 |
| Single-machine caveat | §5.3 (1 para), §6 (3 paras) | §5 setup (1 sentence) | §6 reduce to 1 sentence |
| BGP Coin economy details | §3, §4, §5.3 | Appendix | §3 keep 1 sentence, remove from §5.3 |
| Penalty values | §3, §4 Table 1, Alg 2 | §4 Table 1 | §3 reference Table 1 |
| Five trust tiers | §1, §3, §4, §5.1 | §3 (definition) | reference elsewhere |
