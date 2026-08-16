# Header/Footer Position Fix — Quote Editor Preview

## Problem
The "Header Position" / "Footer Position" dropdowns (Narrow/Standard/Wide = 5/10/20px) are
labeled as *position* but currently drive the inline **inner padding** of an element that is
`position:absolute` and flush to the page edge (`top:0` for header, `bottom:0` for footer,
hard-coded in CSS). Changing inner padding on a flush element produces no visible movement,
so the dropdown appears to do nothing.

- Listener is correctly wired: `user_output_editor.js:1803-1804` → `collectDocumentStyles()` → `renderPreviewPage()` (re-renders header/footer HTML at lines 1275/1298).
- JS applies inline `padding:${padding}px ...` at lines 1315 (header) and 1348 (footer), where `padding = hdr.preset_padding` / `ftr.preset_padding`.
- CSS `.preview-header` (line 1056) and `.preview-footer` (line 1065) hard-code `left:72px; right:72px; top:0` / `bottom:0` plus their own `padding-bottom:8px` / `padding-top:8px`.

## Decision
The dropdown controls **distance of the header/footer from the page edge** (user-confirmed):
- Header: `top` offset = preset value (15/40/80px from page top).
- Footer: `bottom` offset = preset value (15/40/80px from page bottom).
- Keep `preset_padding` as the persisted field name (so saved `document_styles` stay compatible) but render it as the edge offset, not inner padding.

## Changes

### 1. `app/static/js/user_output_editor.js`
- `renderPreviewHeader()` (~line 1315): replaced
  `padding:${padding}px ${mr}px ${padding}px ${ml}px;` with
  `top:${padding}px; left:${ml}px; right:${mr}px;` (drop the static `top:0` reliance; position now driven by inline style). Keep `font-size:${fs}px;`. Inner `padding-bottom` separator gap stays via CSS.
- `renderPreviewFooter()` (~line 1348): replaced
  `padding:${padding}px ${marginRight}px ${padding}px ${marginLeft}px;` with
  `bottom:${padding}px; left:${marginLeft}px; right:${marginRight}px;`.
- `padding` variable (lines 1311 / 1344) is now the edge offset = `hdr.preset_padding` / `ftr.preset_padding`.
- `collectDocumentStyles()` (lines 933 / 942): stores `preset_padding` from `docHeaderPreset` / `docFooterPreset`; fallback defaults updated to 15 (header) and 40 (footer).
- `populateHeaderFooterFields()` (~lines 1614 / 1653): load fallbacks updated to 15 / 40 to match render defaults.

### 2. `app/static/css/user_output_editor.css`
- `.preview-header` (line 1056): removed hard-coded `top:0; left:72px; right:72px;` and the `padding-bottom:8px` (position now set inline by JS). Kept `position:absolute; border-bottom:1px solid #eee;`.
- `.preview-footer` (line 1065): removed hard-coded `bottom:0; left:72px; right:72px;` and `padding-top:8px`. Kept `position:absolute; border-top:1px solid #eee;`.
- Left/right are now derived from page margins (inline `ml`/`mr`), so the 72px magic number is gone and headers/footers track the actual margin settings.

## Edge cases
- `preset_padding` default: header fallback `15` (Standard) in render and collect; footer fallback `40` (Standard).
- `hide_on_cover` logic and `enabled` checks (lines 1305 / 1341) are untouched and still gate rendering.
- Export/output generation: this fix is preview-only; no change to server-side render.

## Validation
- `node --check app/static/js/user_output_editor.js` (no syntax errors).
- Flask restarted (kill `lsof -ti:5003`, run `app/start_flask.sh`), open http://127.0.0.1:5003/.
- In Quote Editor → Styles → Header/Footer: change Position dropdown and confirm the header visibly moves down from the top / footer visibly moves up from the bottom in the preview. Preset values: Narrow=15, Standard=40, Wide=80 (px).
- Confirm left/right of header/footer follow the page Margin Left/Right inputs (no longer pinned at 72px).
- Confirm selection persists after Save (reload editor, re-open Styles modal).
