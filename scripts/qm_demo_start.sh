#!/bin/bash
set -e
PORT="${1:-5051}"
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${DEMO_DIR}/app"

echo "=== QM Demo Startup ==="
echo "Port: $PORT"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"; exit 1
fi

# Create venv
if [ ! -d "${DEMO_DIR}/venv" ]; then
    echo "Creating venv..."
    python3 -m venv "${DEMO_DIR}/venv"
fi

# Activate venv
source "${DEMO_DIR}/venv/bin/activate"

# Install deps
echo "Installing dependencies..."
pip install -q -r "${APP_DIR}/requirements.txt"

# Reset to baseline
echo "Resetting demo baseline..."
cd "$APP_DIR"
python3 scripts/qm_demo_reset.py

# Start app
echo ""
echo "Starting app on port $PORT..."
echo "Visit: http://127.0.0.1:$PORT/login"
echo ""
export QM_TEST_MODE=1 QM_DISABLE_SHEETS=1 PORT="$PORT" FLASK_DEBUG=0 QM_ADMIN_PASSWORD=admin123
exec python3 QMapp.py
