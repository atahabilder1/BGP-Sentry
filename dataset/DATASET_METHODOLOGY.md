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

### 2.3 Approach 3: CAIDA Subgraph + Real RPKI Data -- Final (Current)

**The insight:** We don't need the *full* CAIDA topology. We need a *connected subset* of it -- large enough to be meaningful, small enough that ALL nodes participate.

**The solution:** Combine the best of both previous approaches:
- From Approach 1: **Real CAIDA AS topology** (real ASNs, real customer-provider/peer relationships)
- From Approach 2: **Small enough for complete coverage** (all nodes exported, no sampling)
- **New:** Real RPKI data from `rov-collector` (6 measurement sources including RoVista)

**How it works:**

1. **Build full CAIDA topology** (~73,000 ASes) using bgpy's `CAIDAASGraphConstructor`
2. **Extract connected subgraph** via BFS from the highest-degree AS (see Section 3 for details)
3. **Get real RPKI data** from `rov-collector` -- 6 independent measurement sources
4. **Filter RPKI data** to only the ASNs in our subgraph
5. **Run simulations** on the subgraph with real RPKI assignments
6. **Export ALL nodes** (no sampling) -- every node in the subgraph participates

**Why this solves all previous problems:**

| Problem from Earlier | How This Approach Solves It |
|---------------------|---------------------------|
| Sampling breaks consensus | No sampling -- ALL nodes in the subgraph participate |
| Synthetic ASNs | Real ASNs from CAIDA (e.g., AS7018 AT&T, AS13335 Cloudflare) |
| Fake RPKI classification | Real ROV data from 6 measurement sources (RoVista, APNIC, etc.) |
| Inferred hierarchy | Real customer-provider/peer relationships from CAIDA |
| Synthetic PeerLinks | No synthetic links -- all links come from the real CAIDA topology |
| Scale too large | Subgraph is 100-1000 nodes -- manageable for proof-of-concept |
| Not AS-level | CAIDA topology is the gold standard for AS-level Internet research |

---

## 3. How We Extract the Subgraph from the Full CAIDA Topology

This is the core technical contribution of our dataset methodology. The question is: **how do you extract a meaningful, connected subset from 73,000 ASes?**

### 3.1 Why BFS (Breadth-First Search)?

We use BFS because it provides three critical guarantees:

1. **Connectivity:** Every node in the subgraph is reachable from every other node. BFS explores outward from a seed node layer by layer, so the resulting subgraph is always connected. This is essential because BGP propagation requires connectivity -- announcements must be able to reach all nodes.

2. **Local structure preservation:** BFS explores neighbors first, which means the subgraph preserves the local neighborhood structure around the seed. Nearby ASes in the real Internet remain nearby in the subgraph. This produces a more realistic topology than random sampling, which would scatter disconnected ASes across the Internet.

3. **Diversity of AS types:** Starting from a high-degree transit AS, BFS first visits other transit providers and large peers (layer 1), then medium-sized networks (layer 2), then stubs and small multihomed ASes (layer 3+). This naturally produces a subgraph with a realistic mix of transit, multihomed, and stub ASes.

### 3.2 The Algorithm

```
Algorithm: extract_caida_subgraph(max_size, seed_asn=None)

Input:  max_size (target number of ASes), optional seed ASN
Output: ASGraphInfo (links, clique, IXPs), set of real ASNs

1. Build full CAIDA AS graph via CAIDAASGraphConstructor().run()
   → Downloads/caches CAIDA AS relationship data
   → Constructs ASGraph with ~73,000 AS objects
   → Each AS has: customers, providers, peers, input_clique flag

2. Select BFS seed:
   IF seed_asn is specified:
     Use that AS as the seed
   ELSE:
     Pick the AS with the most neighbors (highest degree)
     → This is typically a Tier-1 provider with thousands of peers/customers

3. BFS traversal:
   visited = {seed_asn}
   queue = [seed_asn]

   WHILE queue is not empty AND |visited| < max_size:
     current = queue.popleft()
     FOR each neighbor of current (customers + peers + providers):
       IF neighbor not in visited:
         visited.add(neighbor)
         queue.append(neighbor)
         IF |visited| >= max_size: BREAK

4. Reconstruct links (keep only links where BOTH endpoints are in visited):
   FOR each ASN in visited:
     FOR each provider: if provider in visited → add CustomerProviderLink
     FOR each customer: if customer in visited → add CustomerProviderLink
     FOR each peer: if peer in visited → add PeerLink

5. Preserve metadata:
   input_clique_asns = {asn for asn in visited if as_obj.input_clique}
   ixp_asns = {asn for asn in visited if as_obj.ixp}

6. Free the full graph (save memory)

7. Return ASGraphInfo(cp_links, peer_links, input_clique, ixp_asns), visited
```

### 3.3 Seed Selection: Why Highest-Degree AS?

The BFS seed determines the "center" of the subgraph. We choose the AS with the highest degree (most neighbors) because:

- **Maximum coverage per hop:** A high-degree AS has hundreds or thousands of direct neighbors. Starting BFS here means even a small subgraph (100 nodes) captures significant topological diversity.
- **Realistic network core:** The highest-degree ASes are typically Tier-1 or large Tier-2 providers -- exactly the kind of ASes that form the backbone of the Internet. Starting from the core and expanding outward produces a subgraph that looks like a real regional Internet topology.
- **Deterministic:** For a given CAIDA snapshot, the highest-degree AS is fixed, making the subgraph reproducible.

The `--seed-asn` flag allows overriding this choice for experimentation (e.g., starting from a specific regional provider).

### 3.4 What Happens at the Subgraph Boundary?

ASes at the edge of the BFS subgraph may have real-world neighbors that are *not* in the subgraph. This means:
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

| Subgraph Size | RPKI Validators | Observers | RPKI % |
|---------------|----------------|-----------|--------|
| 100 nodes | 58 | 42 | 58.0% |
| 200 nodes | 101 | 99 | 50.5% |
| 500 nodes | 206 | 294 | 41.2% |
| 1,000 nodes | 366 | 634 | 36.6% |
| Global average | ~27,000 | ~46,000 | ~37% |

**Why does RPKI % decrease as subgraph size increases?** BFS starts from a high-degree AS (typically Tier-1). The first ~100 nodes are mostly large transit providers and their direct peers -- these are the organizations most likely to have deployed RPKI. As BFS expands to 500 and 1000 nodes, it reaches smaller, more peripheral ASes (stubs, small multihomed networks) that are less likely to have deployed RPKI. At 1000 nodes, the rate (36.6%) closely matches the real-world global average (~37%), confirming that our subgraph extraction produces realistic RPKI distributions at sufficient scale.

---

## 5. Simulation Model: How a Scenario Is Executed

### 5.1 Two-Phase Design

Each dataset is generated by running **64 total scenarios** in two phases:

**Phase 1: Legitimate Warm-Up (60 scenarios)**

Before any attack, the network runs 60 legitimate-only scenarios (`VictimsPrefix`). Each scenario selects a random victim that announces its prefix; all nodes propagate and converge normally. This produces ~94% of all observations.

**Phase 2: Attack Injection (4 scenarios)**

After warm-up, 4 attack scenarios are injected -- one of each type. Each independently selects a random attacker and victim. This models the real-world situation: steady-state operation, then a sudden hijack.

**Why 60+4?** This produces a ~5-6% attack ratio, matching the realistic rarity of BGP hijacks. A 50/50 split would make detection trivially easy; ~5% requires the system to genuinely detect rare anomalies.

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
| **PREFIX_HIJACK** | `1.2.0.0/16` | `1.2.0.0/16` (same prefix) |
| **SUBPREFIX_HIJACK** | `1.2.0.0/16` | `1.2.3.0/24` (more specific) |
| **BOGON_INJECTION** | *(none)* | `10.0.0.0/8` (RFC 1918 reserved) |
| **ROUTE_FLAPPING** | `1.2.0.0/16` | `1.2.0.0/16` (instability) |

---

## 6. Generated Datasets: Real Numbers

Four CAIDA subgraph datasets at increasing scale, demonstrating that the approach works from small proof-of-concept (100 nodes) to practical deployment (1,000 nodes):

### 6.1 Overall Statistics

| Dataset | Nodes | RPKI Validators | Observers | RPKI % | Total Announcements | Attack % |
|---------|-------|----------------|-----------|--------|---------------------|----------|
| **caida_100** | 100 | 58 | 42 | 58.0% | 7,069 | 4.71% |
| **caida_200** | 200 | 101 | 99 | 50.5% | 15,038 | 3.17% |
| **caida_500** | 500 | 206 | 294 | 41.2% | 38,499 | 6.14% |
| **caida_1000** | 1,000 | 366 | 634 | 36.6% | 80,665 | 4.59% |

### 6.2 Attack Breakdown Per Dataset

| Attack Type | caida_100 | caida_200 | caida_500 | caida_1000 |
|-------------|-----------|-----------|-----------|------------|
| PREFIX_HIJACK | 103 | 7 | 591 | 1,234 |
| SUBPREFIX_HIJACK | 107 | 232 | 591 | 1,234 |
| BOGON_INJECTION | 115 | 235 | 591 | 1,234 |
| ROUTE_FLAPPING | 8 | 2 | 591 | 2 |
| **Total attacks** | **333** | **476** | **2,364** | **3,704** |

**Why do attack counts vary?** Each attack scenario independently selects a random attacker and victim. The attacker's position in the topology determines how many nodes receive the attack announcement. A well-connected attacker near the core reaches more nodes; a peripheral stub attacker reaches fewer. This randomness is realistic -- in the real Internet, the impact of a hijack depends heavily on the attacker's position.

### 6.3 Observation Quality

| Metric | caida_100 | caida_200 | caida_500 | caida_1000 |
|--------|-----------|-----------|-----------|------------|
| Best routes (FIB) | 7,049 | 15,030 | 38,495 | 80,661 |
| Alternative routes (Adj-RIB-In) | 20 | 8 | 4 | 4 |
| Legitimate observations | 6,736 | 14,562 | 36,135 | 76,961 |
| Scenarios run | 64 | 64 | 64 | 64 |

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
      "prefix": "1.2.0.0/16",
      "origin_asn": 13335,
      "as_path": [7018, 3356, 13335],
      "as_path_length": 3,
      "next_hop_asn": 3356,
      "timestamp": 1770835360,
      "timestamp_readable": "2026-02-11 13:42:40",
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
  "subgraph_method": "BFS from highest-degree AS",
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

### Generate All Four Datasets

```bash
python generate_rpki_dataset.py --topology caida --nodes 100
python generate_rpki_dataset.py --topology caida --nodes 200
python generate_rpki_dataset.py --topology caida --nodes 500
python generate_rpki_dataset.py --topology caida --nodes 1000
```

### CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--topology` | `caida` | `caida` (real ASNs + real RPKI) or legacy Zoo: `ASN`, `Vlt`, `Tiscali` |
| `--nodes` | 200 | Target subgraph size. BFS stops when this many ASes are collected. |
| `--seed-asn` | *(auto)* | BFS seed. Default: highest-degree AS in CAIDA topology. |
| `--adoption` | 0.37 | RPKI rate for Zoo topologies only. Ignored for CAIDA (uses real data). |
| `--legitimate-scenarios` | 60 | Number of legitimate warm-up scenarios. |
| `--output` | `dataset` | Output directory. |

---

## 10. Limitations and Assumptions

1. **CAIDA snapshot dependency.** The subgraph depends on the CAIDA snapshot used. bgpy's collector downloads and caches a specific snapshot. Different snapshots may produce different subgraphs.

2. **ROV data is probabilistic.** ASes with <100% ROV probability are included stochastically. Different runs may produce slightly different RPKI sets (but consistent within a single generation run).

3. **BFS locality bias.** BFS from a single seed produces a subgraph centered around that seed's neighborhood. The subgraph over-represents the core Internet. This is acceptable because BGPSentry's validators (RPKI ASes) are concentrated in the core.

4. **Subgraph boundary effects.** Edge ASes in the subgraph may have real-world neighbors outside the subgraph, so their routing behavior may differ from the full Internet.

5. **Fixed IP prefixes.** All scenarios use `1.2.0.0/16`, `1.2.3.0/24`, `10.0.0.0/8`. Standard in BGP simulation research.

6. **Single attacker, single victim per scenario.** Real attacks may involve multiple colluding attackers.

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
| Reproducible | Partially | Yes | Yes |

The CAIDA subgraph approach is the only one that satisfies all six requirements simultaneously.

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
