#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:5051}"
PORT="${PORT:-5051}"
LOG_FILE="${LOG_FILE:-/tmp/qm_ui_regression.log}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "FAIL: required command '$1' not found"
    exit 1
  fi
}

expect_200() {
  local url="$1"
  local label="$2"
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "$url")"
  if [[ "$code" != "200" ]]; then
    echo "FAIL: $label returned HTTP $code"
    exit 1
  fi
  echo "PASS: $label (HTTP 200)"
}

assert_contains() {
  local url="$1"
  local pattern="$2"
  local label="$3"
  if ! curl -s "$url" | rg -q "$pattern"; then
    echo "FAIL: $label did not match pattern '$pattern'"
    exit 1
  fi
  echo "PASS: $label"
}

require_cmd curl
require_cmd lsof
require_cmd python3
require_cmd rg

echo "=== UI Regression: starting local app ==="
kill "$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null)" 2>/dev/null || true

QM_TEST_MODE=1 QM_TEMPLATE_STORE_READ=1 PORT="$PORT" FLASK_DEBUG=0 \
  python3 app/QMapp.py > "$LOG_FILE" 2>&1 &
APP_PID=$!
sleep 2

cleanup() {
  kill "$APP_PID" 2>/dev/null || true
}
trap cleanup EXIT

if ! lsof -iTCP:"$PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "FAIL: app did not start on port $PORT"
  tail -n 40 "$LOG_FILE" || true
  exit 1
fi
echo "PASS: app listening on port $PORT"

echo "=== UI Regression: endpoint checks ==="
expect_200 "$BASE_URL/form_builder_demo" "GET /form_builder_demo"
expect_200 "$BASE_URL/admin/template_store_status" "GET /admin/template_store_status"
expect_200 "$BASE_URL/admin/template_store_templates" "GET /admin/template_store_templates"

echo "=== UI Regression: builder content checks ==="
assert_contains "$BASE_URL/form_builder_demo" "Template Store:" "Builder shows template status"
assert_contains "$BASE_URL/form_builder_demo" "Current Form Flow" "Builder shows form flow section"
assert_contains "$BASE_URL/form_builder_demo" "Pricing Calculations" "Builder shows pricing section"

echo "=== UI Regression: clone + listing checks ==="
CLONE_KEY="ui_regression_$(date +%s)"
CLONE_URL="$BASE_URL/admin/template_clone?new_template_key=$CLONE_KEY&scenario_key=kitchen_only"
assert_contains "$CLONE_URL" "$CLONE_KEY" "Template clone endpoint returns new key"
assert_contains "$BASE_URL/admin/template_store_templates" "$CLONE_KEY" "Templates list includes cloned key"

echo "=== UI Regression: submit smoke flow ==="
python3 app/scripts/smoke_submit.py --base-url "$BASE_URL"

echo "=== UI Regression: unit tests ==="
python3 -m unittest discover -s app/tests -v >/tmp/qm_ui_regression_tests.log 2>&1 || {
  echo "FAIL: unittest suite failed"
  tail -n 40 /tmp/qm_ui_regression_tests.log || true
  exit 1
}
tail -n 10 /tmp/qm_ui_regression_tests.log

echo "=== UI Regression: completed ==="
echo "PASS: all automated checks passed"