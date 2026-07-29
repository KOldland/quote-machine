# Follow-Up Question Visibility Fix Plan

## Problem
In Form Mode, checking a line item checkbox does not reveal the associated follow-up question input field.

## Root Cause Analysis
1. Data flow from DB to template context verified (is_follow_up, follow_up_type, follow_up_config included)
2. HTML rendering for follow-up inputs exists in form_preview.html  
3. JavaScript toggle logic present in script.js
4. Likely issues: data attribute mismatch, JS selector failure, or event binding not executing

## Solution Plan
### Phase 1: Verification Tasks
- [ ] Confirm is_follow_up=1 in database for test item
- [ ] Inspect rendered HTML: checkbox has data-follow-up="1" and class="preview-checkbox-input"
- [ ] Inspect rendered HTML: .preview-follow-up container exists with correct data-follow-up-for
- [ ] Test JS selector: document.querySelectorAll('.preview-checkbox-input[data-follow-up="1"]')
- [ ] Verify JS executes: add console.log to toggle handler and test in browser

### Phase 2: Fix Implementation (If Needed)
If verification reveals issues:
- [ ] Fix data attribute type mismatch (ensure integer 1 renders as "1" not "True"/"1")
- [ ] Correct JS selector if class/attribute names differ
- [ ] Ensure script.js toggle logic runs on form preview page (not blocked by isBuilderBetaPage)
- [ ] Add error handling to JS toggle logic

### Phase 3: Validation Tasks
- [ ] Manual test: check checkbox → follow-up input appears
- [ ] Manual test: uncheck checkbox → follow-up input hides and clears
- [ ] Verify persistence after page refresh
- [ ] Confirm no JS errors in console during interaction
- [ ] Verify existing functionality remains intact

## Dependencies
- Requires working database connection and session state
- Depends on correct form preview route rendering
- Assumes no conflicting JS libraries

## Success Criteria
When user checks a line item checkbox in Form Mode:
1. Corresponding follow-up input field becomes visible immediately
2. Field is editable and accepts user input
3. Unchecking hides the field and clears its value
4. Page refresh maintains correct visibility state
5. No JavaScript errors occur during interaction