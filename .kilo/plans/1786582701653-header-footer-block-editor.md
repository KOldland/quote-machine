# Simplified Header/Footer Tool — Implementation Plan

## Goal

Replace the raw HTML textarea in the Theme panel's Header/Footer tabs with a visual, drag-and-drop block editor that non-technical users can operate without touching HTML.

## Current State

- Header tab has: HTML textarea (`docHeaderHtml`), font size input, hide-on-cover checkbox
- Footer tab has: HTML textarea (`docFooterHtml`), font size input, hide-on-cover checkbox
- `documentStyles` stores `header_html` / `footer_html` as raw strings
- PDF export renders them directly (`quote_editor_export.html` line 82)
- DOCX export renders them via `_replace_placeholders` (`quote_editor_export.py` line 229)
- On-screen preview modal does **not** render header/footer at all

## Target State

Header and footer are defined as ordered arrays of field blocks. A visual editor (reusing the editor's existing drag-and-drop and gallery patterns) lets users assemble them. Exports render from the structured data.

## Data Model

### New `documentStyles` shape

```js
// OLD
header_html: '<div>Quote Ref: {{quote_ref}}</div>'
footer_html: '<div>Page {{page_num}}</div>'

// NEW
header_fields: [
  { id: 'f_1', type: 'variable', key: 'quote_ref', label: 'Quote Ref:' },
  { id: 'f_2', type: 'variable', key: 'client_name', label: '' },
]
footer_fields: [
  { id: 'f_1', type: 'variable', key: 'page_number', label: 'Page' },
  { id: 'f_2', type: 'text', content: ' | Grand Total: ' },
  { id: 'f_3', type: 'variable', key: 'grand_total', label: '' },
]
```

Keep `header_hide_on_cover` / `footer_hide_on_cover` as booleans.

Remove `header_html` / `footer_html` from `documentStyles` after migration.

### Field types

| type | key examples | behaviour |
|------|-------------|-----------|
| `variable` | `quote_ref`, `client_name`, `date`, `page_number`, `grand_total`, `company_name` | Renders the resolved value at export/preview time |
| `text` | — | Static text the user types inline |
| `image` | — | Image from gallery (for logo in header) |
| `spacer` | — | Flexible horizontal space (margin/push) |

## Migration

On first load after deployment, if `documentStyles.header_html` is non-empty, convert it to `header_fields` array. Heuristic: scan for `{{key}}` patterns, create `variable` fields for each, wrap remaining text in `text` fields. Same for `footer_html`.

If conversion fails or produces empty fields, leave `header_fields: []` (blank header).

## Header/Footer Editor UI

### Tab layout

Replace the current textarea in both Header and Footer tabs with:

```
┌─────────────────────────────────────────────┐
│  Header Fields                          [+]  │
│                                             │
│  [Quote Ref: _____]  [X]   ← draggable     │
│  [Acme Ltd]          [X]   ← draggable     │
│                                             │
│  ─── Palette ────────────────────────────   │
│  [+ Variable] [+ Text] [+ Image] [+ Spacer] │
│                                             │
│  ☐ Hide header on cover page                │
│  [Apply]  [Save]  [Cancel]                  │
└─────────────────────────────────────────────┘
```

### Interactions

- **Add field:** Click palette button → field appended to end of header/footer
- **Reorder:** Drag handle on each field block (reuse Sortable.js pattern)
- **Remove:** X button on each field block
- **Edit variable:** Click field → dropdown to select which variable key, label input for prefix text
- **Edit text:** Click field → inline text input
- **Edit image:** Click field → opens gallery picker (reuse `openGalleryModal`)
- **Spacer:** No editing needed, just draggable width

### Live preview

As the user builds the header/footer, a live preview strip at the top of the tab shows how it will look. Variables show as grey placeholders (e.g., `[quote_ref]`) in the editor; real values are substituted at export/preview time.

## Export Integration

### PDF (`quote_editor_export.html`)

Replace the raw `{{ document_styles.header_html }}` block with a Jinja2 loop over `header_fields`:

```html
{% if document_styles and document_styles.header_fields %}
  <div class="doc-header">
    {% for field in document_styles.header_fields %}
      {% if field.type == 'variable' %}
        {{ field.label }}{{ field.key | placeholder }}
      {% elif field.type == 'text' %}
        {{ field.content }}
      {% elif field.type == 'image' %}
        <img src="{{ field.url }}" ...>
      {% elif field.type == 'spacer' %}
        <span class="header-spacer"></span>
      {% endif %}
    {% endfor %}
  </div>
{% endif %}
```

### DOCX (`quote_editor_export.py`)

Iterate over `header_fields` array, appending runs/paragraphs to the header paragraph. Variable values resolved from `blocks` data (same as `_replace_placeholders` does now).

### Preview modal (`user_output_editor.js` — `renderPreviewPage`)

Add header/footer rendering using the same field-iteration logic. Resolve variables from `documentStyles` or current page context. Respect `header_hide_on_cover` on page index 0.

## Files Changed

| File | Change |
|------|--------|
| `app/static/js/user_output_editor.js` | New `header_fields` / `footer_fields` in `documentStyles`; new `renderHeaderFields` / `renderFooterFields` functions; replace textarea in Header/Footer tabs with block editor UI; `collectDocumentStyles` / `updateStylesFormFromDocumentStyles` updated; migration from old `header_html` |
| `app/templates/user_output_editor.html` | Replace `docHeaderHtml` / `docFooterHtml` textareas with block editor containers + palette buttons |
| `app/static/css/user_output_editor.css` | Styles for header/footer field blocks, palette, live preview strip, drag handles |
| `app/templates/quote_editor_export.html` | Replace raw `header_html` / `footer_html` with Jinja2 loops over `header_fields` / `footer_fields` |
| `app/quote_editor_export.py` | Replace raw `header_html` / `footer_html` string handling with field-array iteration for DOCX |

## Validation

1. Header tab: add a variable field → select "Quote Ref" → save → reload → field persists
2. Add image field → select from gallery → save → reload → image persists
3. Reorder fields by dragging → save → order preserved
4. Preview modal: header renders with resolved values
5. PDF export: header renders with resolved values + page numbers
6. DOCX export: header renders with resolved values
7. Hide-on-cover: page 1 of PDF has no header when checked
8. Migration: load a quote with old `header_html` → fields are created automatically

## Out of Scope

- Footer works the same as header (same field types, same drag-and-drop UX)
- Per-side (left/center/right) alignment — left-aligned only for now
- Per-field font/size overrides — uses document-level typography
- Anchor links, continuous scroll, sidebar nav (PDF-only features from the larger themes discussion — deferred)
- Image library tagging/search (separate feature)

## Key Risk

The DOCX export path is the hardest to get right — python-docx's header/footer paragraph model is limited. If field-array rendering proves too complex in DOCX, fallback is to generate the HTML string from the field array and use the same string-based approach currently in `_replace_placeholders`.
