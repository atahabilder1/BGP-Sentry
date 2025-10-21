#!/usr/bin/env python3
"""
=============================================================================
Non-RPKI AS Rating System
=============================================================================

Purpose: Track trust scores for non-RPKI ASes based on behavior

Rating System:
- Initial Score: 50 (neutral)
- Range: 0-100
- Score updated based on attacks and good behavior

Score Updates:
GOOD BEHAVIOR:
  + 5 per month (no attacks detected)
  + 2 if falsely accused (proven innocent via consensus)
  + 1 per 100 legitimate announcements
  + 10 bonus at score 90+ for 3 consecutive months

BAD BEHAVIOR:
  - 20 per confirmed IP prefix hijacking
  - 15 per confirmed route leak
  - 30 for repeated attack (within 30 days)
  - 50 for persistent attacker (3+ attacks total)

Score Ranges:
  90-100: Highly Trusted (nearly RPKI-level, consider adding ROA)
  70-89:  Trusted (good track record)
  50-69:  Neutral (new or mixed history)
  30-49:  Suspicious (some attacks detected)
  0-29:   Malicious (confirmed attacker, block/filter)

Author: BGP-Sentry Team
=============================================================================
"""

import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class NonRPKIRatingSystem:
    """
    Manages trust scores for non-RPKI autonomous systems.

    Tracks behavior over time and adjusts ratings based on:
    - Confirmed attacks (decrease score)
    - Good behavior (increase score)
    - False accusations (restore score)
    """

    def __init__(self, rating_path="blockchain_data/state"):
        """
        Initialize non-RPKI rating system.

        Args:
            rating_path: Path to store rating data
        """
        self.rating_dir = Path(rating_path)
        self.ratings_file = self.rating_dir / "nonrpki_ratings.json"
        self.history_file = self.rating_dir / "rating_history.jsonl"

        # Thread safety
        self.lock = threading.RLock()

        # Rating configuration
        self.initial_score = 50  # Neutral starting point
        self.score_min = 0
        self.score_max = 100

        # Score change amounts
        self.penalties = {
            "ip_prefix_hijacking": -20,
            "route_leak": -15,
            "repeated_attack": -30,      # Additional penalty for attack within 30 days
            "persistent_attacker": -50    # 3+ total attacks
        }

        self.rewards = {
            "monthly_good_behavior": 5,
            "false_accusation_cleared": 2,
            "legitimate_announcements_100": 1,
            "highly_trusted_bonus": 10    # Bonus for 90+ score for 3 months
        }

        # Score thresholds
        self.thresholds = {
            "highly_trusted": 90,
            "trusted": 70,
            "neutral": 50,
            "suspicious": 30,
            "malicious": 0
        }

        # Rating data
        self.ratings_data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "as_ratings": {}  # as_number -> rating_info
        }

        # Load existing ratings
        self._load_ratings()

    def _load_ratings(self):
        """Load rating data from disk"""
        try:
            if self.ratings_file.exists():
                with open(self.ratings_file, 'r') as f:
                    loaded = json.load(f)
                    self.ratings_data.update(loaded)
                print(f"📊 Loaded ratings for {len(self.ratings_data['as_ratings'])} non-RPKI ASes")
            else:
                print(f"📊 Initializing new non-RPKI rating system")

        except Exception as e:
            print(f"Error loading ratings: {e}")

    def _save_ratings(self):
        """Save rating data to disk"""
        try:
            with self.lock:
                self.ratings_data["last_updated"] = datetime.now().isoformat()

                # Atomic write
                temp_file = self.ratings_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(self.ratings_data, f, indent=2)
                temp_file.replace(self.ratings_file)

        except Exception as e:
            print(f"Error saving ratings: {e}")

    def _log_rating_change(self, as_number: int, old_score: float, new_score: float,
                          reason: str, details: Dict = None):
        """Log rating change to history file"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "as_number": as_number,
                "old_score": old_score,
                "new_score": new_score,
                "change": new_score - old_score,
                "reason": reason,
                "details": details or {}
            }

            with open(self.history_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            print(f"Error logging rating change: {e}")

    def get_or_create_rating(self, as_number: int) -> Dict:
        """
        Get rating for AS, create if doesn't exist.

        Args:
            as_number: AS number

        Returns:
            Rating info dict
        """
        with self.lock:
            as_str = str(as_number)

            if as_str not in self.ratings_data["as_ratings"]:
                # Create new rating entry
                self.ratings_data["as_ratings"][as_str] = {
                    "as_number": as_number,
                    "trust_score": self.initial_score,
                    "initial_score": self.initial_score,
                    "attacks_detected": 0,
                    "false_accusations": 0,
                    "legitimate_announcements": 0,
                    "last_attack_date": None,
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "rating_level": self._get_rating_level(self.initial_score),
                    "history": []
                }
                self._save_ratings()

            return self.ratings_data["as_ratings"][as_str]

    def _get_rating_level(self, score: float) -> str:
        """Get rating level based on score"""
        if score >= self.thresholds["highly_trusted"]:
            return "highly_trusted"
        elif score >= self.thresholds["trusted"]:
            return "trusted"
        elif score >= self.thresholds["neutral"]:
            return "neutral"
        elif score >= self.thresholds["suspicious"]:
            return "suspicious"
        else:
            return "malicious"

    def record_attack(self, as_number: int, attack_type: str, attack_details: Dict = None) -> Dict:
        """
        Record confirmed attack and update rating.

        Args:
            as_number: AS that committed attack
            attack_type: Type of attack (ip_prefix_hijacking, route_leak)
            attack_details: Additional attack information

        Returns:
            Updated rating info
        """
        try:
            with self.lock:
                rating = self.get_or_create_rating(as_number)
                old_score = rating["trust_score"]

                # Base penalty
                penalty = self.penalties.get(attack_type, -10)

                # Check for repeated attack (within 30 days)
                if rating["last_attack_date"]:
                    last_attack = datetime.fromisoformat(rating["last_attack_date"])
                    if (datetime.now() - last_attack).days <= 30:
                        penalty += self.penalties["repeated_attack"]
                        print(f"⚠️  AS{as_number} repeated attack within 30 days - extra penalty!")

                # Check for persistent attacker (3+ total attacks)
                rating["attacks_detected"] += 1
                if rating["attacks_detected"] >= 3:
                    penalty += self.penalties["persistent_attacker"]
                    print(f"🚨 AS{as_number} is persistent attacker (3+ attacks) - severe penalty!")

                # Apply penalty
                new_score = max(self.score_min, old_score + penalty)
                rating["trust_score"] = new_score
                rating["last_attack_date"] = datetime.now().isoformat()
                rating["last_updated"] = datetime.now().isoformat()
                rating["rating_level"] = self._get_rating_level(new_score)

                # Add to history
                history_entry = {
                    "date": datetime.now().isoformat(),
                    "event": attack_type,
                    "score_change": penalty,
                    "new_score": new_score,
                    "details": attack_details
                }
                rating["history"].append(history_entry)

                # Save and log
                self._save_ratings()
                self._log_rating_change(as_number, old_score, new_score, f"attack_{attack_type}", attack_details)

                print(f"📉 AS{as_number} rating updated:")
                print(f"   Attack: {attack_type}")
                print(f"   Score: {old_score:.1f} → {new_score:.1f} ({penalty:+.1f})")
                print(f"   Level: {rating['rating_level']}")
                print(f"   Total attacks: {rating['attacks_detected']}")

                return rating

        except Exception as e:
            print(f"Error recording attack: {e}")
            return None

    def record_good_behavior(self, as_number: int, behavior_type: str, details: Dict = None) -> Dict:
        """
        Record good behavior and increase rating.

        Args:
            as_number: AS number
            behavior_type: Type of good behavior
            details: Additional information

        Returns:
            Updated rating info
        """
        try:
            with self.lock:
                rating = self.get_or_create_rating(as_number)
                old_score = rating["trust_score"]

                # Determine reward
                reward = self.rewards.get(behavior_type, 1)

                # Apply reward (capped at max score)
                new_score = min(self.score_max, old_score + reward)
                rating["trust_score"] = new_score
                rating["last_updated"] = datetime.now().isoformat()
                rating["rating_level"] = self._get_rating_level(new_score)

                # Add to history
                history_entry = {
                    "date": datetime.now().isoformat(),
                    "event": behavior_type,
                    "score_change": reward,
                    "new_score": new_score,
                    "details": details
                }
                rating["history"].append(history_entry)

                # Save and log
                self._save_ratings()
                self._log_rating_change(as_number, old_score, new_score, f"good_behavior_{behavior_type}", details)

                print(f"📈 AS{as_number} rating improved:")
                print(f"   Behavior: {behavior_type}")
                print(f"   Score: {old_score:.1f} → {new_score:.1f} ({reward:+.1f})")
                print(f"   Level: {rating['rating_level']}")

                return rating

        except Exception as e:
            print(f"Error recording good behavior: {e}")
            return None

    def increment_legitimate_announcements(self, as_number: int):
        """
        Increment legitimate announcement counter.
        Awards bonus every 100 announcements.

        Args:
            as_number: AS number
        """
        try:
            with self.lock:
                rating = self.get_or_create_rating(as_number)
                rating["legitimate_announcements"] += 1

                # Award bonus every 100 legitimate announcements
                if rating["legitimate_announcements"] % 100 == 0:
                    self.record_good_behavior(
                        as_number,
                        "legitimate_announcements_100",
                        {"total_announcements": rating["legitimate_announcements"]}
                    )

        except Exception as e:
            print(f"Error incrementing announcements: {e}")

    def get_rating(self, as_number: int) -> Optional[Dict]:
        """Get rating for AS"""
        return self.ratings_data["as_ratings"].get(str(as_number))

    def get_all_ratings(self) -> Dict:
        """Get all ratings"""
        return self.ratings_data["as_ratings"]

    def get_summary(self) -> Dict:
        """Get summary statistics"""
        ratings = self.ratings_data["as_ratings"]

        summary = {
            "total_ases": len(ratings),
            "by_level": {
                "highly_trusted": 0,
                "trusted": 0,
                "neutral": 0,
                "suspicious": 0,
                "malicious": 0
            },
            "total_attacks": sum(r["attacks_detected"] for r in ratings.values()),
            "average_score": sum(r["trust_score"] for r in ratings.values()) / len(ratings) if ratings else 0
        }

        for rating in ratings.values():
            level = rating["rating_level"]
            summary["by_level"][level] += 1

        return summary


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("NON-RPKI RATING SYSTEM - TEST")
    print("=" * 80)
    print()

    # Initialize rating system
    rating_system = NonRPKIRatingSystem("test_data/state")

    # Test 1: Record attack
    print("🧪 Test 1: Record IP Prefix Hijacking")
    print("-" * 40)
    rating_system.record_attack(
        as_number=666,
        attack_type="ip_prefix_hijacking",
        attack_details={
            "victim_prefix": "8.8.8.0/24",
            "legitimate_owner": 15169
        }
    )
    print()

    # Test 2: Record good behavior
    print("🧪 Test 2: Record Good Behavior")
    print("-" * 40)
    rating_system.record_good_behavior(
        as_number=777,
        behavior_type="monthly_good_behavior"
    )
    print()

    # Test 3: Get summary
    print("🧪 Test 3: Get Summary")
    print("-" * 40)
    summary = rating_system.get_summary()
    print(f"Total ASes: {summary['total_attacks']}")
    print(f"Average Score: {summary['average_score']:.1f}")
    print(f"By Level:")
    for level, count in summary['by_level'].items():
        print(f"  {level}: {count}")
