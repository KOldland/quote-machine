# Demo Walkthrough Checklist

Estimated runtime: **10-15 minutes**

## Login & Role Setup (1 min)
- [ ] Visit http://127.0.0.1:5051/login
- [ ] Observe login form (username, password fields)
- [ ] Login as admin with username=`admin` and your QM_ADMIN_PASSWORD
- [ ] Confirm redirected to dashboard with "admin" role visible

## Admin Edit Mode Flow (4 min)
- [ ] Navigate to any form page
- [ ] Add `?edit=1` to URL to enter edit mode
- [ ] Observe yellow edit-mode-bar at top with "Publish draft" and "Rollback" buttons
- [ ] Change a field label (e.g., rename "Special Notes" to "Important Notes")
- [ ] Click the "Save" button next to field
- [ ] Refresh page → confirm label change persists
- [ ] Hide a field using hide toggle
- [ ] Refresh page → confirm field remains hidden

## Inspector & Pricing Flow (3 min)
- [ ] In edit mode, open Inspector drawer on a text or number field
- [ ] Set pricing mode to "entered"
- [ ] Set label for entered amount (e.g., "Custom Amount")
- [ ] Click "Save Pricing"
- [ ] Refresh page → confirm settings persist
- [ ] Exit edit mode (click X button or remove ?edit=1)
- [ ] Verify field now shows an input for entered amount during runtime

## Publish & Rollback Flow (3 min)
- [ ] Enter edit mode again
- [ ] Change a different field label (make it visibly different)
- [ ] Click "Publish draft" → confirm success alert
- [ ] Refresh page → confirm label change is now "published"
- [ ] Make another field change (don't publish)
- [ ] Click "Rollback" → confirm alert
- [ ] Verify field reverted to previously published state
- [ ] Confirm draft changes are lost

## User Runtime Flow (3 min)
- [ ] Logout (click logout button)
- [ ] Login as user with username=`user` and password=`user`
- [ ] Navigate to a form page
- [ ] Fill in form fields end-to-end
- [ ] Navigate to Review page
- [ ] Review submission preview
- [ ] Click "Submit" or equivalent
- [ ] Confirm no errors and submission triggers

## Validation: All Steps Pass ✓
If all steps above complete without errors, demo is ready for handoff.

**Common Issues & Fixes**
- **404 on edit mode**: Page doesn't exist or is not in schema. Try /special_notes_page or check page_schemas.json for valid page IDs.
- **Publish fails**: Check browser console for network errors. Verify Flask app is running.
- **Pricing mode doesn't save**: Verify Inspector "Save Pricing" button click registered. Check browser console.
- **Rollback reverts too much**: Expected behavior. Rollback restores entire draft to last-published state, not just one field.
