vision_text = """

## Architectural Vision (Pages > Categories > Questions)
As established at the end of Session AI, our core vision is a constant nesting hierarchy: **Pages > Categories > Questions**.

Upcoming UI and Integration requirements to achieve this:
1. **Creation & Persistence:** Be able to create and save new pages and categories natively.
2. **Category Assignment:** Be able to assign categories to specific pages.
3. **Question Assignment:** Assign questions to categories (rudimentarily set up in the question editor's Meta tab already).
4. **Page Ordering:** Up/down arrow system to reorder pages.
5. **Category Ordering:** Up/down ordering for categories within a page.
6. **Question Ordering:** Up/down ordering for questions within a category.
7. **Category Controls:** UI controls for categories including a 'make visible' checkbox, 'add question' button, 'save' button, and 'move to page' (similar approach to the Meta tab in the question editor).
"""

with open('app/.continue/prompts/current_development.md', 'a') as f:
    f.write(vision_text)

with open('app/SESSION.md', 'r') as f:
    session = f.read()

session = session.replace(
    "Plan UI components for managing Categories (add, rename, move, reorder).",
    "Plan UI components for managing Categories (add, rename, move, reorder) and Pages, following the Pages > Categories > Questions hierarchy. Implement up/down ordering for all 3 levels."
)

with open('app/SESSION.md', 'w') as f:
    f.write(session)

print("Vision appended.")
