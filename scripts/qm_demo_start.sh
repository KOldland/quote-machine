#!/bin/bash
set -e
PORT="${1:-5051}"

# Since this script now lives directly in app/scripts/, 
# APP_DIR is the parent directory of this script's folder.
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== QM Demo Startup ==="
echo "Port: $PORT"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"; exit 1
fi

# Create/Verify the venv inside your true app workspace folder
if [ ! -d "${APP_DIR}/venv" ]; then
    echo "Creating venv..."
    python3 -m venv "${APP_DIR}/venv"
fi

# Activate the venv
source "${APP_DIR}/venv/bin/activate"

# Install dependencies using the correct app directory path
echo "Installing dependencies..."
pip install -q -r "${APP_DIR}/requirements.txt"

# Reset demo baseline
echo "Resetting demo baseline..."
cd "$APP_DIR"
python3 scripts/qm_demo_reset.py

# Start app
echo ""
echo "Starting app on port $PORT..."
echo "Visit: http://127.0.0.1:$PORT/login"
echo ""
export QM_TEST_MODE=1 QM_DISABLE_SHEETS=1 QM_CATALOG_SOURCE=db PORT="$PORT" FLASK_DEBUG=0 QM_ADMIN_PASSWORD=admin123
exec python3 QMapp.py
