# Category Audit: Original Prototype / Client Zero Template

## Overview
This document lists all categories from the original prototype, cross-referenced against:
- `docs/Plus Rooms Live input - Sheet3.csv` (the complete dataset)
- `QMapp.py.bak.py` (the original route handlers)
- `form.html.bak.html` (the original template)
- Current `page_schemas.json` (what exists in the new system)

---

## Category List

### 1. Special Notes <---- DONE>
- **Page**: `special_notes_page`
- **Type**: Checkbox group
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 2. Dimensions <---- Skip>
- **Page**: `summary_page`
- **Type**: Number inputs
- **Line Codes**: `dm1@`, `dm2@`, `dm3@`, `dm4@`, `dm5@`, `lwx`
- **Anomalies**: Manual number inputs (extension size, rear depth, wall width, side return, sliding door width, lightwell)
- **Status**: ⚠️ Needs `number_input` line items

### 3. Neighbours
- **Page**: `summary_page`
- **Type**: Text inputs
- **Line Codes**: `nb1#`, `nb2#`
- **Anomalies**: Manual text inputs (left/right neighbour door numbers)
- **Status**: ⚠️ Needs `text_input` line items

### 4. Boundary Line
- **Page**: `summary_page`
- **Type**: Toggle checkbox + multi-select dropdown
- **Line Codes**: `bll` (left), `blr` (right), `bl1^`-`bl6^` (left options), `bl7^`-`bl12^` (right options)
- **Anomalies**: `bll`/`blr` toggles reveal multi-select dropdowns
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdown items

### 5. Basement
- **Page**: `summary_page`
- **Type**: Standalone checkboxes
- **Line Codes**: `bs1@`, `bs2@`
- **Anomalies**: Yes/No checkboxes (mutually exclusive in UI)
- **Status**: ⚠️ Needs `checkbox` line items with logic

### 6. Council area
- **Page**: `summary_page`
- **Type**: Dropdown + text input
- **Line Codes**: `cs1`-`cs7` (options), `cs0` (Other)
- **Options**: Camden, Ealing, Lambeth, Merton, Richmond, Southwark, Wandsworth, Other
- **Anomalies**: Single-select dropdown; `cs0` = "Other" reveals text input
- **Status**: ⚠️ Needs `dropdown_select` line item + `option_items`

### 7. Conservation status
- **Page**: `summary_page`
- **Type**: Standalone checkboxes
- **Line Codes**: `cs8^`, `cs9^`
- **Anomalies**: Yes/No checkboxes
- **Status**: ⚠️ Needs `checkbox` line items

### 8. Planning permission
- **Page**: `summary_page`
- **Type**: Dropdown (single-select)
- **Line Codes**: `ppx` (header), `pp1@`-`pp8@` (options)
- **Anomalies**: Single-select dropdown
- **Status**: ⚠️ Needs `dropdown_select` line item + `option_items`

### 9. Building works
- **Page**: `summary_page`
- **Type**: Checkbox group + toggle + text input
- **Line Codes**: `bw1^`-`bw23^` (options), `bw4^` (toggle), `lwx` (text)
- **Anomalies**: `bw4^` "Create a courtyard/lightwell" reveals `lwx` text input
- **Status**: ⚠️ Needs `checkbox_toggle` for `bw4^` + child `text_input` for `lwx`

### 10. External wall finish & height
- **Page**: `materials_page`
- **Type**: Checkbox group + toggle + 2 dropdowns
- **Line Codes**: `ew1^`-`ew3^` (options), `ew0` (toggle), `ew4` (metres dropdown), `ew5` (cm dropdown)
- **Anomalies**: `ew0` toggle reveals `ew4` (2m, 3m) and `ew5` (0-95cm in 5cm steps) — **hardcoded in template**
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdowns

### 11. External roofing finish
- **Page**: `materials_page`
- **Type**: Checkbox group + toggle + dropdown + text
- **Line Codes**: `er1#` (toggle), `er2#` (flat roof), `er3#` (facia), `er4^`-`er7^` (dropdown options)
- **Anomalies**: `er1#` toggle reveals roofing finish dropdown; `er7^` = "Other" reveals text input
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdown + text

### 12. Floor structure
- **Page**: `further_requirements_page`
- **Type**: Checkbox group
- **Line Codes**: `fs1#`-`fs4#`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 13. Plastering
- **Page**: `materials_page`
- **Type**: Checkbox group
- **Line Codes**: `ps1#`-`ps3#`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 14. Internal doors
- **Page**: `materials_page`
- **Type**: Checkbox group + number inputs
- **Line Codes**: `id1^`, `id4^` (checkboxes), `pd4^` (fire doors count), `pd5^` (non-fire doors count)
- **Anomalies**: `pd4^`/`pd5^` are number inputs for door counts
- **Status**: ⚠️ Needs `number_input` line items

### 15. Drainage
- **Page**: `materials_page`
- **Type**: Checkbox group + toggle + text + number
- **Line Codes**: `dr1^`-`dr3^` (checkboxes), `dr4^` (toggle), `dra` (text), cost
- **Anomalies**: `dr4^` toggle reveals text input + cost input
- **Status**: ⚠️ Needs `checkbox_toggle` + child text + number

### 16. Waste & Parking
- **Page**: `materials_page`
- **Type**: Checkbox group
- **Line Codes**: `wp1#`-`wp3#`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 17. Further Requirements & Considerations
- **Page**: `further_requirements_page`
- **Type**: Checkbox group
- **Line Codes**: `frc1#`-`frc20#`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 18. Demolition Works
- **Page**: `further_requirements_page`
- **Type**: Toggle + dropdown + text + number
- **Line Codes**: `dw0` (toggle), `dw1#`-`dw3#` (dropdown), `dw6#` (Other), `dw4#` (garden wall), `dw7`-`dw10` (floor retention)
- **Anomalies**: `dw0` toggle reveals dropdown; `dw6#` = "Other" reveals text + cost; `dw7`-`dw10` are standalone checkboxes
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdown + text + number

### 19. Rear Reception Opening
- **Page**: `further_requirements_page`
- **Type**: Toggle + dropdown
- **Line Codes**: `rro0` (toggle), `rro1`-`rro7` (options)
- **Anomalies**: `rro0` toggle reveals dropdown of rear reception options
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdown

### 20. Internal Walls
- **Page**: `further_requirements_page`
- **Type**: Checkbox + sqm/fixed inputs
- **Line Codes**: `iw1#`-`iw6#`
- **Anomalies**: Each checkbox reveals a choice between sqm input or fixed cost input
- **Status**: ⚠️ Needs `checkbox` + child `number_input` with type selector

### 21. Additional Building Items
- **Page**: `additional_building_work_page`
- **Type**: Checkbox group (sub-grouped into accordions)
- **Line Codes**: `ab1#`-`ab18#`
- **Anomalies**: Sub-grouped into Chimney Breasts, Rear Reception, WC, Concealment, Other
- **Status**: ⚠️ Needs sub-category grouping

### 22. Schedule of works
- **Page**: `schedule_of_works_page` (NOT YET CREATED)
- **Type**: Checkbox group
- **Line Codes**: `sww*`, `tww*`
- **Anomalies**: Missing page entirely
- **Status**: ❌ Page not in current system

### 23. Pricing category
- **Page**: `schedule_of_works_page` / `standard_items_page` (NOT YET CREATED)
- **Type**: Display only (output formatting)
- **Line Codes**: `pc1`-`pc10`
- **Anomalies**: These are output document formatting markers, not form inputs
- **Status**: ❌ Not applicable to form

### 24. Standard item
- **Page**: `standard_items_page` (NOT YET CREATED)
- **Type**: Checkbox group
- **Line Codes**: `si1^`-`si46^`
- **Anomalies**: Missing page entirely
- **Status**: ❌ Page not in current system

### 25. Electrics
- **Page**: `additional_costs_page`
- **Type**: Toggle + dropdown + number inputs
- **Line Codes**: `elk1` (kitchen toggle), `elk2`-`elk5` (kitchen options), `elk0` (custom), `elkl0` (lights), `elkp0` (points), `ell1` (loft toggle), `ell2`-`ell5` (loft options), `ell0` (custom), `elll0` (lights), `ellp0` (points)
- **Anomalies**: Kitchen/Loft toggles reveal dropdowns; "Other" option reveals manual light/point counts
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdown + number inputs

### 26. Plumbing
- **Page**: `additional_costs_page`
- **Type**: Checkbox group
- **Line Codes**: `pl1`-`pl14`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 27. Skylights
- **Page**: `additional_costs_page`
- **Type**: Toggle + dropdown + checkboxes
- **Line Codes**: `sk0` (toggle), `sk1`-`sk10` (options)
- **Anomalies**: `sk0` toggle reveals dropdown + additional checkboxes
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdown + checkboxes

### 28. Velux
- **Page**: `additional_costs_page`
- **Type**: Checkbox group
- **Line Codes**: `vl1@`-`vl5`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 29. Sliding doors
- **Page**: `additional_costs_page`
- **Type**: Dropdown + text input
- **Line Codes**: `sd1@`-`sd99@` (options), `pd10` (area input)
- **Anomalies**: Single-select dropdown for door style/size; `pd10` text input for door area
- **Status**: ⚠️ Needs `dropdown_select` + `text_input`

### 30. Totals
- **Page**: Output only
- **Type**: Display
- **Anomalies**: Calculated values, not form inputs
- **Status**: ✅ Handled by calculator

### 31. Price breakdowns
- **Page**: Output only
- **Type**: Display
- **Anomalies**: Calculated values, not form inputs
- **Status**: ✅ Handled by calculator

### 32. Glass valley
- **Page**: `further_requirements_page`
- **Type**: Checkbox group
- **Line Codes**: `gv1`-`gv2`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 33. Sash Windows
- **Page**: NOT IN CURRENT SYSTEM
- **Type**: Unknown
- **Line Codes**: Unknown
- **Anomalies**: Category exists in original but no data found
- **Status**: ❌ Missing from all sources

### 34. Aluminum Capping
- **Page**: `additional_costs_page`
- **Type**: Checkbox group
- **Line Codes**: `ac1`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 35. Contingency
- **Page**: NOT IN CURRENT SYSTEM
- **Type**: Unknown
- **Line Codes**: Unknown
- **Anomalies**: Category exists in TITLE_MAPPING but no data found
- **Status**: ❌ Missing from all sources

### 36. Optional Extras
- **Page**: `optional_extras_page`
- **Type**: Checkbox group + toggle + dropdown
- **Line Codes**: `oe1`-`oeN`, `oe111`-`oe112` (chimney options)
- **Anomalies**: `oe1` toggle reveals chimney breast dropdown
- **Status**: ⚠️ Needs `checkbox_toggle` + child dropdown

### 37. Finishing Works
- **Page**: `optional_extras_page`
- **Type**: Toggle + dropdown (multiple sections)
- **Line Codes**: `fw1@`-`fw6@` (toggles), `fw12`-`fw63` (options)
- **Anomalies**: Each `fw*@` toggle reveals a dropdown of finishing options (Kitchen, Utility, Bathroom, Rear Reception Half, Rear Reception Full)
- **Status**: ⚠️ Needs multiple `checkbox_toggle` + child dropdowns

### 38. Finishing Works Optional Extras
- **Page**: `optional_extras_page`
- **Type**: Checkbox group
- **Line Codes**: `foe*`
- **Anomalies**: None
- **Status**: ✅ Pure checkbox group

### 39. Additional Notes
- **Page**: NOT IN CURRENT SYSTEM (was `twenty_eighth_page`)
- **Type**: Text inputs
- **Line Codes**: `an1`-`an7`
- **Anomalies**: Manual text inputs for various notes
- **Status**: ❌ Page not in current system

---

## Summary

| Status | Count | Categories |
|--------|-------|------------|
| ✅ Pure checkbox (no changes needed) | 12 | Special Notes, Floor Structure, Plastering, Waste & Parking, Further Requirements, Plumbing, Velux, Glass Valley, Aluminum Capping, Finishing Works Optional Extras, Pricing Category (output), Totals (output) |
| ⚠️ Needs special handling | 20 | Dimensions, Neighbours, Boundary Line, Basement, Council, Conservation, Planning Permission, Building Works, External Wall, External Roofing, Internal Doors, Drainage, Demolition Works, Rear Reception Opening, Internal Walls, Additional Building Items, Electrics, Skylights, Sliding Doors, Optional Extras, Finishing Works |
| ❌ Missing from system | 5 | Schedule of Works, Standard Items, Sash Windows, Contingency, Additional Notes |