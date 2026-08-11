# Fix Bullet Positioning in Editor List Groups

## Problem
Bullets/number markers appear **outside** the `.editor-block` visual boundary in the editor center panel. The bullet floats to the left, outside the block's content area, because native `<ul>`/`<ol>` list styling renders the marker at the `<li>` border edge, while the `.editor-block` content (with header, drag handle, etc.) is positioned inside the `<li>` padding.

## Root Cause
- `wrapListGroups` (JS line 486) wraps each `.editor-block` inside `<li>` elements within a `<ul class="editor-list-group">`
- CSS (line 226-235) sets `list-style: disc` on `.editor-list-group` and `padding-left: 24px` on `.editor-list-group li`
- Both inline style (`paddingLeft: 18px` at JS line 524) and CSS (`padding-left: 24px`) apply to `<li>`
- Native `list-style-position: outside` (default) renders the bullet to the LEFT of the `<li>` padding, which is outside the `.editor-block` content area
- The `.editor-block__header` (drag handle, type label, remove button) is inside the `<li>`, so the bullet appears above-left of the header, not aligned with the actual content

## Design Decision
Use **CSS custom bullet/number via `::before` pseudo-element** instead of native list styling. This gives full control over position and ensures the marker appears inside the `.editor-block` visual boundary, aligned with the content.

## Implementation Plan

### Step 1: Modify `wrapListGroups` in `user_output_editor.js`
- Remove inline `paddingLeft` from `<li>` creation (line 524)
- Add class `editor-block--in-list` to each `.editor-block` element inside the list group
- Set `data-list-type` attribute on `.editor-block` elements (value: `'ul'` or `'ol'`)
- Set `data-list-index` attribute on `.editor-block` elements (value: numeric index)
- Remove `list-style: disc` from `.editor-list-group` CSS — use `list-style: none` instead

### Step 2: Update CSS in `user_output_editor.css`
Replace current `.editor-list-group` and `.editor-list-group li` rules with:
```css
.editor-list-group {
  margin: 0 0 12px 0;
  padding: 0;
  list-style: none;
}

.editor-list-group li {
  margin-bottom: 2px;
}

.editor-block--in-list {
  position: relative;
  padding-left: 24px;
}

.editor-block--in-list::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  font-size: 1.2em;
  line-height: 1.5;
}

.editor-block--in-list[data-list-type="ul"]::before {
  content: '•';
  font-weight: bold;
}

.editor-block--in-list[data-list-type="ol"]::before {
  content: attr(data-list-index);
  font-weight: bold;
}
```

### Step 3: Verify preview rendering is unaffected
The preview (`renderPreviewPage`/`renderPreviewListItem`) uses standard `<ul>`/`<ol>` with `<li>` tags — this is correct for print/PDF output and doesn't need the CSS pseudo-element fix. No changes needed to preview functions.

## Files to Modify
- `app/static/js/user_output_editor.js` — Step 1 (lines 508-534, modify `wrapListGroups`)
- `app/static/css/user_output_editor.css` — Step 2 (lines 226-235, replace `.editor-list-group` rules)

## Validation
1. Restart Flask server
2. Load quote editor at http://127.0.0.1:5305/quote_editor
3. Add multiple form question blocks
4. Ctrl+Click to select multiple blocks
5. Click UL button → verify bullets appear INSIDE each block, aligned with content (not floating left)
6. Click OL button → verify numbers (1, 2, 3...) appear inside each block
7. Open Preview modal → verify standard bullet/number rendering in preview
8. Verify drag-and-drop reordering still works for blocks inside list groups
9. Verify Clear List button properly unwraps blocks
