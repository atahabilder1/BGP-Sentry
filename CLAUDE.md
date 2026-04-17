# BGP-Sentry Design Decisions

## Architecture
- Only RPKI nodes are blockchain participants (validators). Non-RPKI nodes are passive and untrusted — they do NOT participate in consensus, voting, or blockchain writes.
- Each RPKI validator maintains its own independent blockchain (per-node chain architecture).
- The proposer (node that observed a BGP announcement) creates a transaction and broadcasts it to peers for voting. The proposer does NOT count as a signer — only external peer votes count.

## Consensus Levels
- **CONFIRMED** (3+ approve votes): Full consensus — highest trust weight.
- **INSUFFICIENT_CONSENSUS** (1-2 approve votes): Partial corroboration — medium trust weight.
- **SINGLE_WITNESS** (0 approve votes): Only the proposer saw it — lowest trust weight.
- All three levels are written to the blockchain. Nothing is discarded.
- Over time, multiple SINGLE_WITNESS entries from different proposers for the same (prefix, origin) accumulate and gain credibility through longitudinal analysis.

## Peer Selection for Voting
- Adaptive broadcast: peers asked = max(threshold * 2, sqrt(N)) — scales sublinearly with network size.
- Priority: relevant neighbors first (topology-aware from CAIDA), then random peers to fill remaining slots.

## Dedup
- RPKI dedup window (RPKI_DEDUP_WINDOW): skips repeated (prefix, origin) within N seconds. Attacks always bypass dedup.
- Goal is to record every unique BGP announcement on the blockchain. Dedup only prevents redundant duplicates within a short time window.

## Scalability Evaluation
- Primary metrics: consensus commit rate, fork detection/resolution, P2P message delivery, TPS (network and per-node).
- NOT accuracy/precision/recall — those are secondary.
- Test across growing node counts: 50 → 100 → 200 → 400 → 800 → 1600.

## Fork Resolution
- Forks are expected due to concurrent block production across independent chains.
- Fork merge blocks incorporate novel transactions from peer-replicated blocks.
- 100% fork resolution is the target.

## Attack Detectors
Seven enabled detectors orchestrated in `attack_detector.detect_attacks()`:
1. **PREFIX_HIJACK** — announcement claims ownership of a prefix with a different origin than ROA/blockchain state.
2. **SUBPREFIX_HIJACK** — more-specific announcement than a known ROA prefix, different origin.
3. **BOGON_INJECTION** — advertises a reserved / private / documentation prefix.
4. **FORGED_ORIGIN_PREFIX_HIJACK** — AS-path implies an origin that cannot plausibly have announced given the topology.
5. **ROUTE_FLAPPING** — rapid oscillation of the same (prefix, origin) beyond threshold.
6. **ROUTE_LEAK** — valley-free / Gao-Rexford violation: an AS re-announces a route from a provider or peer upward (to another provider or peer).
7. **PATH_POISONING** — AS-path contains an adjacency with no CAIDA-documented relationship between the two consecutive ASes, indicating a forged inserted hop.

One attack type is **intentionally filtered**:
- **ACCIDENTAL_ROUTE_LEAK** (from BGPy) — its forged-origin re-announcement pattern does not match the valley-free ROUTE_LEAK detector. Filtered to avoid artificial false-negatives.

Detectors 6 and 7 are evaluated on synthetic attack observations injected by
`scripts/inject_attacks.py` because BGPy's default scenarios do not exercise
these two vectors. Both achieve **100% recall on the injected events and
0% false positives on 300 legit samples per dataset** (see
`dataset/DATASET_REVISION.md` §Validation).

Taxonomy coverage (relative to standard BGP control-plane attack taxonomies):
- **5 of 5 control-plane attack categories covered** (Prefix Hijacking, Policy
  Violation, Invalid Injection, Path Manipulation, Control-Plane Instability)
- **7 of 8 individual attack types** — only AS-Path Prepending Abuse remains
  uncovered (ambiguous with legitimate traffic engineering, left to future work)
- Data-plane attacks (blackholing, MITM) are out of scope by architecture.

## Dataset
The `dataset/caida_N/` folders contain **revised** datasets (see `dataset/DATASET_REVISION.md`):
- Observations from BGPy Gao-Rexford over CAIDA 2022-01 topology.
- First-seen-per-observer dedup (from `scripts/fix_dataset_frequency.py`).
- Per-node legit rate tuned to real-world steady-state (~0.005 events/sec/validator; source: RIPE RIS 2022).
- Attack types restricted to the enabled detector set (ACCIDENTAL_ROUTE_LEAK / ROUTE_LEAK filtered out).
- Per-type event counts capped per dataset (effective ceiling: ~5 unique events per type from BGPy generation — each event naturally observed by many validators as network size grows, giving per-type statistics that scale with N).
- Originals archived in `dataset/_raw_backup_<date>/` for reproducibility.

Do not re-run `scripts/fix_dataset_frequency.py` — the revision is the active dataset. Re-apply via `scripts/revise_dataset.py all --apply` after restoring originals from the backup dir.
