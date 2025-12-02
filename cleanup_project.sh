#!/bin/bash
# Clean redundant/outdated documentation files

echo "🧹 Cleaning Redundant Documentation Files..."
echo ""
echo "Files to remove (redundant/outdated):"
echo "  - QUICK_TEST.md (superseded by HOW_TO_RUN_EXPERIMENTS.md)"
echo "  - ATTACK_EXPERIMENT_QUICKSTART.md (superseded by HOW_TO_RUN_EXPERIMENTS.md)"
echo "  - FINAL_SETUP_GUIDE.md (superseded by HOW_TO_RUN_EXPERIMENTS.md)"
echo "  - EXPERIMENT_FEATURES_SUMMARY.md (information in ARCHITECTURE_DETAILS.md)"
echo "  - IMPLEMENTATION_COMPLETE.md (outdated status file)"
echo "  - UPDATES_SUMMARY.md (outdated status file)"
echo "  - README_TESTING.md (testing info in HOW_TO_RUN_EXPERIMENTS.md)"
echo "  - WEEKLY_PRESENTATION_NOTES.md (temporary notes)"
echo ""
read -p "Remove these files? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    rm -f QUICK_TEST.md
    rm -f ATTACK_EXPERIMENT_QUICKSTART.md
    rm -f FINAL_SETUP_GUIDE.md
    rm -f EXPERIMENT_FEATURES_SUMMARY.md
    rm -f IMPLEMENTATION_COMPLETE.md
    rm -f UPDATES_SUMMARY.md
    rm -f README_TESTING.md
    rm -f WEEKLY_PRESENTATION_NOTES.md
    echo "✅ Removed 8 redundant documentation files"
else
    echo "❌ Cancelled - no files removed"
fi
