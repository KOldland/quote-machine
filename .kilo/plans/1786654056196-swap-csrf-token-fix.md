# Fix: Swap Request Failed Due to Missing CSRF Token

## Problem
The `/builder_beta/swap_order` endpoint returns "swap request failed" because the fetch call is missing the CSRF token header. The app uses `CSRFProtect(app)` globally, and the swap endpoint is not exempt. Every other fetch call in `_builder_macros.html` includes the token, but the swap call at line 753 does not.

## Root Cause
`app/QMapp.py:61` enables global CSRF protection. `builder_swap_order` at line 2082 lacks `@csrf.exempt`. The template fetch at line 753 only sends `Content-Type` header, triggering a 400/403 rejection caught by `.catch()` at line 782.

## Fix
Add the `X-CSRFToken` header to the swap fetch call in `app/templates/_builder_macros.html:753`.

**File:** `app/templates/_builder_macros.html`
**Line:** 753
**Change:**
```diff
-                headers: {'Content-Type': 'application/json'},
+                headers: {
+                    'Content-Type': 'application/json',
+                    'X-CSRFToken': (document.querySelector('[name=csrf_token]') || {}).value || ''
+                },
```

## Validation
1. Restart Flask.
2. Open builder page and attempt to swap a question or category.
3. "Swap request failed" alert should no longer appear; the swap should succeed.
4. Check browser Network tab for a 200 response on `/builder_beta/swap_order`.
