# MVP Demo Release Gate Checklist

**Status**: Ready for MVP Release  
**Date**: [YYYY-MM-DD]  
**Tested By**: [Name]  

## Pre-Release Validation

### Code & Tests (5 min)
- [ ] Unit test suite passes: `cd app && python3 -m unittest discover -s tests -p 'test_*.py'`
  - Expected: 28/28 tests green
- [ ] No syntax errors in QMapp.py
- [ ] No uncommitted changes: `git status` is clean

### Phase 1: Baseline Reset (3 min)
- [ ] Reset script works: `cd app && python3 scripts/qm_demo_reset.py`
  - Expected: "RESET OK" message
- [ ] page_schemas.json matches page_schemas_published.json after reset

### Phase 2: Portable Startup (5 min)
- [ ] Startup script executes without errors
- [ ] App boots cleanly on port 5051
- [ ] Login page accessible at http://127.0.0.1:5051/login
- [ ] No missing dependency errors in logs

### Phase 3: Fallback Mode (3 min)
- [ ] App boots with QM_TEST_MODE=1 QM_DISABLE_SHEETS=1
- [ ] No Google credential errors in console
- [ ] No blocking on sheet initialization
- [ ] Forms load without external API calls

### Phase 4: Demo-Critical Paths (15 min)
- [ ] Admin login works (admin / password)
- [ ] Edit mode renders with ?edit=1 query param
- [ ] Field label editing persists across refresh
- [ ] Field hide/show toggles work
- [ ] Inspector drawer opens and saves pricing settings
- [ ] Publish draft button succeeds with alert
- [ ] Rollback button succeeds and reverts changes
- [ ] User login works (user / user)
- [ ] User can fill and submit form without errors

### Phase 5: Operator Readiness (10 min)
- [ ] Smoke check script passes: `bash app/scripts/qm_demo_verify.sh`
- [ ] Demo walkthrough checklist (DEMO_WALKTHROUGH.md) completes in one pass
- [ ] Time to first working form: < 5 min from startup
- [ ] Time to complete walkthrough: < 15 min

### Phase 6: Release Gate
- [ ] All above checks pass ✓
- [ ] No known showstoppers
- [ ] README or deployment docs updated
- [ ] Scripts committed to main branch

## Release Decision

**Go/No-Go**: [ ] GO [ ] NO-GO

**Issues Found** (if any):
- Issue 1: [Description] → [Resolution]
- Issue 2: [Description] → [Resolution]

**Sign-Off**:
- Developer: _________________ Date: _________
- QA/Reviewer: _________________ Date: _________

**Notes**:
[Any additional context]

---

## Post-Release (Optional Stretch)

### Phase 7: Containerization (if time allows, 30 min)
- [ ] Dockerfile created with python:3.9-slim base
- [ ] Dependencies installed in image
- [ ] Image builds: `docker build -t qm-demo:latest .`
- [ ] Container runs: `docker run -p 5051:5051 -e QM_TEST_MODE=1 qm-demo:latest`
- [ ] Demo walkthrough passes in containerized version

**Container Release Status**: [ ] READY [ ] SKIPPED
