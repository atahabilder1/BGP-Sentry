#!/usr/bin/env python3
"""
=============================================================================
Initialize Non-RPKI AS Ratings
=============================================================================

Purpose: Initialize all non-RPKI ASes with random ratings between 80-85
         This gives them a "good" starting reputation that can change
         based on their behavior over time.

Author: BGP-Sentry Team
=============================================================================
"""

import json
import random
from pathlib import Path
from datetime import datetime


class RatingInitializer:
    """Initialize ratings for non-RPKI ASes"""

    def __init__(self, project_root: str = None):
        """Initialize the rating initializer"""
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = Path(__file__).parent.parent.parent.parent.parent

        self.rpki_nodes_dir = self.project_root / "nodes/rpki_nodes"

        print("🎲 Rating Initializer")
        print("=" * 80)
        print(f"Project Root: {self.project_root}")
        print()

    def get_non_rpki_ases(self) -> list:
        """Get list of non-RPKI AS numbers"""
        # Common non-RPKI test ASes
        # You can customize this list based on your setup
        non_rpki_ases = [666, 31337, 100, 200, 300, 400, 500, 600, 700, 800]

        print(f"📋 Non-RPKI ASes to initialize: {non_rpki_ases}")
        print()

        return non_rpki_ases

    def generate_initial_rating(self) -> dict:
        """Generate random initial rating between 80-85"""
        # Random rating between 80 and 85
        rating = random.uniform(80.0, 85.0)

        # Determine rating level
        if rating >= 84:
            level = "excellent"
        elif rating >= 82:
            level = "good"
        else:
            level = "good"  # Still good, just lower end

        return {
            "trust_score": round(rating, 2),
            "rating_level": level,
            "attacks_detected": 0,
            "good_announcements": 0,
            "bad_announcements": 0,
            "last_updated": datetime.now().isoformat(),
            "initialized": True,
            "initial_rating": round(rating, 2)
        }

    def initialize_ratings_for_all_nodes(self, non_rpki_ases: list):
        """Initialize ratings on all RPKI blockchain nodes"""

        rpki_nodes = ["as01", "as03", "as05", "as07", "as09", "as11", "as13", "as15", "as17"]

        print("🔧 Initializing ratings on all RPKI nodes...")
        print()

        for node in rpki_nodes:
            rating_file = (
                self.rpki_nodes_dir /
                node /
                "blockchain_node/blockchain_data/state/nonrpki_ratings.json"
            )

            # Create directory if doesn't exist
            rating_file.parent.mkdir(parents=True, exist_ok=True)

            # Generate ratings for all non-RPKI ASes
            as_ratings = {}

            for as_num in non_rpki_ases:
                as_ratings[str(as_num)] = self.generate_initial_rating()

            # Create rating data structure
            rating_data = {
                "last_updated": datetime.now().isoformat(),
                "as_ratings": as_ratings,
                "total_non_rpki_ases": len(non_rpki_ases),
                "initialized": True,
                "initialization_timestamp": datetime.now().isoformat()
            }

            # Save to file
            with open(rating_file, 'w') as f:
                json.dump(rating_data, f, indent=2)

            print(f"   ✅ {node}: Initialized {len(non_rpki_ases)} AS ratings")

        print()
        print(f"✅ All RPKI nodes initialized with non-RPKI ratings")
        print()

    def display_initialized_ratings(self, non_rpki_ases: list):
        """Display the initialized ratings"""

        # Read from first node as sample
        rating_file = (
            self.rpki_nodes_dir /
            "as01/blockchain_node/blockchain_data/state/nonrpki_ratings.json"
        )

        if not rating_file.exists():
            print("⚠️  Rating file not found")
            return

        with open(rating_file, 'r') as f:
            rating_data = json.load(f)

        print("=" * 80)
        print("📊 INITIALIZED RATINGS (Sample from as01)")
        print("=" * 80)
        print()

        print(f"{'AS Number':<12} {'Initial Rating':<15} {'Level':<15}")
        print("-" * 42)

        for as_num in sorted(non_rpki_ases):
            as_data = rating_data["as_ratings"].get(str(as_num), {})
            rating = as_data.get("trust_score", 0)
            level = as_data.get("rating_level", "unknown")

            emoji = "🟢" if rating >= 80 else "🟡"

            print(f"AS{as_num:<10} {rating:<15.2f} {emoji} {level:<15}")

        print()
        print(f"📊 Rating Range: 80.00 - 85.00 (All start with good reputation)")
        print(f"📊 Total ASes: {len(non_rpki_ases)}")
        print()

    def run(self):
        """Run the initialization"""

        print("=" * 80)
        print("🎲 INITIALIZING NON-RPKI AS RATINGS")
        print("=" * 80)
        print()

        print("This will:")
        print("   • Set all non-RPKI ASes to random ratings between 80-85")
        print("   • Give them a 'good' initial reputation")
        print("   • Ratings will adjust based on behavior over time")
        print()

        response = input("Continue? (y/n): ").lower().strip()

        if response != 'y':
            print("Initialization cancelled.")
            return

        print()

        # Get non-RPKI ASes
        non_rpki_ases = self.get_non_rpki_ases()

        # Initialize ratings
        self.initialize_ratings_for_all_nodes(non_rpki_ases)

        # Display results
        self.display_initialized_ratings(non_rpki_ases)

        print("=" * 80)
        print("✅ INITIALIZATION COMPLETE")
        print("=" * 80)
        print()

        print("💡 Next Steps:")
        print("   1. Ratings are now initialized (80-85 range)")
        print("   2. Run your attack experiment:")
        print("      python3 run_complete_test.py")
        print("   3. Ratings will adjust based on behavior")
        print()


def main():
    """Main entry point"""
    initializer = RatingInitializer()
    initializer.run()


if __name__ == "__main__":
    main()
