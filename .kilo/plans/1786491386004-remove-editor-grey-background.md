# Plan: Remove misleading grey editor background

## Goal
Eliminate the false overflow indicator in the Quote Editor by removing the grey workspace background. The editor becomes a continuous scroll workspace; the preview modal remains the accurate page-boundary view.

## Changes
### 1. CSS: Remove grey background from editor canvas
**File:** `app/static/css/user_output_editor.css`
**Line:** 101
**Change:** `background: #e9ecef;` → `background: #fff;`

This removes the grey "off-page" area. The white `.document-page` with its shadow remains visible, but without the contrasting grey background there is no misleading overflow signal.

## Behavior after fix
- **Quote Editor:** Continuous scroll workspace. Content is not constrained to a visual page boundary in the editor.
- **Preview:** Accurate page-boundary view (unchanged). Users see exactly how content aligns on page.
- **Pagination:** Controlled by explicit page break blocks inserted by the user. No automatic overflow detection needed.

## Validation
1. Open Quote Editor
2. Confirm the workspace background is white (no grey)
3. Confirm the `.document-page` white page with shadow is still visible
4. Add enough content to span multiple pages in preview
5. Confirm preview shows correct page breaks
6. Confirm no false "off-page" indication in editor
