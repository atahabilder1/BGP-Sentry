#!/usr/bin/env python3
"""
=============================================================================
BGP-Sentry Configuration Loader
=============================================================================

Reads tunable hyperparameters from the project-root .env file so that
every module gets a single, consistent set of values.

Usage in any module:
    from config import cfg
    timeout = cfg.P2P_REGULAR_TIMEOUT
=============================================================================
"""

import os
from pathlib import Path

# Locate the .env file (project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # …/BGP-Sentry
_ENV_FILE = _PROJECT_ROOT / ".env"

# Load .env into os.environ (will NOT override existing env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(_ENV_FILE, override=False)
except ImportError:
    # Fallback: parse .env manually
    if _ENV_FILE.exists():
        with open(_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


class _Config:
    """Singleton holding every tunable parameter."""

    # ── Consensus ──────────────────────────────────────────────────
    CONSENSUS_MIN_SIGNATURES: int = _int("CONSENSUS_MIN_SIGNATURES", 3)
    CONSENSUS_CAP_SIGNATURES: int = _int("CONSENSUS_CAP_SIGNATURES", 5)

    # ── P2P Network ────────────────────────────────────────────────
    P2P_REGULAR_TIMEOUT: int = _int("P2P_REGULAR_TIMEOUT", 30)
    P2P_ATTACK_TIMEOUT: int = _int("P2P_ATTACK_TIMEOUT", 60)
    P2P_MAX_BROADCAST_PEERS: int = _int("P2P_MAX_BROADCAST_PEERS", 10)
    P2P_BASE_PORT: int = _int("P2P_BASE_PORT", 8000)

    # ── Deduplication & Sampling ──────────────────────────────────
    RPKI_DEDUP_WINDOW: int = _int("RPKI_DEDUP_WINDOW", 3600)
    NONRPKI_DEDUP_WINDOW: int = _int("NONRPKI_DEDUP_WINDOW", 10)
    SAMPLING_WINDOW_SECONDS: int = _int("SAMPLING_WINDOW_SECONDS", 3600)

    # ── Knowledge Base ────────────────────────────────────────────
    KNOWLEDGE_WINDOW_SECONDS: int = _int("KNOWLEDGE_WINDOW_SECONDS", 480)
    KNOWLEDGE_CLEANUP_INTERVAL: int = _int("KNOWLEDGE_CLEANUP_INTERVAL", 60)

    # ── Buffer Capacity Limits ──────────────────────────────────
    PENDING_VOTES_MAX_CAPACITY: int = _int("PENDING_VOTES_MAX_CAPACITY", 5000)
    COMMITTED_TX_MAX_SIZE: int = _int("COMMITTED_TX_MAX_SIZE", 50000)
    COMMITTED_TX_CLEANUP_INTERVAL: int = _int("COMMITTED_TX_CLEANUP_INTERVAL", 300)
    KNOWLEDGE_BASE_MAX_SIZE: int = _int("KNOWLEDGE_BASE_MAX_SIZE", 50000)
    LAST_SEEN_CACHE_MAX_SIZE: int = _int("LAST_SEEN_CACHE_MAX_SIZE", 100000)

    # ── Attack Detection — Route Flapping ─────────────────────────
    FLAP_WINDOW_SECONDS: int = _int("FLAP_WINDOW_SECONDS", 60)
    FLAP_THRESHOLD: int = _int("FLAP_THRESHOLD", 5)
    FLAP_DEDUP_SECONDS: int = _int("FLAP_DEDUP_SECONDS", 2)

    # ── BGPCOIN Economy ───────────────────────────────────────────
    BGPCOIN_TOTAL_SUPPLY: int = _int("BGPCOIN_TOTAL_SUPPLY", 10_000_000)

    BGPCOIN_REWARD_BLOCK_COMMIT: float = _float("BGPCOIN_REWARD_BLOCK_COMMIT", 10)
    BGPCOIN_REWARD_VOTE_APPROVE: float = _float("BGPCOIN_REWARD_VOTE_APPROVE", 1)
    BGPCOIN_REWARD_FIRST_COMMIT_BONUS: float = _float("BGPCOIN_REWARD_FIRST_COMMIT_BONUS", 5)
    BGPCOIN_REWARD_ATTACK_DETECTION: float = _float("BGPCOIN_REWARD_ATTACK_DETECTION", 100)
    BGPCOIN_REWARD_DAILY_MONITORING: float = _float("BGPCOIN_REWARD_DAILY_MONITORING", 10)

    BGPCOIN_PENALTY_FALSE_REJECT: float = _float("BGPCOIN_PENALTY_FALSE_REJECT", 2)
    BGPCOIN_PENALTY_FALSE_APPROVE: float = _float("BGPCOIN_PENALTY_FALSE_APPROVE", 5)
    BGPCOIN_PENALTY_MISSED_PARTICIPATION: float = _float("BGPCOIN_PENALTY_MISSED_PARTICIPATION", 1)

    BGPCOIN_MULTIPLIER_ACCURACY_MIN: float = _float("BGPCOIN_MULTIPLIER_ACCURACY_MIN", 0.5)
    BGPCOIN_MULTIPLIER_ACCURACY_MAX: float = _float("BGPCOIN_MULTIPLIER_ACCURACY_MAX", 1.5)
    BGPCOIN_MULTIPLIER_PARTICIPATION_MIN: float = _float("BGPCOIN_MULTIPLIER_PARTICIPATION_MIN", 0.8)
    BGPCOIN_MULTIPLIER_PARTICIPATION_MAX: float = _float("BGPCOIN_MULTIPLIER_PARTICIPATION_MAX", 1.2)
    BGPCOIN_MULTIPLIER_QUALITY_MIN: float = _float("BGPCOIN_MULTIPLIER_QUALITY_MIN", 0.9)
    BGPCOIN_MULTIPLIER_QUALITY_MAX: float = _float("BGPCOIN_MULTIPLIER_QUALITY_MAX", 1.3)

    # ── Non-RPKI Trust Rating ─────────────────────────────────────
    RATING_INITIAL_SCORE: int = _int("RATING_INITIAL_SCORE", 50)
    RATING_MIN_SCORE: int = _int("RATING_MIN_SCORE", 0)
    RATING_MAX_SCORE: int = _int("RATING_MAX_SCORE", 100)

    RATING_PENALTY_PREFIX_HIJACK: int = _int("RATING_PENALTY_PREFIX_HIJACK", -20)
    RATING_PENALTY_SUBPREFIX_HIJACK: int = _int("RATING_PENALTY_SUBPREFIX_HIJACK", -18)
    RATING_PENALTY_BOGON_INJECTION: int = _int("RATING_PENALTY_BOGON_INJECTION", -25)
    RATING_PENALTY_ROUTE_FLAPPING: int = _int("RATING_PENALTY_ROUTE_FLAPPING", -10)
    RATING_PENALTY_ROUTE_LEAK: int = _int("RATING_PENALTY_ROUTE_LEAK", -15)
    RATING_PENALTY_REPEATED_ATTACK: int = _int("RATING_PENALTY_REPEATED_ATTACK", -30)
    RATING_PENALTY_PERSISTENT_ATTACKER: int = _int("RATING_PENALTY_PERSISTENT_ATTACKER", -50)

    RATING_REWARD_MONTHLY_GOOD_BEHAVIOR: int = _int("RATING_REWARD_MONTHLY_GOOD_BEHAVIOR", 5)
    RATING_REWARD_FALSE_ACCUSATION_CLEARED: int = _int("RATING_REWARD_FALSE_ACCUSATION_CLEARED", 2)
    RATING_REWARD_PER_100_LEGITIMATE: int = _int("RATING_REWARD_PER_100_LEGITIMATE", 1)
    RATING_REWARD_HIGHLY_TRUSTED_BONUS: int = _int("RATING_REWARD_HIGHLY_TRUSTED_BONUS", 10)

    RATING_THRESHOLD_HIGHLY_TRUSTED: int = _int("RATING_THRESHOLD_HIGHLY_TRUSTED", 90)
    RATING_THRESHOLD_TRUSTED: int = _int("RATING_THRESHOLD_TRUSTED", 70)
    RATING_THRESHOLD_NEUTRAL: int = _int("RATING_THRESHOLD_NEUTRAL", 50)
    RATING_THRESHOLD_SUSPICIOUS: int = _int("RATING_THRESHOLD_SUSPICIOUS", 30)

    # ── Attack Consensus ──────────────────────────────────────────
    ATTACK_CONSENSUS_MIN_VOTES: int = _int("ATTACK_CONSENSUS_MIN_VOTES", 3)
    ATTACK_CONSENSUS_REWARD_DETECTION: float = _float("ATTACK_CONSENSUS_REWARD_DETECTION", 10)
    ATTACK_CONSENSUS_REWARD_CORRECT_VOTE: float = _float("ATTACK_CONSENSUS_REWARD_CORRECT_VOTE", 2)
    ATTACK_CONSENSUS_PENALTY_FALSE_ACCUSATION: float = _float("ATTACK_CONSENSUS_PENALTY_FALSE_ACCUSATION", -20)


# Module-level singleton
cfg = _Config()
