# Theme Engine + Image Library Plan (Round 2)

## Goal
Extend the document-styles system (built in Round 1) into a full **theme engine**
with per-element typography, table styling, image framing, link styling, plus an
**image library** with tagging and Builder/Editor attachment. PDF-only functions
(anchor links, scroll vs page, sidebar nav) are explicitly **out of scope** this round.

## Decisions (confirmed with user)
- **Theme storage:** Per-layout, inside `settings_json.document_styles` (no new DB
  table). "Load Template = styles only" already reuses themes across quotes.
- **PDF-only functions:** Skipped.
- **Scope order:** (a) theme panel extension first, then image-library tagging +
  Builder attachment.
- **Image library location:** Library (upload/tag/search) lives in Image Manager
  mode; Builder/Editor *consume* it via the existing gallery picker modal. No
  duplicate upload UI in Builder.

---

## Part A — Theme Panel Extension

### A.1 New `document_styles` structure (superset of current)
```json
{
  "font_family": "Arial, sans-serif",
  "font_size_base": 16,
  "header_html": "...", "footer_html": "...",
  "header_font_size": 10, "footer_font_size": 8,
  "page_size": "A4",
  "margins": {"margin_top":20,"margin_bottom":20,"margin_left":25,"margin_right":25},
  "header_hide_on_cover": false, "footer_hide_on_cover": false,
  "typography": {
    "h1":  {"family":"","weight":"","size":24,"bold":false,"italic":false,"underline":false},
    "h2":  {"family":"","weight":"","size":20,"bold":false,"italic":false,"underline":false},
    "h3":  {"family":"","weight":"","size":18,"bold":false,"italic":false,"underline":false},
    "para":  {"family":"","weight":"","size":16,"bold":false,"italic":false,"underline":false},
    "notes": {"family":"","weight":"","size":14,"bold":false,"italic":false,"underline":false},
    "guide": {"family":"","weight":"","size":14,"bold":false,"italic":false,"underline":false}
  },
  "tables": {
    "border": "1px solid #ccc",
    "header_bg": "#f5f5f5",
    "row_bg": "#ffffff",
    "alt_row_bg": "#fafafa",
    "font_size": 14
  },
  "images": { "frame": "none", "shadow": false },
  "links":  { "color": "#0d6efd", "underline": true }
}
```
Empty string `family`/`weight` = inherit global. All keys optional (defaults applied
in export + preview).

### A.2 Files to modify
1. `app/static/js/user_output_editor.js`
   - Extend `documentStyles` default to include `typography`, `tables`, `images`,
     `links`, `header_hide_on_cover`, `footer_hide_on_cover`.
   - Extend `collectDocumentStyles()` to read new inputs.
   - Add UI tabs to the Styles modal: Typography (6 element rows), Tables, Images,
     Links. Each typography row: family select, weight select, size number,
     bold/italic/underline checkboxes.
2. `app/templates/user_output_editor.html`
   - Add modal tabs/panels: Typography, Tables, Images, Links (reuse `.styles-panel`
     pattern already in CSS).
3. `app/static/css/user_output_editor.css`
   - Add `.typography-row` grid layout; minor spacing for new panels.
4. `app/templates/quote_editor_export.html`
   - Inject `<style>` from theme: build per-element CSS for h1/h2/h3/p/notes/guide;
     table border/header bg/alt-row shading (use `nth-child(even)`); image frame +
     box-shadow; `a { color; text-decoration }`.
   - Honor `header_hide_on_cover` / `footer_hide_on_cover`: on the first page (`@page
     :first`) suppress the running header/footer when flag set.
5. `app/quote_editor_export.py`
   - Pass full `document_styles` (already does). Add a helper
     `_theme_css(document_styles)` returning a CSS string, render into template
     context as `theme_css`.
   - DOCX: apply typography weights/sizes to heading/paragraph runs where feasible
     (best-effort: size + bold; italic/underline via run flags; family already set).
6. `app/static/js/user_output_editor.js` (preview) — `renderPreviewPage()` should
   apply theme CSS classes so preview matches export (optional, best-effort).

### A.3 Fonts list (reuse Round 1 list)
System: Arial, Helvetica, Times New Roman, Georgia, Courier New, Verdana.
Google: Roboto, Open Sans, Lora, Merriweather, Montserrat, Poppins.
Weight options: normal, 300, 400, 500, 600, 700, bold.

---

## Part B — Image Library + Builder Attachment

### B.1 Tagging / categorisation (session-backed, no new DB table)
- Extend `quote_editor_routes.py` `/quote_editor/upload-image`: accept `tags`
  (comma string) + `category` form fields; store on `session['quote_editor_images']`
  entry: `{url, filename, original_name, tags:[], category:""}`.
- Extend `/quote_editor/images` GET: return tags/category; support
  `?tag=&category=&q=` filters.
- Gallery modal JS (`user_output_editor.js` `openGalleryModal`): add filter bar
  (search input + tag/category dropdowns) built from current image set; clicking a
  tag filters grid.

### B.2 Builder attachment to category blocks
- Category blocks in Builder (`builder_beta`) get an optional `image_url` /
  `image_meta` on the block's `standard` (or a new `category_options` dict).
- `builder_properties.html`: for `line_items_by_category` blocks add an
  "Attach Image" button that opens the **same gallery picker** (reuse
  `openGalleryModal`). On select, store image URL on the block.
- When the form is completed and blocks flow into the Quote Editor
  (`add_form_block` in `quote_editor_routes.py`), carry the category image into the
  generated `category_title` block snapshot as `snapshot.category_image`, rendered in
  export + editor as a small header image above the category title.
- Gallery picker must be callable from Builder context too — extract
  `openGalleryModal` into a shared JS module or duplicate a thin wrapper in
  `builder_beta.html` JS. **Decision:** keep one gallery modal in the Quote Editor;
  Builder opens it via a lightweight event/listener bridge (postMessage or a shared
  `window.QuoteGallery` object) to avoid duplicating markup. If Builder is a separate
  page, expose the picker through a tiny shared script `static/js/gallery_picker.js`.

### B.3 Files to modify
- `app/quote_editor_routes.py` — upload-image (tags/category), images GET (filters).
- `app/templates/user_output_editor.html` + JS — gallery filter UI.
- `app/templates/partials/builder_properties.html` — category image attach control.
- `app/static/js/builder_beta.js` (or equivalent) — wire attach button to shared
  gallery picker.
- `app/quote_editor_routes.py` `add_form_block` — propagate category image.
- `app/templates/quote_editor_export.html` + `user_output_editor.js` — render
  `category_image` above category title.

---

## Validation
1. Set typography for h1/h2/para (different sizes/weights/bold) → export PDF, verify
   each element renders with its style.
2. Set table border + alt-row shading + header bg → export, verify.
3. Set image frame + shadow → insert image block → export, verify.
4. Set link color → export with a hyperlink block, verify.
5. Toggle header/footer hide-on-cover → 2-page doc, verify cover lacks header/footer.
6. Upload image with tags "kitchen,bathroom" + category "Site" → gallery filter by
   tag returns only it.
7. In Builder, attach image to a category block → complete form → Quote Editor shows
   category image above title.
8. Reuse via "Load Template (styles only)" preserves content, applies new theme.

## Risks
- `nth-child(even)` alt-row shading depends on table structure staying consistent.
- Builder/Editor are separate pages → shared gallery picker needs a small shared JS
  module; avoid copy-paste markup.
- DOCX typography fidelity is limited (no per-run font family easily); best-effort.

## Environment Fix (2026-08-07)
- App venv is Python 3.9. weasyprint was 59.0 + pydyf 0.11.0 → broken
  (`pydyf.PDF()` signature mismatch). Resolved by pinning **weasyprint==53.0**
  (works with pydyf 0.11.0 on py3.9). Full-theme PDF (typography/tables/images/
  links/header-footer/page-numbers) validated at runtime: 19,868 bytes.
- Boot smoke-test: `PORT=5305 python app/QMapp.py` → `/quote_editor` 200,
  `/api/quote-editor/export-pdf` 200, `/api/quote-editor/export-docx` 200.
- Note: QMapp `--port` arg is ignored; use `PORT` env var to choose port.
  Port 5000 is held by macOS ControlCenter (unrelated) — avoid it.
- `category_templates` gained `image_url` column (schema + DB migrated).

