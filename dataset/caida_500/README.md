# BGPSentry Dataset - CAIDA Subgraph (500 Nodes)

## Overview

This dataset contains **realistic BGP observations** generated using the **bgpy** simulation
framework on a **connected subgraph** extracted from the real **CAIDA AS-level Internet topology**.

Unlike the earlier Zoo topology datasets (ASN, Vlt, Tiscali), this dataset uses:
- **Real ASNs** from the actual Internet (e.g., AS7018 AT&T, AS13335 Cloudflare)
- **Real customer-provider and peer relationships** from CAIDA
- **Real RPKI/ROV deployment data** from rov-collector (6 measurement sources)
- **All 500 nodes** exported (no sampling) for blockchain consensus integrity

### Why This Approach?

Previous iterations used Internet Topology Zoo networks, which are **intra-AS router-level**
topologies with synthetic ASNs and degree-based RPKI heuristics. Those were discarded because:

1. **Not AS-level**: Zoo networks represent routers within a single ISP, not the inter-AS topology
2. **Synthetic ASNs**: Nodes are numbered 1, 2, 3... not real Internet AS numbers
3. **Fake RPKI**: RPKI status was assigned by node degree, not real-world ROV deployment
4. **No real relationships**: Customer-provider hierarchy was inferred from degree, not from
   actual BGP routing data

See `DATASET_METHODOLOGY.md` for the full evolution of dataset approaches.

## Data Sources

### Topology: CAIDA AS Relationships Dataset

- **Source**: [CAIDA AS Relationships](https://www.caida.org/catalog/datasets/as-relationships/)
- **Method**: BFS from highest-degree AS to extract 500-node connected subgraph
- **Full topology**: ~73,000 ASes with real customer-provider and peer links
- **Subgraph guarantee**: Connected (BFS ensures all nodes are reachable from seed)

> CAIDA infers AS relationships from BGP routing data collected by RouteViews and RIPE RIS.
> The dataset is updated periodically and is the gold standard for AS-level topology research.

### RPKI Data: rov-collector (6 Sources)

RPKI/ROV deployment status is determined by **real measurement data**, not heuristics:

| Source | Method | Reference |
|--------|--------|-----------|
| **RoVista** | Active measurement of ROV filtering | Li et al., IMC 2023 |
| **APNIC** | ROV measurement via APNIC labs | APNIC Research |
| **TMA** | Traffic and routing analysis | TMA Research |
| **FRIENDS** | Collaborative ROV measurement | FRIENDS Project |
| **IsBGPSafeYet** | Community-maintained ROV status | Cloudflare |
| **rpki.net** | RPKI repository monitoring | rpki.net |

Each AS's ROV adoption probability is aggregated across all sources.
The `rov-collector` library (used by bgpy) handles data collection and aggregation.

### Blockchain Role Assignment

In BGPSentry's **Proof of Population** consensus:
- **RPKI-enabled ASes** = **Blockchain validators** (can vote in consensus)
- **Non-RPKI ASes** = **Observers** (submit data but cannot vote)

This mapping is stored in `as_classification.json` under the `rpki_role` field.

## Simulation Framework: bgpy

1. **Subgraph extraction**: BFS from highest-degree AS in full CAIDA topology
2. **RPKI assignment**: Real ROV data from rov-collector (not degree heuristic)
3. **BGP Engine**: `SimulationEngine` with Gao-Rexford propagation model
4. **Scenarios**: 60 legitimate warm-up + 4 attack scenarios
5. **Extraction**: Full Adj-RIB-In capture from every AS (ALL nodes, no sampling)

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total ASes** | 500 |
| **RPKI ASes (validators)** | 206 (41.2%) |
| **Non-RPKI ASes (observers)** | 294 (58.8%) |
| **Total Announcements** | 38,499 |
| **Total Attacks** | 2,364 (6.14%) |
| **Legitimate** | 36,135 |
| **RPKI Source** | rov-collector (6 real measurement sources) |
| **Topology Source** | CAIDA AS Relationships |

### Attack Breakdown
| Attack Type | Count |
|-------------|-------|
| PREFIX_HIJACK | 591 |
| SUBPREFIX_HIJACK | 591 |
| BOGON_INJECTION | 591 |
| ROUTE_FLAPPING | 591 |

## Folder Structure

```
caida_500/
├── README.md
├── as_classification.json        # Real RPKI data + blockchain roles
├── observations/                  # 500 individual AS files (ALL nodes, real ASNs)
│   ├── AS<real_asn>.json
│   └── ...
└── ground_truth/
    ├── ground_truth.csv
    ├── ground_truth.json
    └── as_classification.json
```

## as_classification.json Schema

```json
{
  "rpki_source": "rov-collector (RoVista, APNIC, TMA, FRIENDS, IsBGPSafeYet, rpki.net)",
  "topology_source": "CAIDA AS Relationships Dataset",
  "subgraph_method": "BFS from highest-degree AS",
  "rpki_role": {
    "<asn>": "blockchain_validator",  // RPKI-enabled: can vote
    "<asn>": "observer"               // Non-RPKI: submits data only
  }
}
```

## Citation

If you use this dataset in your research, please cite:

```bibtex
@misc{bgpsentry_dataset_caida,
  title = {BGPSentry BGP Dataset (CAIDA Subgraph, 500 Nodes)},
  author = {BGPSentry Team},
  year = {2025},
  note = {Generated using bgpy with CAIDA AS topology and real RPKI data from rov-collector}
}

@misc{caida_as_relationships,
  title = {CAIDA AS Relationships Dataset},
  author = {Center for Applied Internet Data Analysis (CAIDA)},
  howpublished = {\url{https://www.caida.org/catalog/datasets/as-relationships/}},
  year = {2024}
}

@inproceedings{li2023rovista,
  title = {RoVista: Measuring and Analyzing the Route Origin Validation (ROV) in RPKI},
  author = {Li, Weitong and Chunhui, Liang and Testart, Cecilia and Calder, Matt and Claffy, KC},
  booktitle = {ACM Internet Measurement Conference (IMC)},
  year = {2023}
}
```

## Generated

- **Date**: 2026-02-13 14:54:30
- **Generator**: BGPSentry Dataset Generator
- **Mode**: CAIDA Subgraph (real ASNs, real RPKI data)
