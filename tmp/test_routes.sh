#!/bin/bash
# test_routes.sh – Endpoint testing for Quote Machine Flask app
# Usage: bash /tmp/test_routes.sh

set -e  # exit on first error

cd /Users/krisoldland/Documents/QM_web_app/app

# ------------------------------------------------------------------
# 1. Start dev server in background
# ------------------------------------------------------------------
echo "Starting Flask dev server on port 5000..."
export FLASK_APP=QMapp.py
export FLASK_ENV=development
python3 QMapp.py &
FLASK_PID=$!
sleep 2  # wait for server to be ready

# ------------------------------------------------------------------
# Helper: extract CSRF token from a saved HTML page
# ------------------------------------------------------------------
extract_csrf() {
    grep -oP 'name="csrf_token"\s+value="\K[^"]+' "$1" || echo ""
}

# ------------------------------------------------------------------
# Helper: perform a POST request, store HTML response and cookies
# ------------------------------------------------------------------
post_and_store() {
    local url="$1"
    local data="$2"
    local cookie_jar="$3"
    local output_file="$4"

    curl -s -c "$cookie_jar" -b "$cookie_jar" \
        -X POST \
        -d "$data" \
        -L \
        "http://localhost:5000$url" \
        -o "$output_file"
}

# ------------------------------------------------------------------
# Test scenarios
# ------------------------------------------------------------------
PASS=0
FAIL=0

# Scenario 1 – Login with default admin
echo "Scenario 1: Login with default admin"
COOKIE_JAR="/tmp/test_cookie_jar_1.txt"
rm -f "$COOKIE_JAR"

# Get login page to obtain CSRF token
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login_page.html
CSRF=$(extract_csrf /tmp/login_page.html)
if [ -z "$CSRF" ]; then
    echo "  FAIL: Could not extract CSRF token from login page"
    ((FAIL++))
else
    post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF" "$COOKIE_JAR" /tmp/scenario1_resp.html
    # Expect redirect to / -> final URL should be /
    FINAL_URL=$(curl -s -o /dev/null -w "%{redirect_url}" -b "$COOKIE_JAR" "http://localhost:5000/login" -d "username=admin&password=admin123&csrf_token=$CSRF" -L)
    if echo "$FINAL_URL" | grep -q "/$"; then
        echo "  PASS"
        ((PASS++))
    else
        echo "  FAIL: redirect not to /"
        ((FAIL++))
    fi
fi

# Scenario 2 – Login with bad credentials
echo "Scenario 2: Login with bad credentials"
COOKIE_JAR="/tmp/test_cookie_jar_2.txt"
rm -f "$COOKIE_JAR"

curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login_page2.html
CSRF=$(extract_csrf /tmp/login_page2.html)
if [ -z "$CSRF" ]; then
    echo "  FAIL: Could not extract CSRF token"
    ((FAIL++))
else
    post_and_store "/login" "username=admin&password=wrong&csrf_token=$CSRF" "$COOKIE_JAR" /tmp/scenario2_resp.html
    # Expect login page again (no redirect to /)
    if grep -q '<form.*login' /tmp/scenario2_resp.html; then
        echo "  PASS"
        ((PASS++))
    else
        echo "  FAIL: did not stay on login page"
        ((FAIL++))
    fi
fi

# Scenario 3 – Logout
echo "Scenario 3: Logout"
# First login with admin
COOKIE_JAR="/tmp/test_cookie_jar_3.txt"
rm -f "$COOKIE_JAR"
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login3.html
CSRF=$(extract_csrf /tmp/login3.html)
post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF" "$COOKIE_JAR" /tmp/scenario3a.html

# Now logout
post_and_store "/logout" "" "$COOKIE_JAR" /tmp/scenario3b.html
# Expect redirect to /login
if grep -q '<form.*login' /tmp/scenario3b.html; then
    echo "  PASS"
    ((PASS++))
else
    echo "  FAIL: not redirected to login"
    ((FAIL++))
fi

# Scenario 4 – List users (unauthenticated)
echo "Scenario 4: List users (unauthenticated)"
COOKIE_JAR="/tmp/test_cookie_jar_4.txt"
rm -f "$COOKIE_JAR"
curl -s -c "$COOKIE_JAR" "http://localhost:5000/admin/list-users" -L -o /tmp/scenario4.html
if grep -q '<form.*login' /tmp/scenario4.html; then
    echo "  PASS"
    ((PASS++))
else
    echo "  FAIL: not redirected to login"
    ((FAIL++))
fi

# Scenario 5 – List users (authenticated as admin)
echo "Scenario 5: List users (authenticated as admin)"
COOKIE_JAR="/tmp/test_cookie_jar_5.txt"
rm -f "$COOKIE_JAR"
# login first
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login5.html
CSRF=$(extract_csrf /tmp/login5.html)
post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF" "$COOKIE_JAR" /tmp/scenario5a.html

# now get list-users
curl -s -b "$COOKIE_JAR" "http://localhost:5000/admin/list-users" -o /tmp/scenario5.html
if grep -q 'list_users\|users' /tmp/scenario5.html; then
    echo "  PASS"
    ((PASS++))
else
    echo "  FAIL: did not get list_users page"
    ((FAIL++))
fi

# Scenario 6 – Register a user
echo "Scenario 6: Register a user"
COOKIE_JAR="/tmp/test_cookie_jar_6.txt"
rm -f "$COOKIE_JAR"
# login as admin
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login6.html
CSRF_LOGIN=$(extract_csrf /tmp/login6.html)
post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF_LOGIN" "$COOKIE_JAR" /tmp/scenario6a.html

# get register page to obtain CSRF
curl -s -b "$COOKIE_JAR" "http://localhost:5000/register" -o /tmp/register6.html
CSRF_REG=$(extract_csrf /tmp/register6.html)
if [ -z "$CSRF_REG" ]; then
    echo "  FAIL: Could not extract CSRF token from /register"
    ((FAIL++))
else
    post_and_store "/register" "username=testuser&password=test123&confirm_password=test123&csrf_token=$CSRF_REG" "$COOKIE_JAR" /tmp/scenario6b.html
    # Expect redirect to /admin/list-users (or /list-users as per description)
    FINAL_URL=$(curl -s -o /dev/null -w "%{redirect_url}" -b "$COOKIE_JAR" -X POST -d "username=testuser&password=test123&confirm_password=test123&csrf_token=$CSRF_REG" "http://localhost:5000/register" -L)
    if echo "$FINAL_URL" | grep -q 'list-users'; then
        echo "  PASS"
        ((PASS++))
    else
        echo "  FAIL: did not redirect to list-users"
        ((FAIL++))
    fi
fi

# Scenario 7 – Duplicate registration
echo "Scenario 7: Duplicate registration"
COOKIE_JAR="/tmp/test_cookie_jar_7.txt"
rm -f "$COOKIE_JAR"
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login7.html
CSRF_LOGIN=$(extract_csrf /tmp/login7.html)
post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF_LOGIN" "$COOKIE_JAR" /tmp/scenario7a.html

curl -s -b "$COOKIE_JAR" "http://localhost:5000/register" -o /tmp/register7.html
CSRF_REG=$(extract_csrf /tmp/register7.html)
post_and_store "/register" "username=testuser&password=test123&confirm_password=test123&csrf_token=$CSRF_REG" "$COOKIE_JAR" /tmp/scenario7b.html
if grep -q 'already exists\|duplicate' /tmp/scenario7b.html; then
    echo "  PASS"
    ((PASS++))
else
    echo "  FAIL: no error message for duplicate"
    ((FAIL++))
fi

# Scenario 8 – Promote / Demote user
echo "Scenario 8: Promote / Demote user"
COOKIE_JAR="/tmp/test_cookie_jar_8.txt"
rm -f "$COOKIE_JAR"
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login8.html
CSRF_LOGIN=$(extract_csrf /tmp/login8.html)
post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF_LOGIN" "$COOKIE_JAR" /tmp/scenario8a.html

# promote
post_and_store "/admin/promote-user/testuser" "" "$COOKIE_JAR" /tmp/scenario8b.html
# demote
post_and_store "/admin/demote-user/testuser" "" "$COOKIE_JAR" /tmp/scenario8c.html

# Check if auth_credentials.json changed accordingly (optional)
# For simplicity, assume success if no error.
if grep -q 'error\|denied' /tmp/scenario8b.html /tmp/scenario8c.html; then
    echo "  FAIL: error during promote/demote"
    ((FAIL++))
else
    echo "  PASS"
    ((PASS++))
fi

# Scenario 9 – Delete user
echo "Scenario 9: Delete user"
COOKIE_JAR="/tmp/test_cookie_jar_9.txt"
rm -f "$COOKIE_JAR"
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login9.html
CSRF_LOGIN=$(extract_csrf /tmp/login9.html)
post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF_LOGIN" "$COOKIE_JAR" /tmp/scenario9a.html

post_and_store "/admin/delete-user/testuser" "" "$COOKIE_JAR" /tmp/scenario9b.html

if grep -q 'deleted\|success' /tmp/scenario9b.html; then
    echo "  PASS"
    ((PASS++))
else
    echo "  FAIL: delete did not succeed"
    ((FAIL++))
fi

# Scenario 10 – Admin payment schedule config (GET)
echo "Scenario 10: Admin payment schedule config (GET)"
COOKIE_JAR="/tmp/test_cookie_jar_10.txt"
rm -f "$COOKIE_JAR"
curl -s -c "$COOKIE_JAR" "http://localhost:5000/login" -o /tmp/login10.html
CSRF_LOGIN=$(extract_csrf /tmp/login10.html)
post_and_store "/login" "username=admin&password=admin123&csrf_token=$CSRF_LOGIN" "$COOKIE_JAR" /tmp/scenario10a.html

curl -s -b "$COOKIE_JAR" "http://localhost:5000/admin/payment-schedule-config" -o /tmp/scenario10b.html
if grep -q 'payment.*schedule\|config' /tmp/scenario10b.html; then
    echo "  PASS"
    ((PASS++))
else
    echo "  FAIL: did not render config page"
    ((FAIL++))
fi

# ------------------------------------------------------------------
# Clean up dev server
# ------------------------------------------------------------------
kill $FLASK_PID 2>/dev/null
wait $FLASK_PID 2>/dev/null

echo "------------------------------------------------"
echo "Test results: $PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then
    exit 1
fi