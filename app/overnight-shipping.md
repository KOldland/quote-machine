
🚀 Demo MVP Ship Plan – Tonight
Focus: End-to-end demo flow works
Nothing else matters. Security is fine for a single-client demo. Let's get the flow working.

**The 5 Critical Steps**

//**DONE**//
Step 1: Fix the get_builder_beta_state() bug (15 min)
There's a logic bug that will cause the app to show no pages. At line ~700-720 of QMapp.py:


Apply
# BUG: These two lines overwrite the pages from the schema file
schema_pages = page_schemas.get('pages', {})  # This loads from the file
if isinstance(schema_pages, dict):
    pages = schema_pages.copy()  # This sets pages correctly
else:
    pages = {}

# Then THIS line overwrites it with the builder_beta state (which is empty):
pages = state.get('pages', {})  # <-- BUG: overwrites the data from the file
Fix: Remove the second assignment. The builder_beta state should use the schema_pages as its source, not overwrite it.

//**DONE**//
Step 2: Verify the review route exists (10 min)
I need to check if there's a @app.route('/review') in QMapp.py. The review page template exists at app/templates/review.html but it references variables like review_data, li_by_category, totals_by_group, TITLE_MAPPING. If the route doesn't exist or the data isn't passed correctly, the review page will crash.

Fix: Either add the missing route or wire up the existing session data to the review template.

//**DONE**  //
Step 3: Wire up the form flow end-to-end (30 min)
The flow should be:

/ → Project Details (client address, date)
Click "Continue" → first dynamic page (e.g. ground_floor_page)
Fill in checkboxes/inputs → click "Save & Continue"
Navigate through all pages → lands on /review
Check: The dynamic_page route handles POST correctly. The index route redirects to the first page. Need to verify the last page's navigation points to review.

//**DONE**//

Step 4: Make the review page work (45 min)
The review template needs:

review_data – dict of form answers grouped by section
li_by_category – selected line items grouped by category
totals_by_group – pricing breakdown
TITLE_MAPPING – human-readable field names
Fix: Create or update the /review route to compile all session data and pass it to the template.

//**DONE**//
Step 5: Make export work (30 min)
The export routes at /api/export-pdf and /api/export-docx exist but:

They use session.get('form_key', 'kitchen_only_template_test') – need to ensure this is set
calculate_quote() expects line_items from the DB – need to seed test data
session.get('form_data', {}) must contain the answers
Fix: Export the session data and make sure the calculator can find the line items.

Execution Plan (Timeline)
Task	                            What to do
Fix get_builder_beta_state() bug	Remove the overwriting line; ensure pages from page_schemas.json are used
Check review route + add if missing	Search for @app.route('/review') in QMapp.py; if missing, add it with session data compilation
Wire up form navigation	            Verify last page's next_endpoint points to review; fix navigation logic
Build the review route	            Compile all session data (data, checkbox_data) into review_data, li_by_category, totals_by_group
Test the full flow	                Walk through: start → fill form → review → confirm it works
Fix export	                        Ensure session['form_key'] is set; verify calculator can find line items
Polish & cleanup	                Remove debug prints, add .gitignore for SQLite WAL files, verify startup
Final walkthrough	                Complete end-to-end demo flow from start to PDF export

intended structure of app. 

There are in effect 3 modes

1) Edit Mode <--- to avoid confsion later I am going to call this FORM BUILDER mode. This is where ADMIN can edit and build FORMS for the user to complete. 
2) FORM Mode <--- this is the primary use mode. The intention is that the USER (not ADMIN) can quickly check the items in the FORM some of which may prompt for manual input (names, numbers etc) and then save this to a session. THis mode also has teh Culculator FUNCTION and IMAGE UPLOAD and ALIGNMENT FUNCTIONS
3) QUOTATION EDITOR Mode <----- Moving forward we will call this EDIT mode. This mode is engaged after the USER has submitted their input, uploaded their images, saved there session and run REVIEW function. From REVIEW they then have a WYSIWYG editor that allows them to make edits to the QUOTATION. Edits such as changing test,, bold/underline/emphasis, font family selector, font type selector (H1, H2, H3, para), drag and drop image movement and edit/insert additional notes. 