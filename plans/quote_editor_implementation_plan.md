# Quote Editor Implementation Plan

## Overview
Build a block-based Quote Editor at `/quote_editor` where users assemble, edit, and export quotes using reusable blocks (Form, Calculator, Notes, Image, Image Group). Static snapshots with red-dot change tracking. SortableJS for drag-drop. Separate `quote_editor_layouts` table. Own export endpoints.

---

## Phase 1: Backend Foundation

### 1.1 Database Migration
**File:** `app/template_store.py`

Add `quote_editor_layouts` table via `_create_schema()`:

```sql
CREATE TABLE IF NOT EXISTS quote_editor_layouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_template_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default',
    blocks_json TEXT NOT NULL DEFAULT '[]',
    settings_json TEXT NOT NULL DEFAULT '{}',
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (form_template_id) REFERENCES form_templates(id) ON DELETE CASCADE
);
```

Also add helper functions:
- `create_quote_editor_layout(form_template_id, name, blocks_json, is_default) -> dict`
- `get_quote_editor_layout(form_template_id, layout_id=None) -> dict | None`
- `list_quote_editor_layouts(form_template_id) -> list`
- `update_quote_editor_layout(layout_id, blocks_json=None, settings=None, name=None) -> bool`
- `delete_quote_editor_layout(layout_id) -> bool`
- `duplicate_quote_editor_layout(layout_id, new_name) -> dict`

### 1.2 Quote Editor Routes
**File:** `app/QMapp.py`

Add new blueprint or routes:

```
GET  /quote_editor                      -> render editor
GET  /quote_editor/layouts              -> list layouts (JSON)
POST /quote_editor/layouts              -> create layout
PUT  /quote_editor/layouts/<id>         -> update layout
DELETE /quote_editor/layouts/<id>       -> delete layout
POST /quote_editor/layouts/<id>/duplicate -> duplicate layout
POST /quote_editor/upload-image         -> upload image to editor
GET  /quote_editor/source/<page_key>/<block_id> -> get source block data
POST /quote_editor/save-quote           -> save quote with metadata
GET  /quote_editor/load-quote/<id>      -> load saved quote
```

Session keys used:
- `data` — form data
- `checkbox_data` — form checkbox state
- `session_overrides` — calculator overrides
- `uploaded_images` — Image Mode uploads

### 1.3 Export Endpoints
**New file:** `app/quote_editor_export.py`

Blueprint: `quote_editor_export_bp`

Endpoints:
```
GET /api/quote-editor/export-pdf
GET /api/quote-editor/export-docx
```

Behavior:
- Accept `layout_id` query param (or use session default)
- Load blocks from `quote_editor_layouts.blocks_json`
- Render via WeasyPrint / python-docx
- Each block type has a renderer:
  - `form` → renders label + value
  - `calculator` → renders group table + totals
  - `notes` → renders text editor content as paragraphs
  - `image` → renders inline image
  - `image_group` → renders image grid
- Respect per-block settings (margin, padding, alignment)

Register blueprint in `QMapp.py`.

### 1.4 Image Upload
**New file:** `app/quote_editor_routes.py` (or add to existing blueprint)

- `POST /quote_editor/upload-image`
  - Accepts multipart file
  - Saves to `app/static/uploads/quote_editor/`
  - Returns `{url, filename, width, height}`
  - Also adds to `session['quote_editor_images']`

---

## Phase 2: Frontend Structure

### 2.1 HTML Template Update
**File:** `app/templates/user_output_editor.html`

Replace skeleton with 3-column layout:

```
┌──────────────────────────────────────────────────────────┐
│ Header: Quote Editor | Layout selector | Save/Load/Export │
├──────────┬───────────────────────────────┬───────────────┤
│ Left     │ Centre                       │ Right         │
│ Source   │ Canvas                       │ Insert        │
│ Column   │ (SortableJS blocks)          │ Panel         │
│          │                              │               │
│ Block    │ Floating toolbar            │ NotesBlock    │
│ mapping  │ (H1, H2, Para, Bold, etc)   │ CalcBlock     │
│ with red │                              │ ImageGroup    │
│ dots     │                              │ Image         │
│          │                              │               │
│          │                              │ Load/Save/    │
│          │                              │ Export        │
└──────────┴───────────────────────────────┴───────────────┘
```

Key CSS classes:
- `.editor-source-column` — left panel, 220px wide
- `.editor-canvas` — centre, flex-grow, min-height 500px
- `.editor-insert-panel` — right panel, 220px wide
- `.editor-block` — individual block wrapper
- `.editor-block--form`, `.editor-block--calculator`, etc.
- `.editor-block__source-dot` — red dot indicator
- `.editor-toolbar` — floating toolbar, sticky top of canvas

### 2.2 Block Rendering System
**New file:** `app/static/js/quote_editor_blocks.js`

Block type definitions with renderers:

```javascript
const BLOCK_TYPES = {
  form: {
    render(data) { ... },
    getSourceData(sourceRef) { ... },
    isDirty() { ... }
  },
  calculator: { ... },
  notes: { ... },
  image: { ... },
  image_group: { ... }
};
```

Each block DOM structure:
```html
<div class="editor-block" data-block-id="..." data-block-type="form">
  <div class="editor-block__header">
    <span class="editor-block__type-label">Form: Client Address</span>
    <span class="editor-block__source-dot" title="Source changed"></span>
    <button class="editor-block__remove">&times;</button>
  </div>
  <div class="editor-block__content" contenteditable="true">
    ...
  </div>
  <div class="editor-block__settings">
    <label>Margin: <input type="number" data-setting="margin"></label>
    <label>Padding: <input type="number" data-setting="padding"></label>
    <label>Align: 
      <select data-setting="alignment">
        <option value="left">Left</option>
        <option value="center">Center</option>
        <option value="right">Right</option>
      </select>
    </label>
  </div>
</div>
```

### 2.3 SortableJS Integration
**File:** `app/static/js/user_output_editor.js`

```javascript
import Sortable from 'sortablejs';

const canvas = document.getElementById('editorCanvas');
new Sortable(canvas, {
  animation: 150,
  handle: '.editor-block__drag-handle',
  onEnd: (evt) => {
    const newOrder = [...canvas.children].map(el => el.dataset.blockId);
    saveBlockOrder(newOrder);
  }
});
```

Add drag handles to each block header.

### 2.4 Floating Toolbar
**File:** `app/static/css/user_output_editor.css`

```css
.editor-toolbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: white;
  border-bottom: 1px solid #ddd;
  padding: 8px;
  display: flex;
  gap: 4px;
}
```

Buttons: H1, H2, Para, Note, Guide, Bold, Italic, Underline, Insert Image, Align Left/Center/Right.

Toolbar uses `document.execCommand` (deprecated but still works) or modern `document.queryCommandSupported`. For insert image, open gallery modal.

### 2.5 Left Column: Source Mapping
**File:** `app/static/js/quote_editor_source_column.js`

```javascript
function updateSourceColumn(activeBlockId) {
  const block = getBlock(activeBlockId);
  if (!block || block.type !== 'form') return;
  
  const sourcePage = block.source_page;
  const sourceBlockId = block.source_block_id;
  
  // Fetch source data
  fetch(`/quote_editor/source/${sourcePage}/${sourceBlockId}`)
    .then(r => r.json())
    .then(data => {
      renderSourceMap(data, block);
    });
}
```

Red dot logic:
- On block render, compare `block.snapshot.value` with current form data (fetched from API or session)
- If different, add `.editor-block__source-dot--dirty`
- On editor edit, add `.editor-block__editor-dirty`
- Left column shows both indicators with labels

### 2.6 Right Panel: Insert Options
**File:** `app/templates/user_output_editor.html`

```html
<div class="editor-insert-panel">
  <button class="insert-btn" data-block-type="notes">Notes Block</button>
  <button class="insert-btn" data-block-type="calculator">Calc Block</button>
  <button class="insert-btn" data-block-type="image_group">Image Group</button>
  <button class="insert-btn" data-block-type="image">Image</button>
  
  <hr>
  <button class="action-btn" onclick="loadLayout()">Load</button>
  <button class="action-btn" onclick="saveLayout()">Save</button>
  <button class="action-btn" onclick="saveAsTemplate()">Save As Template</button>
  <button class="action-btn" onclick="exportPDF()">Export PDF</button>
  <button class="action-btn" onclick="exportDOCX()">Export DOCX</button>
</div>
```

Image button opens gallery modal (see 2.7).

### 2.7 Image Gallery Modal
**New file:** `app/templates/_image_gallery_modal.html`

Partial template for modal:
```html
<div id="imageGalleryModal" class="modal">
  <div class="modal-content">
    <h3>Select Image</h3>
    <div class="gallery-grid">
      <!-- Thumbnails from session + filesystem -->
    </div>
    <button class="upload-btn">Upload New Image</button>
    <input type="file" accept="image/*" multiple style="display:none">
    <button class="close-modal">Close</button>
  </div>
</div>
```

**JS:** `app/static/js/quote_editor_gallery.js`
- Load images from `GET /quote_editor/images` (returns session + filesystem)
- Click thumbnail -> insert as `image` block (inline) or `image_group` block
- Upload button triggers file input -> POST `/quote_editor/upload-image` -> refresh gallery

---

## Phase 3: Integration With Other Modes

### 3.1 "Add to Quote" Buttons
Add buttons to existing pages that push blocks into `session['quote_editor_pending_blocks']`:

**Form Mode (`form.html`):**
```html
<button id="addToQuoteBtn" data-page="{{ page_key }}">
  Add Current Page to Quote
</button>
```

**Calculator Mode (`calculator.html`):**
```html
<button id="addCalcToQuoteBtn">
  Add Calculator Summary to Quote
</button>
```

**Image Upload (`image_upload.html`):**
```html
<button id="addImagesToQuoteBtn">
  Add Uploaded Images to Quote
</button>
```

**JS Hook (`app/static/js/quote_editor_integration.js`):**
```javascript
document.getElementById('addToQuoteBtn')?.addEventListener('click', async () => {
  const pageKey = document.body.dataset.pageKey;
  const response = await fetch(`/quote_editor/add-form-block?page=${pageKey}`);
  const block = await response.json();
  sessionStorage.setItem('quote_editor_pending_block', JSON.stringify(block));
  window.location.href = '/quote_editor';
});
```

On `/quote_editor` load, check for pending blocks and append them to the canvas.

### 3.2 Navigation
Add "Quote Editor" link to main nav (visible to all authenticated users).

---

## Phase 4: Save / Load & Template Management

### 4.1 Save Quote
**UI:** "Save" button in right panel opens a simple modal with:
- Quote name (text input)
- Client name (optional, from session if available)
- Notes (optional)

**Backend:**
```sql
-- New table for saved quotes
CREATE TABLE IF NOT EXISTS saved_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,  -- NULL for session-based (pre-auth)
    form_template_id INTEGER NOT NULL,
    layout_id INTEGER,
    name TEXT NOT NULL,
    client_name TEXT,
    notes TEXT,
    blocks_json TEXT NOT NULL,
    settings_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (form_template_id) REFERENCES form_templates(id) ON DELETE CASCADE
);
```

**Endpoint:**
`POST /quote_editor/save-quote` -> returns `quote_id`

### 4.2 Load Quote
**UI:** "Load" button opens modal listing saved quotes (from `saved_quotes` table + session drafts).

**Endpoint:**
`GET /quote_editor/load-quote/<id>` -> returns full quote JSON -> replaces canvas blocks.

### 4.3 Save As Template
Creates a new `quote_editor_layouts` entry from current canvas state.

**Endpoint:**
`POST /quote_editor/layouts` with `{name, blocks_json, is_default=false}`

---

## Phase 5: Change Tracking & Red Dot System

### 5.1 Block Metadata
Each block in `blocks_json` stores:
```json
{
  "id": "form__index__client_address",
  "type": "form",
  "source_page": "index",
  "source_block_id": "index__client_address",
  "snapshot": {
    "label": "Address:",
    "value": "123 Main St",
    "captured_at": "2026-08-02T17:00:00Z"
  },
  "editor_overrides": {},
  "flags": {
    "source_dirty": false,
    "editor_dirty": false
  },
  "settings": {
    "margin_top": 8,
    "margin_bottom": 8,
    "padding": 12,
    "alignment": "left"
  }
}
```

### 5.2 Dirty Detection
On every block render:
1. Fetch current source value from `/quote_editor/source/<page>/<block_id>`
2. Compare with `block.snapshot.value`
3. If different -> set `source_dirty = true`, add red dot
4. If user edits content -> set `editor_dirty = true`, add amber dot

### 5.3 Left Column Display
For each block in canvas, left column shows:
- Block type icon
- Source page / block label
- Red dot + "Source changed" tooltip if `source_dirty`
- Amber dot + "Edited" tooltip if `editor_dirty`
- Green check if clean

Clicking a left-column item scrolls to and highlights the block in canvas.

---

## Phase 6: Export Implementation

### 6.1 PDF Export
**File:** `app/quote_editor_export.py`

```python
@quote_editor_export_bp.route('/api/quote-editor/export-pdf')
def export_pdf():
    layout_id = request.args.get('layout_id')
    layout = get_quote_editor_layout(layout_id=layout_id)
    blocks = layout['blocks_json']
    
    html = render_template('quote_editor_export.html', blocks=blocks)
    pdf = weasyprint.HTML(string=html).write_pdf()
    return send_file(BytesIO(pdf), mimetype='application/pdf', ...)
```

**Template:** `app/templates/quote_editor_export.html`
- Iterates blocks, applies per-block margins/padding/alignment
- Each block type has a macro:
  - `{% import '_quote_editor_macros.html' as macros %}`
  - `{{ macros.render_form_block(block) }}`
  - `{{ macros.render_calculator_block(block) }}`
  - etc.

### 6.2 DOCX Export
Same approach but using `python-docx`:
- Paragraph styles for notes
- Table for calculator/form data
- Inline images with `add_picture()`

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `app/template_store.py` | Modify | Add `quote_editor_layouts` table + CRUD helpers |
| `app/QMapp.py` | Modify | Register new routes and blueprints |
| `app/quote_editor_export.py` | Create | PDF/DOCX export endpoints |
| `app/quote_editor_routes.py` | Create | Image upload, source data, save/load quote APIs |
| `app/templates/user_output_editor.html` | Modify | Full 3-column layout |
| `app/templates/_image_gallery_modal.html` | Create | Image gallery partial |
| `app/templates/quote_editor_export.html` | Create | Export HTML template |
| `app/templates/_quote_editor_macros.html` | Create | Block render macros for export |
| `app/static/css/user_output_editor.css` | Modify | Complete editor styling |
| `app/static/js/user_output_editor.js` | Modify | Main editor logic, SortableJS init |
| `app/static/js/quote_editor_blocks.js` | Create | Block type definitions and renderers |
| `app/static/js/quote_editor_source_column.js` | Create | Left column source mapping + red dots |
| `app/static/js/quote_editor_gallery.js` | Create | Image gallery modal logic |
| `app/static/js/quote_editor_integration.js` | Create | Cross-mode "Add to Quote" hooks |
| `app/static/js/quote_editor_export.js` | Create | Export button handlers |
| `app/templates/form.html` | Modify | Add "Add to Quote" button |
| `app/templates/calculator.html` | Modify | Add "Add to Quote" button |
| `app/templates/image_upload.html` | Modify | Add "Add Images to Quote" button |
| `app/templates/_builder_macros.html` | Modify | Add nav link for Quote Editor |

---

## Dependencies to Add

```html
<!-- SortableJS via CDN in base template or user_output_editor.html -->
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
```

No new Python packages required (WeasyPrint and python-docx already used).

---

## Implementation Order

1. **Backend first:** DB table + basic CRUD routes + image upload
2. **Frontend skeleton:** 3-column HTML + SortableJS + basic block add/remove
3. **Block system:** All 5 block types render correctly in canvas
4. **Toolbar + formatting:** Text editing, alignment, margins/padding
5. **Source column:** Red dot dirty tracking
6. **Image gallery:** Modal + thumbnail selection + upload
7. **Export:** PDF then DOCX
8. **Integration:** Cross-mode buttons
9. **Save/Load:** Saved quotes + templates
10. **Polish:** Animations, error handling, responsive tweaks

---

## Testing Checklist

- [ ] Add/remove/reorder all 5 block types
- [ ] Drag and drop with SortableJS
- [ ] Text formatting (bold, italic, underline, headings)
- [ ] Image insertion inline and as image group
- [ ] Calculator block renders correct summary
- [ ] Form block captures page data correctly
- [ ] Red dot appears when source data changes
- [ ] Save layout, load layout, delete layout
- [ ] Save quote, load quote
- [ ] Export PDF preserves block order and styling
- [ ] Export DOCX preserves block order and styling
- [ ] Image upload from gallery works
- [ ] Cross-mode "Add to Quote" buttons work
- [ ] Navigation from all modes to Quote Editor
- [ ] Responsive layout on tablet (left/right panels collapse)
