#!/usr/bin/env python3
"""
DatasetLoader - Reads CAIDA datasets for BGP-Sentry experiments.

Loads as_classification.json, observation files, and ground truth to
provide a clean in-memory representation of the entire dataset.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Loads a CAIDA dataset directory and provides access to all AS data.

    Expected directory structure:
        dataset_path/
            as_classification.json
            observations/AS<N>.json ...
            ground_truth/ground_truth.json
    """

    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self._classification: Dict = {}
        self._observations: Dict[int, List[dict]] = {}  # ASN -> list of observations
        self._ground_truth: Dict = {}
        self._all_asns: Set[int] = set()
        self._rpki_asns: Set[int] = set()
        self._non_rpki_asns: Set[int] = set()
        self._legitimate_prefixes: Set[Tuple[str, int]] = set()  # (prefix, origin_asn)

        self._load()

    def _load(self):
        """Load all dataset files."""
        self._load_classification()
        self._load_observations()
        self._load_ground_truth()
        logger.info(
            f"Dataset loaded: {self.dataset_path.name} - "
            f"{len(self._all_asns)} ASes, "
            f"{sum(len(v) for v in self._observations.values())} total observations"
        )

    def _load_classification(self):
        """Load as_classification.json."""
        cls_file = self.dataset_path / "as_classification.json"
        if not cls_file.exists():
            raise FileNotFoundError(f"as_classification.json not found in {self.dataset_path}")

        with open(cls_file, "r") as f:
            self._classification = json.load(f)

        self._rpki_asns = set(self._classification.get("rpki_asns", []))
        self._non_rpki_asns = set(self._classification.get("non_rpki_asns", []))
        self._all_asns = self._rpki_asns | self._non_rpki_asns

    def _load_observations(self):
        """Load per-AS observation files."""
        obs_dir = self.dataset_path / "observations"
        if not obs_dir.exists():
            logger.warning(f"Observations directory not found: {obs_dir}")
            return

        for obs_file in sorted(obs_dir.glob("AS*.json")):
            try:
                with open(obs_file, "r") as f:
                    data = json.load(f)

                asn = data.get("asn")
                if asn is None:
                    continue

                observations = data.get("observations", [])
                self._observations[asn] = observations

                # Track legitimate prefixes
                for obs in observations:
                    if not obs.get("is_attack"):
                        prefix = obs.get("prefix")
                        origin = obs.get("origin_asn")
                        if prefix and origin:
                            self._legitimate_prefixes.add((prefix, origin))

            except Exception as e:
                logger.warning(f"Failed to load {obs_file}: {e}")

    def _load_ground_truth(self):
        """Load ground truth labels."""
        gt_file = self.dataset_path / "ground_truth" / "ground_truth.json"
        if gt_file.exists():
            with open(gt_file, "r") as f:
                self._ground_truth = json.load(f)
        else:
            logger.warning(f"Ground truth not found: {gt_file}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_all_asns(self) -> List[int]:
        """Get sorted list of all AS numbers in the dataset."""
        return sorted(self._all_asns)

    def get_rpki_asns(self) -> List[int]:
        """Get sorted list of RPKI AS numbers."""
        return sorted(self._rpki_asns)

    def get_non_rpki_asns(self) -> List[int]:
        """Get sorted list of non-RPKI AS numbers."""
        return sorted(self._non_rpki_asns)

    def get_observations_for_asn(self, asn: int) -> List[dict]:
        """Get all observations for a specific ASN."""
        return self._observations.get(asn, [])

    def get_all_observations(self) -> Dict[int, List[dict]]:
        """Get observations dict: ASN -> list of observations."""
        return dict(self._observations)

    def get_legitimate_prefixes(self) -> Set[Tuple[str, int]]:
        """Get set of (prefix, origin_asn) pairs from legitimate observations."""
        return set(self._legitimate_prefixes)

    def get_ground_truth(self) -> Dict:
        """Get ground truth data."""
        return dict(self._ground_truth)

    def get_ground_truth_attacks(self) -> List[dict]:
        """Get list of attack entries from ground truth."""
        return self._ground_truth.get("attacks", [])

    def get_classification(self) -> Dict:
        """Get the full classification dict."""
        return dict(self._classification)

    def get_role(self, asn: int) -> str:
        """Get blockchain role for an ASN."""
        roles = self._classification.get("rpki_role", {})
        return roles.get(str(asn), "unknown")

    def is_rpki(self, asn: int) -> bool:
        """Check if ASN is RPKI."""
        return asn in self._rpki_asns

    @property
    def dataset_name(self) -> str:
        """Return dataset directory name (e.g. 'caida_100')."""
        return self.dataset_path.name

    @property
    def total_ases(self) -> int:
        return len(self._all_asns)

    @property
    def rpki_count(self) -> int:
        return len(self._rpki_asns)

    @property
    def non_rpki_count(self) -> int:
        return len(self._non_rpki_asns)

    def summary(self) -> dict:
        """Return a summary dict of the loaded dataset."""
        total_obs = sum(len(v) for v in self._observations.values())
        attack_obs = sum(
            1
            for obs_list in self._observations.values()
            for obs in obs_list
            if obs.get("is_attack")
        )
        return {
            "dataset_name": self.dataset_name,
            "dataset_path": str(self.dataset_path),
            "total_ases": self.total_ases,
            "rpki_count": self.rpki_count,
            "non_rpki_count": self.non_rpki_count,
            "total_observations": total_obs,
            "attack_observations": attack_obs,
            "legitimate_observations": total_obs - attack_obs,
            "ground_truth_attacks": len(self.get_ground_truth_attacks()),
        }
