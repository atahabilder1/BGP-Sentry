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
- Test across growing node counts: 50 → 150 → 400 → 800 → 1200.

## Fork Resolution
- Forks are expected due to concurrent block production across independent chains.
- Fork merge blocks incorporate novel transactions from peer-replicated blocks.
- 100% fork resolution is the target.
