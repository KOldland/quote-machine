"""
Phase 2 — Sub-question Migration
Populates sub_blocks[] on accordion_group blocks in page_schemas.json and
page_schemas_published.json with the sub-questions discovered in form.html / QMapp.py.

Safe to re-run: existing sub_blocks are replaced only if the script-defined list differs.
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Sub-block definitions keyed by parent accordion block id
# ---------------------------------------------------------------------------
SUB_BLOCK_MAP = {
    # External Walls → wall height metres + centimetres selects
    "materials_page__selected_ew": [
        {
            "id": "materials_page__ew_wall_height_metres",
            "block_type": "dropdown_select",
            "standard": {
                "label": "Wall Height — Metres",
                "name": "wall_height_metres",
                "required": False,
                "trigger_value": "ew0",
                "dropdown_choices": ["2m", "3m"],
                "help_text": "Shown when 'External Wall Height' checkbox (ew0) is selected"
            }
        },
        {
            "id": "materials_page__ew_wall_height_centimetres",
            "block_type": "dropdown_select",
            "standard": {
                "label": "Wall Height — Centimetres",
                "name": "wall_height_centimetres",
                "required": False,
                "trigger_value": "ew0",
                "dropdown_choices": [
                    "0cm","5cm","10cm","15cm","20cm","25cm","30cm",
                    "35cm","40cm","45cm","50cm","55cm","60cm","65cm",
                    "70cm","75cm","80cm","85cm","90cm","95cm"
                ],
                "help_text": "Shown when 'External Wall Height' checkbox (ew0) is selected"
            }
        }
    ],

    # External Roof → pitched roof finish dropdown + 'other' text input
    "materials_page__selected_er": [
        {
            "id": "materials_page__er_pitched_roof_option",
            "block_type": "dropdown_select",
            "standard": {
                "label": "Choose Roofing Finish",
                "name": "pitched_roof_option",
                "required": False,
                "trigger_value": "er1#",
                "source_codes": ["er4^", "er5^", "er6^", "er7^"],
                "help_text": "Shown when Pitched Roof checkbox (er1#) is selected"
            }
        },
        {
            "id": "materials_page__er_other_roofing_description",
            "block_type": "text_input",
            "standard": {
                "label": "Other Roofing — Please Specify",
                "name": "other_roofing_description",
                "required": False,
                "trigger_value": "er7^",
                "help_text": "Shown when 'Other' (er7^) is selected in roofing finish"
            }
        }
    ],

    # Internal Doors → fire door count + non-fire door count
    "materials_page__selected_id": [
        {
            "id": "materials_page__id_fire_doors_number",
            "block_type": "number_input",
            "standard": {
                "label": "Number of Fire Doors",
                "name": "fire_doors_number",
                "required": False,
                "min": 0,
                "help_text": "Maps to session key fire_doors_number"
            }
        },
        {
            "id": "materials_page__id_non_fire_doors_number",
            "block_type": "number_input",
            "standard": {
                "label": "Number of Non-Fire Doors",
                "name": "non_fire_doors_number",
                "required": False,
                "min": 0,
                "help_text": "Maps to session key non_fire_doors_number"
            }
        }
    ],

    # Drainage Works → 'other' description text + cost
    "materials_page__selected_dr": [
        {
            "id": "materials_page__dr_drainage_other_input",
            "block_type": "text_input",
            "standard": {
                "label": "Drainage details",
                "name": "drainage_other_input",
                "required": False,
                "trigger_value": "dr4^",
                "help_text": "Shown when 'Specify other drainage works' (dr4^) is selected"
            }
        },
        {
            "id": "materials_page__dr_drainage_other_cost",
            "block_type": "number_input",
            "standard": {
                "label": "Additional Drainage Cost (£)",
                "name": "drainage_other_cost",
                "required": False,
                "trigger_value": "dr4^",
                "min": 0,
                "step": 0.01,
                "help_text": "Cost for 'other' drainage work"
            }
        }
    ]
}


def migrate(schema_path: pathlib.Path) -> int:
    data = json.loads(schema_path.read_text())
    pages = data.get("builder_beta", {}).get("pages", {})
    updated = 0

    for page in pages.values():
        for block in page.get("blocks", []):
            bid = block.get("id", "")
            if bid in SUB_BLOCK_MAP:
                new_sub = SUB_BLOCK_MAP[bid]
                if block.get("sub_blocks") != new_sub:
                    block["sub_blocks"] = new_sub
                    updated += 1

    schema_path.write_text(json.dumps(data, indent=2))
    return updated


for fname in ["page_schemas.json", "page_schemas_published.json"]:
    p = REPO / fname
    if p.exists():
        n = migrate(p)
        print(f"  OK — {n} accordion(s) updated with sub_blocks → {fname}")
    else:
        print(f"  SKIP — {fname} not found")
