# Formalizing Pages and Categories in Schema

## Context
Previously, "Categories" were just strings stored on `line_items`, and their assignment to a page was configured via a JSON array within a `line_items_by_category` block in `app/page_schemas.json`. This implicit structure made it difficult to manage categories independently (e.g., reordering, moving between pages, or adding empty categories).

We are formalizing the hierarchy: **Pages -> Categories -> Questions (Line Items)**.

## Goal
Implement a dedicated database table for Categories, update the JSON schema to define categories at the page level, and update the backend logic to use this new structure as the source of truth for category existence and ordering.

## Implementation Plan

### 1. Database Schema Update (`app/template_store.py`)
- Define a new table `category_templates`.
  - **Schema:** `id` (PK), `form_template_version_id` (FK), `page_template_id` (FK), `name` (TEXT), `display_order` (INTEGER).
- Ensure the `_create_schema` function creates this table.

### 2. JSON Schema Update (`app/page_schemas.json` / `app/page_schemas_published.json`)
- Refactor the page definitions.
- Lift category lists out of block configs and move them directly to the page object.
- **Target Structure:**
  ```json
  "summary_page": {
    "id": "summary_page",
    "title": "Summary Page",
    "categories": [
       {"name": "Building Works", "sort_order": 0},
       {"name": "Boundary Lines", "sort_order": 1}
    ],
    "blocks": [...]
  }
  ```

### 3. Backend Logic Integration (`app/template_store.py` & `app/QMapp.py`)
- **Data Insertion:** Update `_replace_page_templates` (and potentially `initialize_template_store`) to parse the new `categories` array from the JSON page definitions and insert them into the `category_templates` table.
- **Data Retrieval:** Update functions like `get_line_items_for_page` or the builder API endpoints (e.g., `/builder_beta/line_items_json`) to query `category_templates` for the list of categories and their order, rather than dynamically extracting unique strings from the `line_items` table.

### 4. UI Preparation (Builder)
- Plan and implement the UI components needed to manage Pages and Categories.
- Requirements include:
  - Add a new Category.
  - Rename a Category.
  - Move a Category to another Page.
  - Reorder Categories within a Page.

## Next Steps
- [x] Execute Step 1 and Step 2: Update the `template_store.py` schema creation logic and refactor the `page_schemas.json` structure.
- [x] Execute Step 3: Update `QMapp.py` and `template_store.py` to query `category_templates` rather than dynamically extracting unique strings from `line_items`.
- [x] Creation & Persistence: Be able to create and save new pages and categories natively.
- [x] Page Ordering: Up/down arrow system to reorder pages.
- [x] Category Ordering: Up/down ordering for categories within a page.
- [x] Question Ordering: Up/down ordering for questions within a category.


## Architectural Vision (Pages > Categories > Questions)
As established at the end of Session AI, our core vision is a constant nesting hierarchy: **Pages > Categories > Questions**.

Upcoming UI and Integration requirements to achieve this:
1. **Creation & Persistence:** Be able to create and save new pages and categories natively. [x] Done
2. **Category Assignment:** Be able to assign categories to specific pages.
3. **Question Assignment:** Assign questions to categories (rudimentarily set up in the question editor's Meta tab already).
4. **Page Ordering:** Up/down arrow system to reorder pages. [x] Done
5. **Category Ordering:** Up/down ordering for categories within a page. [x] Done
6. **Question Ordering:** Up/down ordering for questions within a category. [x] Done
7. **Category Controls:** UI controls for categories including a 'make visible' checkbox, 'add question' button, 'save' button, and 'move to page' (similar approach to the Meta tab in the question editor).

## New Issues from User Feedback (Session AL)
1.  Project details (index) page should not be in edit view.
2.  Still in legacy 'block-view' for Category > questions.
3.  Optional Extras page throws an undefined error.
4.  The page movement in the sidebar is a) not working and b) ugly - we will have a different approach.
5.  There is still no means of creating a category.
6.  We have no UI options in category (potentially due to legacy view).