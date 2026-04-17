#!/usr/bin/env python3
"""
Inject synthetic PATH_POISONING and VALLEY_FREE ROUTE_LEAK attack events
into an already-revised dataset.

Why synthetic:
  BGPy's default attack scenarios do not exercise path-poisoning or
  valley-free-violating route-leak vectors, so the corresponding
  detectors in attack_detector.py have no data to evaluate.  This
  script produces minimally-realistic but well-formed BGP UPDATE
  observations matching each detector's signature, which lets us
  report per-detector precision / recall.

Injection model (deliberately simple so reviewers can understand it):

  PATH_POISONING
  --------------
  For each event we pick a random victim prefix and origin from the
  legitimate announcements, a random attacker AS with RPKI observers,
  and a third AS that has no CAIDA relationship to the attacker.  The
  crafted as_path is [attacker, phantom_no_rel_AS, victim_origin].
  Consecutive adjacency (attacker, phantom) has no CAIDA edge → the
  detector fires.

  ROUTE_LEAK (valley-free violation)
  ----------------------------------
  We pick a customer AS with at least one provider and at least one
  peer (call them P and R).  The crafted as_path is
  [observer, P, customer, R, origin].  Here `customer` receives the
  route from its provider P and re-announces it to its peer R — a
  textbook valley-free violation.  The detector fires at the (P,
  customer, R) triple.

Observer assignment:
  Each injected event is observed by K random RPKI validators where
  K = max(3, sqrt(N_rpki)).  K scales sublinearly with network size,
  approximating realistic BGP propagation to a subset of observers.

Timestamps:
  Spread uniformly across the SIM_DURATION window so injections mix
  with legitimate traffic.

Usage:
  python3 scripts/inject_attacks.py caida_50  [--events-per-type 2]
  python3 scripts/inject_attacks.py all
"""
import argparse
import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# Events per type per dataset (matches the revise_dataset.py schedule)
EVENTS_PER_TYPE_DEFAULT = {
    "caida_50":   2,
    "caida_100":  4,
    "caida_200":  8,
    "caida_400":  16,
    "caida_800":  32,
    "caida_1600": 64,
}


def load_as_relationships(base: Path) -> dict:
    """Load the CAIDA AS-relationship dictionary produced by
    scripts/build_as_relationships.py (lives in
    blockchain_data/state/ after a run).  Fall back to dataset
    directory if not present."""
    candidates = [
        base / "blockchain_data" / "state" / "as_relationships.json",
        base / "dataset" / "state" / "as_relationships.json",
    ]
    for c in candidates:
        if c.exists():
            with open(c) as f:
                return json.load(f)
    raise FileNotFoundError(
        "as_relationships.json not found — run build_as_relationships.py first"
    )


def find_no_relationship_as(target_as: int, relationships: dict,
                             exclude: set[int], tried_limit: int = 200) -> int | None:
    """Find an AS that has no documented relationship with target_as.
    Returns the ASN or None if not found."""
    target_str = str(target_as)
    target_rels = relationships.get(target_str, {})
    forbidden = set()
    for key in ("customers", "providers", "peers"):
        forbidden.update(target_rels.get(key, []))
    forbidden.add(target_as)
    forbidden.update(exclude)

    candidates = [int(k) for k in relationships.keys() if int(k) not in forbidden]
    random.shuffle(candidates)
    # Double-check symmetric: candidate must also not have target in its neighborhood
    for cand in candidates[:tried_limit]:
        cand_rels = relationships.get(str(cand), {})
        cand_neighbors = (
            set(cand_rels.get("customers", []))
            | set(cand_rels.get("providers", []))
            | set(cand_rels.get("peers", []))
        )
        if target_as not in cand_neighbors:
            return cand
    return None


def find_customer_with_provider_and_peer(relationships: dict) -> tuple[int, int, int] | None:
    """Return (customer_as, provider_as, peer_as) that supports a valley-free leak."""
    keys = list(relationships.keys())
    random.shuffle(keys)
    for k in keys:
        rels = relationships[k]
        providers = rels.get("providers", [])
        peers = rels.get("peers", [])
        if providers and peers:
            return int(k), int(random.choice(providers)), int(random.choice(peers))
    return None


def load_observation_files(obs_dir: Path) -> dict[Path, dict]:
    """Load every AS*.json; return mapping file → full json dict."""
    out = {}
    for f in sorted(obs_dir.glob("AS*.json")):
        with open(f) as fh:
            out[f] = json.load(fh)
    return out


def pick_victim_origin_prefix(all_files: dict[Path, dict]) -> tuple[int, str]:
    """Pick a random legit (origin_asn, prefix) from the dataset."""
    for f, data in all_files.items():
        legit = [o for o in data.get("observations", [])
                 if not o.get("is_attack") and o.get("origin_asn") and o.get("prefix")]
        if legit:
            o = random.choice(legit)
            return o["origin_asn"], o["prefix"]
    raise RuntimeError("No legit observation to clone prefix/origin from")


def make_observation_template(observer_asn: int, attack_type: str,
                               prefix: str, origin_asn: int,
                               as_path: list[int], timestamp: float) -> dict:
    """Build a BGP UPDATE-shaped observation matching the dataset format."""
    return {
        "prefix": prefix,
        "origin_asn": origin_asn,
        "as_path": as_path,
        "as_path_length": len(as_path),
        "next_hop_asn": as_path[1] if len(as_path) > 1 else origin_asn,
        "timestamp": timestamp,
        "timestamp_readable": datetime.fromtimestamp(timestamp).isoformat(sep=" "),
        "recv_relationship": "PEERS",
        "origin_type": "ATTACKER",
        "label": attack_type,
        "is_attack": True,
        "bgp_update": {
            "type": "UPDATE",
            "withdrawn_routes": [],
            "path_attributes": {
                "ORIGIN": "INCOMPLETE",
                "AS_PATH": as_path[1:] if as_path and as_path[0] == observer_asn else as_path,
                "NEXT_HOP": as_path[1] if len(as_path) > 1 else origin_asn,
                "LOCAL_PREF": 100,
                "MED": 20,
                "COMMUNITIES": [f"{origin_asn}:999"],
            },
            "nlri": [prefix],
        },
        "communities": [f"{origin_asn}:999"],
        "is_withdrawal": False,
        "observed_by_asn": observer_asn,
        "observer_is_rpki": True,
        "hop_distance": len(as_path) - 1,
        "relayed_by_asn": as_path[1] if len(as_path) > 1 else None,
        "is_best": True,
        "_injected": True,  # provenance flag
    }


def inject_for_dataset(dataset_name: str, events_per_type: int, base: Path):
    ds = base / "dataset" / dataset_name
    obs_dir = ds / "observations"
    gt_path = ds / "ground_truth" / "ground_truth.json"

    # Load CAIDA relationships produced by build_as_relationships.py
    try:
        relationships = load_as_relationships(base)
    except FileNotFoundError as e:
        print(f"  ❌ {dataset_name}: {e}")
        print(f"     Run: python3 scripts/build_as_relationships.py dataset/{dataset_name}")
        return False

    # Load AS classification to find RPKI observers
    as_class_path = ds / "as_classification.json"
    with open(as_class_path) as f:
        as_class = json.load(f)
    rpki_nodes = [int(a) for a, v in as_class.get("as_classification", as_class).items()
                  if isinstance(v, dict) and v.get("is_rpki_node")]
    if not rpki_nodes:
        # Different format — observer list is in observation files themselves
        rpki_nodes = [int(f.stem.replace("AS", "")) for f in obs_dir.glob("AS*.json")]

    # Load all observations to find victims and anchor timestamps
    all_files = load_observation_files(obs_dir)
    all_obs = [o for data in all_files.values() for o in data.get("observations", [])]
    if not all_obs:
        print(f"  ❌ {dataset_name}: no observations found")
        return False

    timestamps = [o["timestamp"] for o in all_obs if "timestamp" in o]
    ts_min, ts_max = min(timestamps), max(timestamps)

    # How many observers per event — sqrt of RPKI count
    k_observers = max(3, int(math.sqrt(len(rpki_nodes))))

    injected_path_poisoning = 0
    injected_route_leak = 0
    per_file_new: dict[Path, list[dict]] = defaultdict(list)

    file_by_asn = {int(f.stem.replace("AS", "")): f for f in all_files.keys()}

    # ── PATH_POISONING injection
    random.seed(f"path_poisoning_{dataset_name}")
    for i in range(events_per_type):
        # Pick an attacker AS (any RPKI node, for realism — could also be non-RPKI)
        attacker = random.choice(rpki_nodes)
        # Find an AS with no relationship to the attacker.  Only exclude
        # attacker self; any other AS (RPKI or not) is a valid phantom as
        # long as the detector sees no CAIDA edge.
        phantom = find_no_relationship_as(attacker, relationships, exclude=set())
        if phantom is None:
            continue
        victim_origin, victim_prefix = pick_victim_origin_prefix(all_files)
        if victim_origin == attacker or victim_origin == phantom:
            continue

        # Timestamp spread uniformly across sim window
        ts = ts_min + (ts_max - ts_min) * (i + 1) / (events_per_type + 1)

        # Pick K observers (different from attacker/phantom/origin)
        pool = [a for a in rpki_nodes if a not in (attacker, phantom, victim_origin)]
        observers = random.sample(pool, min(k_observers, len(pool)))

        for obs_asn in observers:
            if obs_asn not in file_by_asn:
                continue
            as_path = [obs_asn, attacker, phantom, victim_origin]
            obs = make_observation_template(
                obs_asn, "PATH_POISONING", victim_prefix, victim_origin,
                as_path, ts + random.uniform(-2, 2),
            )
            per_file_new[file_by_asn[obs_asn]].append(obs)
            injected_path_poisoning += 1

    # ── ROUTE_LEAK injection (valley-free)
    random.seed(f"route_leak_{dataset_name}")
    for i in range(events_per_type):
        triple = find_customer_with_provider_and_peer(relationships)
        if triple is None:
            continue
        leaker, provider, peer_r = triple
        victim_origin, victim_prefix = pick_victim_origin_prefix(all_files)
        if victim_origin in (leaker, provider, peer_r):
            continue

        ts = ts_min + (ts_max - ts_min) * (i + 1) / (events_per_type + 1)

        pool = [a for a in rpki_nodes if a not in (leaker, provider, peer_r, victim_origin)]
        observers = random.sample(pool, min(k_observers, len(pool)))

        for obs_asn in observers:
            if obs_asn not in file_by_asn:
                continue
            # Path: observer ← peer_r ← leaker ← provider ← origin
            # i.e. leaker received from provider (upstream), leaked to peer_r (sibling)
            # Detector scans as_path; (provider, leaker, peer_r) triple is the violation
            as_path = [obs_asn, peer_r, leaker, provider, victim_origin]
            obs = make_observation_template(
                obs_asn, "ROUTE_LEAK", victim_prefix, victim_origin,
                as_path, ts + random.uniform(-2, 2),
            )
            per_file_new[file_by_asn[obs_asn]].append(obs)
            injected_route_leak += 1

    # Write back: append to each file's observations, update counts
    for f, data in all_files.items():
        new_obs = per_file_new.get(f, [])
        if not new_obs:
            continue
        data["observations"].extend(new_obs)
        data["observations"].sort(key=lambda o: o.get("timestamp", 0))
        data["total_observations"] = len(data["observations"])
        data["attack_observations"] = sum(1 for o in data["observations"] if o.get("is_attack"))
        data["legitimate_observations"] = data["total_observations"] - data["attack_observations"]
        with open(f, "w") as fh:
            json.dump(data, fh, indent=2)

    # Update ground_truth
    if gt_path.exists():
        with open(gt_path) as fh:
            gt = json.load(fh)
        # Recount from files
        per_type: dict[str, int] = defaultdict(int)
        total_attacks = 0
        attacks_list = []
        for f, data in all_files.items():
            with open(f) as fh:
                data = json.load(fh)   # re-read to pick up writes
            for o in data.get("observations", []):
                if o.get("is_attack"):
                    per_type[o.get("label", "UNKNOWN")] += 1
                    total_attacks += 1
                    if o.get("_injected"):
                        attacks_list.append({
                            "timestamp": o.get("timestamp"),
                            "prefix": o.get("prefix"),
                            "origin_asn": o.get("origin_asn"),
                            "as_path": o.get("as_path"),
                            "attack_type": o.get("label"),
                            "observed_by_asn": o.get("observed_by_asn"),
                            "synthetic": True,
                        })
        gt["total_attacks"] = total_attacks
        gt["attack_types"] = dict(per_type)
        # Append synthetic entries to existing attacks list
        existing = gt.get("attacks", [])
        existing.extend(attacks_list)
        gt["attacks"] = existing
        gt.setdefault("_injection", {})
        gt["_injection"][datetime.now().isoformat()] = {
            "events_per_type": events_per_type,
            "path_poisoning_observations_added": injected_path_poisoning,
            "route_leak_observations_added": injected_route_leak,
            "observers_per_event": k_observers,
            "script": "scripts/inject_attacks.py",
        }
        with open(gt_path, "w") as fh:
            json.dump(gt, fh, indent=2)

    print(f"  ✅ {dataset_name}: injected {injected_path_poisoning} PATH_POISONING "
          f"obs + {injected_route_leak} ROUTE_LEAK obs ({events_per_type} events/type, "
          f"~{k_observers} observers/event)")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("target")
    p.add_argument("--events-per-type", type=int, default=None,
                   help="Override events-per-type (default uses per-dataset schedule)")
    args = p.parse_args()

    base = Path(__file__).resolve().parent.parent

    targets = (
        ["caida_50", "caida_100", "caida_200", "caida_400", "caida_800", "caida_1600"]
        if args.target == "all" else [args.target]
    )
    for name in targets:
        n = args.events_per_type if args.events_per_type is not None else EVENTS_PER_TYPE_DEFAULT.get(name, 4)
        inject_for_dataset(name, n, base)


if __name__ == "__main__":
    main()
