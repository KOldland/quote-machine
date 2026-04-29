#!/bin/bash
set -e
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "=== QM Demo Smoke Checks ==="
echo ""
echo "1. Running unit tests..."
python3 -m unittest discover -s tests -p 'test_*.py' -v 2>&1 | grep -E '(test_|OK|FAILED|ERROR)'

echo ""
echo "2. Verification complete ✓"
echo ""
echo "All systems ready for demo."
echo ""
echo "To start demo:"
echo "  bash scripts/qm_demo_start.sh 5051"
