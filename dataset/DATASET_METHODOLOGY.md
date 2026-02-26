# BGPSentry Dataset Generation: Methodology and Design Decisions

## 1. Purpose and Motivation

This dataset was generated for the **BGPSentry** research paper, which proposes a blockchain-based BGP monitoring system using **Proof of Population** consensus. Evaluating BGPSentry requires labeled BGP announcement data with known ground truth -- i.e., which announcements are legitimate and which are attacks. Real-world BGP data from route collectors (RIPE RIS, RouteViews) does not ship with attack labels because real hijacks are not annotated at the time they occur. Therefore, we use simulation to produce data where the ground truth is established by construction.

The simulation is built on top of **bgpy**, a peer-reviewed BGP security simulator used by NIST and multiple research teams. bgpy implements the Gao-Rexford model of BGP propagation and can simulate the entire Internet AS-level topology (~73,000 ASes) on a single machine.

**Key constraint from BGPSentry's design:**
- **RPKI-enabled ASes** are the **blockchain validators** (they can vote in Proof of Population consensus)
- **Non-RPKI ASes** are **observers** (they submit BGP data but cannot vote)
- **All nodes** in the topology must participate -- no sampling allowed, because every validator's vote matters for BFT consensus integrity
- RPKI classification must be **real** (from actual measurement data), not synthetic, because it determines who gets validator authority on the blockchain

---

## 2. Evolution of Dataset Approaches: What We Tried and Why Each Was Discarded

This section documents every approach we explored, in chronological order. Understanding the full journey is important because each failed approach taught us a constraint that shaped the final design.

### 2.1 Approach 1: Full CAIDA Topology with Sampling (~73,000 ASes) -- Discarded

**What we tried:**

bgpy's default mode uses the full CAIDA AS-level Internet topology (~73,000 real ASes with real customer-provider and peer relationships inferred from BGP routing data). We attempted to use this directly: run attack/legitimate scenarios across the full 73K topology, then **sample** a subset of nodes (100-1000) for the dataset.

**Why it was discarded:**

| Problem | Details |
|---------|---------|
| **Sampling breaks consensus** | BGPSentry's Proof of Population requires ALL nodes to participate in consensus. Sampling 100 nodes from 73K means 99.86% of the network is excluded. The blockchain cannot reach quorum if most validators are missing. If we sample, we are no longer simulating blockchain consensus -- we are simulating a random subset observing traffic, which is fundamentally different. |
| **Sampling introduces selection bias** | Which 100 nodes do we pick? Random sampling over-represents stubs (which make up ~85% of ASes). Stratified sampling requires knowing the "right" strata. Any sampling strategy biases the dataset toward or against certain network positions, which biases the consensus results. |
| **Scale is impractical for proof-of-concept** | 73K ASes x 64 scenarios = millions of observation files. Each AS stores its Local RIB state for every scenario, resulting in significant compute time (~hours per run) and memory pressure (>8GB RAM). For a research paper proof-of-concept, this is unnecessarily heavy. |
| **Reproducibility** | CAIDA data requires a license agreement and changes with every monthly snapshot. A paper depending on a specific CAIDA snapshot from January 2022 cannot be exactly reproduced if that snapshot is no longer available. |

**Lesson learned:** We need a topology small enough that ALL nodes can participate (no sampling), but it must still use real AS-level data. The "sample from full Internet" approach fundamentally conflicts with blockchain consensus requirements.

### 2.2 Approach 2: Internet Topology Zoo (ASN, Vlt, Tiscali) -- Discarded

**What we tried:**

To solve the "all nodes must participate" problem, we turned to small, fixed topologies from the [Internet Topology Zoo](http://www.topology-zoo.org/). These are static, publicly available, citable network topologies:

| Dataset | Network | Nodes | Edges | Origin |
|---------|---------|-------|-------|--------|
| `ASN_18` | ANS (Advanced Network & Services) | 18 | 25 | US backbone |
| `Vlt_92` | Virginia Tech network | 92 | 96 | University backbone |
| `Tiscali_161` | Tiscali ISP | 161 | 328 | European ISP |

These were attractive because they are small enough to export ALL nodes without sampling, they are static and reproducible, and they are citable academic resources.

We wrote a complete pipeline:
1. Parse GML files to extract nodes and edges
2. Infer BGP hierarchy from node degree (core nodes = providers, edge nodes = customers)
3. Add synthetic PeerLinks between top-tier nodes to prevent network fragmentation
4. Assign RPKI status using a degree-based heuristic (top 37% by degree = RPKI adopters)
5. Run 60 legitimate + 4 attack scenarios
6. Export ALL nodes' observations

**Why it was discarded -- the RPKI mapping problem:**

The critical flaw was in step 4: **RPKI classification was fake.**

| Problem | Details |
|---------|---------|
| **Not AS-level topologies** | Zoo topologies represent **intra-AS router-level** networks (routers within a single ISP), not the **inter-AS** topology that BGP operates on. BGP is a protocol *between* Autonomous Systems. These networks show routers *within* one AS. The nodes are not ASes at all -- they are routers. |
| **Synthetic ASNs** | Because Zoo nodes are routers (not ASes), we had to assign synthetic ASNs by offsetting GML node IDs: node 0 = AS1, node 1 = AS2, etc. These are not real Internet AS numbers. AS1 is not AT&T, AS2 is not Level3 -- they are meaningless synthetic identifiers. A reviewer or professor examining the dataset would immediately see that these ASNs don't correspond to any real Internet entities. |
| **RPKI classification was a degree heuristic, not real data** | This is the fatal problem for BGPSentry. We assigned RPKI status by sorting nodes by degree and marking the top 37% as "RPKI adopters." But in reality, RPKI adoption depends on organizational decisions, regulatory requirements, business relationships, and regional policy -- not on how many cables a router has. **If the RPKI classification is fake, then the blockchain validator set is fake, and the entire Proof of Population evaluation is meaningless.** A professor would rightly ask: "How do you know your consensus results reflect reality if your validators are chosen by a heuristic instead of actual RPKI deployment data?" |
| **Inferred hierarchy is approximate** | BGP hierarchy (customer-provider, peer) was inferred from node degree, not from actual routing data. Real Internet AS relationships are determined by commercial transit agreements, which CAIDA infers from actual BGP routing data -- not from physical connectivity degree. |
| **Synthetic PeerLinks distort the topology** | In sparse Zoo topologies (e.g., Vlt with 92 nodes and only 96 edges -- nearly a tree), we had to add synthetic PeerLinks between input clique members to prevent the network from fragmenting into isolated propagation islands. For Tiscali, we added 115 synthetic PeerLinks. These links don't exist in any real network and further distance the dataset from reality. |

**What was valuable from this approach:**
- Proved the simulation pipeline works end-to-end
- Confirmed that "all nodes exported" is feasible and necessary
- The two-phase design (60 legitimate warm-up + 4 attacks) produces realistic ~5-6% attack ratios
- The Adj-RIB-In interceptor correctly captures all received announcements

**Lesson learned:** The topology source and RPKI data source must both be real. A heuristic RPKI classification makes the entire blockchain evaluation invalid, because the wrong ASes would be validators.

### 2.3 Approach 3: CAIDA Subgraph + Real RPKI Data -- Trace-Driven (Current)

**The insight:** We don't need the *full* CAIDA topology. We need a *connected subset* of it -- large enough to be meaningful, small enough that ALL nodes participate. Moreover, every dataset component must be traceable to real-world data so a reviewer cannot dismiss the results as "fabricated."

**Design principle:** *"Topology from CAIDA, RPKI from rov-collector, prefix counts proportional to real AS sizes, propagation via Gao-Rexford — only attack injection is simulated, as real BGP feeds lack ground truth labels."*

**The solution:** Combine the best of both previous approaches with trace-driven enhancements:
- From Approach 1: **Real CAIDA AS topology** (real ASNs, real customer-provider/peer relationships)
- From Approach 2: **Small enough for complete coverage** (all nodes exported, no sampling)
- **New:** Real RPKI data from `rov-collector` (6 measurement sources including RoVista)
- **New:** Stratified hierarchical sampling (preserves tier ratios instead of BFS star topology)
- **New:** Dynamic per-AS prefix counts proportional to AS type
- **New:** Multiple attack instances per type with different victim/attacker pairs
- **New:** Per-hop convergence jitter modeling BGP MRAI timer dynamics

**How it works:**

1. **Build full CAIDA topology** (~73,000 ASes) using bgpy's `CAIDAASGraphConstructor`
2. **Stratified hierarchical sampling**: ALL input_clique (~19 ASes), ~10% transit, ~15% multihomed, fill remaining with stubs. Union-find bridge reconnection ensures connectivity.
3. **Get real RPKI data** from `rov-collector` -- 6 independent measurement sources
4. **Dynamic prefix assignment**: Each AS gets prefixes proportional to its type (stubs: 1-3, multihomed: 2-5, transit: 5-20, clique: 20-50)
5. **Legitimate warm-ups**: Each round picks 5-10 random victim ASes with their real prefixes
6. **Attack injection**: Each attack type runs N times (default 5) with different randomly-selected victim/attacker pairs and target prefixes
7. **Post-processing**: Per-hop convergence jitter on timestamps
8. **Export ALL nodes** (no sampling) -- every node in the subgraph participates

**Why this solves all previous problems:**

| Problem from Earlier | How This Approach Solves It |
|---------------------|---------------------------|
| Sampling breaks consensus | No sampling -- ALL nodes in the subgraph participate |
| Synthetic ASNs | Real ASNs from CAIDA (e.g., AS7018 AT&T, AS13335 Cloudflare) |
| Fake RPKI classification | Real ROV data from 6 measurement sources (RoVista, APNIC, etc.) |
| Inferred hierarchy | Real customer-provider/peer relationships from CAIDA |
| Synthetic PeerLinks | No synthetic links -- all links come from the real CAIDA topology |
| Scale too large | Subgraph is 50-10,000 nodes -- manageable for proof-of-concept |
| Not AS-level | CAIDA topology is the gold standard for AS-level Internet research |
| Star topology (BFS) | Stratified sampling preserves tier ratios |
| 3 hardcoded prefixes | Dynamic per-AS prefix allocation |
| 1 attacker per type | N attack instances with different pairs |
| Identical timestamps | Per-hop convergence jitter |

---

## 3. How We Extract the Subgraph from the Full CAIDA Topology

This is the core technical contribution of our dataset methodology. The question is: **how do you extract a meaningful, connected subset from 73,000 ASes that preserves the Internet's hierarchical tier structure?**

### 3.1 Why Stratified Hierarchical Sampling?

Previous versions used BFS from the highest-degree AS. While BFS guarantees connectivity, it creates a **star topology** where all paths go through a single hub AS, and the tier distribution is distorted (mostly transit/core ASes, very few stubs). A reviewer could dismiss this as not representative of the real Internet.

Stratified hierarchical sampling provides:

1. **Tier preservation:** The subgraph contains ASes from every tier of the Internet hierarchy -- input_clique (Tier-1), transit, multihomed, and stubs -- in proportions that reflect the real Internet.

2. **No single-hub bias:** Unlike BFS from one seed, sampling from each tier independently ensures that no single AS dominates all paths.

3. **Connectivity via bridge reconnection:** After sampling, union-find detects disconnected components, then BFS in the full graph finds shortest paths between components and adds intermediate "bridge" ASes.

### 3.2 The Algorithm

```
Algorithm: extract_caida_subgraph(max_size)

Input:  max_size (target number of ASes)
Output: ASGraphInfo (links, clique, IXPs), set of real ASNs

1. Build full CAIDA AS graph via CAIDAASGraphConstructor().run()
   → Downloads/caches CAIDA AS relationship data
   → Constructs ASGraph with ~73,000 AS objects
   → Pre-computed tier groups: input_clique, etc (transit), multihomed, stub

2. Stratified sampling:
   sampled = ALL input_clique ASes (~19, always included)
   budget = max_size - |sampled|
   sample ~15% of budget from transit ASes (randomly)
   sample ~20% of remaining budget from multihomed ASes (randomly)
   fill remaining budget with stub ASes (randomly)

3. Bridge reconnection:
   Build subgraph adjacency (only links where both endpoints in sampled)
   components = union_find(sampled, subgraph_adjacency)

   IF |components| > 1:
     Sort components largest-first
     main_component = components[0]
     FOR each smaller component:
       BFS in full graph from component to main_component
       Add all intermediate ASes on shortest path to sampled
       Merge component into main_component

4. Reconstruct links (keep only links where BOTH endpoints are in sampled):
   FOR each ASN in sampled:
     FOR each provider: if provider in sampled → add CustomerProviderLink
     FOR each customer: if customer in sampled → add CustomerProviderLink
     FOR each peer: if peer in sampled → add PeerLink

5. Handle disconnected ASes:
   ASes with no links in the subgraph → added to unlinked_asns in ASGraphInfo

6. Return ASGraphInfo(cp_links, peer_links, input_clique, ixp_asns, unlinked), sampled
```

### 3.3 Why Include ALL Input Clique ASes?

The input clique (~19 Tier-1 ASes) forms the fully-meshed core of the Internet. Including all of them ensures:
- Announcements can propagate through the core (essential for Gao-Rexford)
- The subgraph has a realistic backbone structure
- RPKI validators at the core are accurately represented

### 3.4 Bridge Reconnection

Randomly sampled ASes from different tiers are often disconnected (they may be geographically or topologically far apart). The bridge reconnection step:
1. Uses **union-find** to efficiently detect disconnected components
2. For each component, runs **BFS in the full CAIDA graph** to find the shortest path to the largest component
3. Adds intermediate ASes (bridges) to connect them
4. Budget: up to 50% of max_size for bridges

This ensures connectivity while adding only real ASes with real relationships.

### 3.5 What Happens at the Subgraph Boundary?

ASes at the edge of the subgraph may have real-world neighbors that are *not* in the subgraph. This means:
- Their propagation behavior in the simulation may differ from the full Internet
- They may receive fewer announcements (because some paths are cut off at the boundary)
- This is inherent to any subgraph extraction method and is a known limitation

However, the *interior* of the subgraph closely matches the real Internet topology, because all internal links are preserved.

---

## 4. Real-World RPKI Data: How We Determine Blockchain Validators

### 4.1 Why Real RPKI Data Matters for BGPSentry

In BGPSentry's Proof of Population consensus:
- **RPKI-enabled ASes = blockchain validators** (one vote per AS)
- **Non-RPKI ASes = observers** (submit data but cannot vote)

If we assign RPKI status by heuristic (as we did with Zoo topologies), the validator set is meaningless. The whole point of Proof of Population is that *real* RPKI-deploying ASes -- organizations that have demonstrated commitment to routing security -- serve as trusted validators. A degree-based heuristic says nothing about whether an organization has actually deployed RPKI.

### 4.2 Data Source: rov-collector (6 Measurement Sources)

We use bgpy's `get_real_world_rov_asn_cls_dict()` function, which aggregates ROV deployment data from **6 independent measurement sources**:

| Source | Method | Reference |
|--------|--------|-----------|
| **RoVista** | Active measurement of ROV filtering behavior | Li et al., ACM IMC 2023 |
| **APNIC** | ROV measurement via APNIC Labs | APNIC Research |
| **TMA** | Traffic and routing analysis | TMA Research |
| **FRIENDS** | Collaborative ROV measurement | FRIENDS Project |
| **IsBGPSafeYet** | Community-maintained ROV status database | Cloudflare |
| **rpki.net** | RPKI repository monitoring | rpki.net |

For each AS, the function:
1. Collects ROV adoption probability from all sources that report on that AS
2. Takes the **maximum probability** across all sources
3. For ASes with 100% probability: always classified as ROV-enabled
4. For ASes with partial probability: included probabilistically (e.g., 80% chance → included ~80% of the time)
5. Special case: AT&T (AS 7018) is classified as PeerROV (only filters peer announcements)

### 4.3 Filtering to Subgraph

After collecting worldwide ROV data, we filter to only ASNs in our subgraph:

```python
rpki_asns = frozenset(asn for asn in rov_dict if asn in subgraph_asns)
```

This ensures every RPKI classification in the dataset corresponds to a **real measurement** of that specific AS's ROV deployment.

### 4.4 Observed RPKI Adoption Rates

RPKI adoption rates in the subgraph depend on which ASes are selected. With stratified sampling (which always includes all ~19 Tier-1 input_clique ASes), smaller subgraphs tend to have higher RPKI rates because input_clique ASes are disproportionately RPKI-enabled. As the subgraph grows larger and includes more stub ASes, the rate converges toward the real-world global average (~37%).

The `--seed` flag ensures reproducible RPKI rates across runs.

---

## 5. Simulation Model: How a Scenario Is Executed

### 5.1 Three-Phase Design

Each dataset is generated in three phases:

**Phase 1: Legitimate Warm-Up (60 scenarios by default)**

Before any attack, the network runs legitimate-only scenarios. Each scenario picks 5-10 random victim ASes from the subgraph and announces their dynamically-assigned prefixes. All nodes propagate and converge normally. This produces the majority of all observations.

**Phase 2: Attack Injection (4 types x N instances each)**

Each attack type runs N times (default 5, configurable via `--attacks-per-type`) with:
- **Different randomly-selected victim/attacker pairs** each time
- **Different target prefixes** from the victim's prefix assignments
- Custom override announcements passed via `ScenarioConfig`

This means the dataset contains 20 attack scenarios (4 types x 5 each) with diverse attacker/victim positions, instead of the previous 4 scenarios with a single fixed pair per type.

**Phase 3: Post-Processing**

- **Convergence jitter**: Per-hop delay added to timestamps based on AS path length (modeling BGP MRAI timer, RFC 4271)
- **Visibility stats**: Diversity metrics computed and logged (prefixes-per-AS, origins-per-AS variation)

**Why this ratio?** With 60 legitimate + 20 attack scenarios, the attack ratio is ~4-6%, matching the realistic rarity of BGP hijacks.

### 5.2 BGP Propagation: Gao-Rexford Model

Each round consists of three strictly ordered phases:

1. **Provider propagation** (ascending rank): Stubs → transit → input clique. Announcements flow UPWARD.
2. **Peer propagation** (all simultaneously): Announcements flow LATERALLY between peers.
3. **Customer propagation** (descending rank): Input clique → transit → stubs. Announcements flow DOWNWARD.

Best path selection: **Local Preference** (customer > peer > provider) > **AS Path Length** (shorter wins) > **Neighbor ASN** (lower wins as tiebreak).

### 5.3 Full Adj-RIB-In Capture

We install a monkey-patched interceptor on every AS's `receive_ann()` method to capture ALL incoming announcements -- not just the best route. Each observation is tagged with `is_best` (true = selected for FIB, false = received but rejected).

### 5.4 Multi-Hop Relay for Full Coverage

Nodes that receive no announcements (due to valley-free constraints) relay what their nearest neighbors heard (`hop_distance=1` or `hop_distance=2`). This ensures near-complete participation in consensus.

### 5.5 Attack Types

| Scenario | Victim Announces | Attacker Announces |
|----------|-----------------|-------------------|
| **PREFIX_HIJACK** | Victim's assigned prefix | Same prefix as victim |
| **SUBPREFIX_HIJACK** | Victim's assigned prefix | More-specific subprefix (auto-generated) |
| **BOGON_INJECTION** | Victim's assigned prefix | Random RFC 1918/6598 reserved prefix |
| **ROUTE_FLAPPING** | Victim's assigned prefix | Same prefix (instability) |

Each attack type runs N times (default 5) with different victim/attacker/prefix combinations.

### 5.6 Dynamic Prefix Assignment

Per-AS prefix counts are proportional to AS type, consistent with observed Internet prefix distribution (Huston, APNIC):

| AS Type | Prefix Count | Prefix Lengths |
|---------|-------------|----------------|
| Input clique (Tier-1) | 20-50 | /16-/20 |
| Transit | 5-20 | /18-/24 |
| Multihomed | 2-5 | /22-/24 |
| Stubs | 1-3 | /24 |

Prefixes are allocated sequentially from non-reserved space (44.0.0.0+), guaranteeing no overlap.

### 5.7 Timestamp Convergence Jitter

Per-announcement jitter based on AS path length models the BGP MRAI timer (RFC 4271, default 30s) with jitter, consistent with measured convergence dynamics (Labovitz et al., 2001):

```
timestamp += sum(uniform(0.5, 15.0) for each hop in path)
```

- Path length 1: +0.5-15s
- Path length 3: +1.5-45s
- Path length 6: +3-90s

---

## 6. Generated Datasets

Six CAIDA subgraph datasets at increasing scale, demonstrating that the approach works from small proof-of-concept (50 nodes) to large-scale evaluation (10,000 nodes):

```bash
python generate_rpki_dataset.py --nodes 50 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 100 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 200 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 500 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 1000 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 10000 --attacks-per-type 5 --seed 42
```

Note: Actual subgraph size may exceed `--nodes` due to bridge ASes added during reconnection.

**Why do attack counts vary?** Each attack scenario independently selects a random attacker and victim. The attacker's position in the topology determines how many nodes receive the attack announcement. A well-connected attacker near the core reaches more nodes; a peripheral stub attacker reaches fewer. With N instances per type, the dataset covers diverse attacker/victim positions across the topology.

---

## 7. Output Directory Structure

```
dataset/
├── DATASET_METHODOLOGY.md          <-- This file
├── caida_100/                      <-- 100-node CAIDA subgraph
│   ├── observations/               # 100 AS files (real ASNs, ALL nodes)
│   │   ├── AS24.json
│   │   ├── AS72.json
│   │   └── ...
│   ├── ground_truth/
│   │   ├── ground_truth.csv
│   │   ├── ground_truth.json
│   │   └── as_classification.json
│   ├── as_classification.json      # Real RPKI data + blockchain roles
│   └── README.md
├── caida_200/                      <-- 200-node CAIDA subgraph
│   ├── observations/               # 200 AS files
│   ├── ground_truth/
│   ├── as_classification.json
│   └── README.md
├── caida_500/                      <-- 500-node CAIDA subgraph
│   ├── observations/               # 500 AS files
│   ├── ground_truth/
│   ├── as_classification.json
│   └── README.md
└── caida_1000/                     <-- 1,000-node CAIDA subgraph
    ├── observations/               # 1,000 AS files
    ├── ground_truth/
    ├── as_classification.json
    └── README.md
```

---

## 8. File Schemas

### Per-AS Observation File (`observations/AS{real_asn}.json`)

```json
{
  "asn": 7018,
  "is_rpki_node": true,
  "total_observations": 5,
  "best_route_observations": 3,
  "alternative_route_observations": 2,
  "attack_observations": 1,
  "legitimate_observations": 4,
  "observations": [
    {
      "prefix": "44.0.0.0/16",
      "origin_asn": 13335,
      "as_path": [7018, 3356, 13335],
      "as_path_length": 3,
      "next_hop_asn": 3356,
      "timestamp": 1770835387,
      "timestamp_readable": "2026-02-11 13:43:07",
      "recv_relationship": "CUSTOMERS",
      "origin_type": "VICTIM",
      "label": "LEGITIMATE",
      "is_attack": false,
      "observed_by_asn": 7018,
      "observer_is_rpki": true,
      "hop_distance": 0,
      "relayed_by_asn": null,
      "is_best": true
    }
  ]
}
```

### as_classification.json

```json
{
  "description": "Classification of ASes as RPKI or non-RPKI",
  "total_ases": 200,
  "rpki_count": 101,
  "non_rpki_count": 99,
  "rpki_source": "rov-collector (RoVista, APNIC, TMA, FRIENDS, IsBGPSafeYet, rpki.net)",
  "topology_source": "CAIDA AS Relationships Dataset",
  "subgraph_method": "Stratified hierarchical sampling (preserves tier ratios)",
  "rpki_role": {
    "7018": "blockchain_validator",
    "13335": "blockchain_validator",
    "64496": "observer"
  },
  "classification": {
    "7018": "RPKI",
    "13335": "RPKI",
    "64496": "NON_RPKI"
  }
}
```

---

## 9. How to Reproduce

### Prerequisites

```bash
pip install -e .[test]    # Install bgpy with dependencies
```

### Generate Datasets (Trace-Driven)

```bash
python generate_rpki_dataset.py --nodes 50 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 100 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 200 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 500 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 1000 --attacks-per-type 5 --seed 42
python generate_rpki_dataset.py --nodes 10000 --attacks-per-type 5 --seed 42
```

### CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--topology` | `caida` | `caida` (real ASNs + real RPKI) or legacy Zoo: `ASN`, `Vlt`, `Tiscali` |
| `--nodes` | 200 | Target subgraph size (stratified sampling). |
| `--attacks-per-type` | 5 | Number of attack instances per attack type. |
| `--seed` | *(none)* | Random seed for reproducibility. |
| `--seed-asn` | *(auto)* | Kept for backward compatibility (ignored in stratified mode). |
| `--adoption` | 0.37 | RPKI rate for Zoo topologies only. Ignored for CAIDA (uses real data). |
| `--legitimate-scenarios` | 60 | Number of legitimate warm-up scenarios. |
| `--output` | `dataset` | Output directory. |

---

## 10. Limitations and Assumptions

1. **CAIDA snapshot dependency.** The subgraph depends on the CAIDA snapshot used. bgpy's collector downloads and caches a specific snapshot. Different snapshots may produce different subgraphs. Use `--seed` for reproducible random selection within a snapshot.

2. **ROV data is probabilistic.** ASes with <100% ROV probability are included stochastically. Different runs may produce slightly different RPKI sets (but consistent within a single generation run, and deterministic with `--seed`).

3. **Stratified sampling may exceed target size.** Bridge ASes added during reconnection can push the subgraph beyond `--nodes`. The actual size may be 10-50% larger than requested, especially for small target sizes where the ~19 input_clique ASes consume a large fraction of the budget.

4. **Subgraph boundary effects.** Edge ASes in the subgraph may have real-world neighbors outside the subgraph, so their routing behavior may differ from the full Internet.

5. **Single attacker per attack instance.** Each attack instance uses one attacker and one victim. Real attacks may involve multiple colluding attackers. However, with N instances per type, the dataset covers diverse attacker/victim positions.

6. **Synthetic IP prefixes.** While prefix *counts* are proportional to real AS types, the actual prefix addresses (44.0.0.0+) are synthetic. This is standard in BGP simulation research and does not affect routing behavior.

---

## 11. Summary: Why This Is the Right Approach

| Requirement | Full CAIDA (Approach 1) | Zoo Topologies (Approach 2) | **CAIDA Subgraph (Approach 3)** |
|-------------|------------------------|----------------------------|-------------------------------|
| Real ASNs | Yes | **No** (synthetic) | **Yes** |
| Real AS relationships | Yes | **No** (degree-inferred) | **Yes** |
| Real RPKI data | Possible but not used | **No** (degree heuristic) | **Yes** (6 sources) |
| All nodes participate | **No** (must sample) | Yes | **Yes** |
| Manageable scale | **No** (73K ASes) | Yes | **Yes** |
| No synthetic links | Yes | **No** (added PeerLinks) | **Yes** |
| Tier structure preserved | Yes | **No** (flat topology) | **Yes** (stratified sampling) |
| Diverse prefixes per AS | N/A | **No** (3 hardcoded) | **Yes** (proportional to type) |
| Multiple attack instances | N/A | **No** (1 per type) | **Yes** (N per type) |
| Realistic timestamps | N/A | **No** (batched) | **Yes** (per-hop jitter) |
| Reproducible | Partially | Yes | **Yes** (with `--seed`) |

The trace-driven CAIDA subgraph approach is the only one that satisfies all requirements simultaneously.

---

## 12. References

```bibtex
@misc{caida_as_relationships,
  title   = {CAIDA AS Relationships Dataset},
  author  = {Center for Applied Internet Data Analysis (CAIDA)},
  howpublished = {\url{https://www.caida.org/catalog/datasets/as-relationships/}},
  year    = {2024}
}

@inproceedings{li2023rovista,
  title     = {RoVista: Measuring and Analyzing the Route Origin Validation (ROV) in RPKI},
  author    = {Li, Weitong and Chunhui, Liang and Testart, Cecilia and Calder, Matt and Claffy, KC},
  booktitle = {ACM Internet Measurement Conference (IMC)},
  year      = {2023}
}

@article{knight2011internet,
  title   = {The Internet Topology Zoo},
  author  = {Knight, Simon and Nguyen, Hung X. and Falkner, Nick
             and Bowden, Rhys and Roughan, Matthew},
  journal = {IEEE Journal on Selected Areas in Communications},
  volume  = {29},
  number  = {9},
  pages   = {1765--1775},
  year    = {2011}
}

@inproceedings{gao2001inferring,
  title     = {On inferring autonomous system relationships in the Internet},
  author    = {Gao, Lixin},
  booktitle = {IEEE/ACM Transactions on Networking},
  volume    = {9},
  number    = {6},
  pages     = {733--745},
  year      = {2001}
}
```

**bgpy simulation framework:**
- Repository: https://github.com/jfuruness/bgpy
- Used by NIST and multiple research teams; peer-reviewed and published.
- Implements the Gao-Rexford model with support for 20+ routing policies including ROV, ASPA, BGPSec, and others.
