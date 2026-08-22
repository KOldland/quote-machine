"""
Quote Machine — Calculator Engine (Phase 2)

Core calculation pipeline for quotes:
1. Fetch base prices from line_items table
2. Apply user overrides if allow_user_override=1
3. Compute line totals grouped by output_group
4. Apply quote-level adjustments (discounts/markups)
5. Compute grand total and payment schedule
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "template_store.sqlite3"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def calculate_quote(
    template_key: str,
    form_data: dict[str, Any] | None = None,
    session_overrides: dict[str, Any] | None = None,
    follow_up_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Calculate a complete quote for a given template.

    Parameters
    ----------
    template_key : str
        The form template key (e.g. 'standard_build').
    form_data : dict or None
        Submitted form values keyed by question line_code.
    session_overrides : dict or None
        User price overrides keyed by question_id (int).
        Structure: { 'overrides': {<question_id>: <value>}, 'deposit_pct': float, 'completion_pct': float }

    Returns
    -------
    dict with keys:
        groups : list of output_group dicts
        subtotals : dict {group_name: subtotal}
        adjustments : list of adjustment dicts
        grand_total : float
        deposit_pct : float
        completion_pct : float
        deposit_amount : float
        completion_amount : float
        middle_balance : float
        items : list of individual line item dicts (flat)
    """
    conn = _get_connection()
    try:
        # ── 1. Fetch all line_items for this template ──────────────────────
        page_rows = conn.execute(
            "SELECT page_key FROM page_templates WHERE form_template_version_id IN "
            "(SELECT id FROM form_template_versions WHERE form_template_id = "
            "(SELECT id FROM form_templates WHERE key = ?))",
            (template_key,),
        ).fetchall()
        page_keys = [r["page_key"] for r in page_rows] if page_rows else [template_key]
        placeholders = ",".join("?" for _ in page_keys)
        cursor = conn.execute(
            f"""
            SELECT id, line_code, category, internal_description,
                   unit_cost, units, output_title, output_notes, output_guidance,
                   output_group, pricing_visibility, allow_user_override,
                   include_default, sort_order, form_page, quantity_source
            FROM line_items
            WHERE form_page IN ({placeholders})
            ORDER BY output_group, sort_order, line_code
            """,
            page_keys,
        )
        rows = cursor.fetchall()

        # ── 2. Build items list with overrides applied ─────────────────────
        overrides = (session_overrides or {}).get("overrides", {})
        items: list[dict[str, Any]] = []
        groups: dict[str, list[dict[str, Any]]] = {}

        for row in rows:
            item = dict(row)
            question_id = item["id"]
            base_cost = float(item["unit_cost"] or 0)
            units = float(item["units"] or 1)

            # If quantity_source is set, use the follow-up answer as units
            qty_source = item.get("quantity_source")
            if qty_source and isinstance(follow_up_data, dict):
                fu_val = follow_up_data.get(qty_source)
                if fu_val is not None and str(fu_val).strip() not in ("", "0", "off", "false", "N", "No"):
                    try:
                        units = float(fu_val)
                    except (TypeError, ValueError):
                        pass

            # Apply user price override if present (API-driven overrides bypass allow_user_override)
            if str(question_id) in overrides:
                override_val = overrides[str(question_id)]
                try:
                    user_price = float(override_val)
                    line_total = user_price
                    item["overridden"] = True
                    item["override_source"] = "user"
                    item["unit_cost"] = user_price
                except (TypeError, ValueError):
                    line_total = base_cost * units
                    item["overridden"] = False
                    item["unit_cost"] = base_cost
            else:
                line_total = base_cost * units
                item["overridden"] = False
                item["unit_cost"] = base_cost

            item["units"] = units
            item["line_total"] = round(line_total, 2)

            # Only include visible or priced items
            if item.get("pricing_visibility") != "hidden":
                group_name = item.get("output_group") or "General"
                groups.setdefault(group_name, []).append(item)
                items.append(item)

        # ── 3. Compute subtotals per output_group ──────────────────────────
        subtotals: dict[str, float] = {}
        group_data: list[dict[str, Any]] = []
        for gname, gitems in groups.items():
            gsub = round(sum(it["line_total"] for it in gitems), 2)
            subtotals[gname] = gsub
            group_data.append(
                {
                    "name": gname,
                    "subtotal": gsub,
                    "line_items": gitems,
                }
            )

        # ── 4. Apply quote adjustments (from session or defaults) ──────────
        adjustments: list[dict[str, Any]] = []
        adjustment_total = 0.0

        # ── 5. Compute totals ──────────────────────────────────────────────
        subtotal = round(sum(subtotals.values()), 2)
        grand_total = round(subtotal + adjustment_total, 2)

        # ── 6. Payment schedule (client business rules) ────────────────────
        import template_store as ts
        ps_settings = ts.get_payment_schedule_block(template_key)

        optional_codes = set(
            code.lower()
            for code in ps_settings.get("optional_line_codes", ["pl6", "glazing"])
        )
        temp_kitchen_code = ps_settings.get("temp_kitchen_line_code", "pl6")
        temp_kitchen_cost = float(ps_settings.get("temp_kitchen_cost", 250.0))
        glazing_cost = float(ps_settings.get("glazing_cost", 500.0))

        selected_codes = set()
        if form_data:
            for key, val in form_data.items():
                if val and str(val).strip() not in ("0", "off", "false", "N", "No"):
                    selected_codes.add(key.strip().lower())

        def _is_optional(item: dict) -> bool:
            return item.get("line_code", "").lower() in optional_codes

        basic_build_items = [it for it in items if not _is_optional(it)]
        basic_build = round(sum(it["line_total"] for it in basic_build_items), 2)

        initial_pct = float(ps_settings.get("initial_payment_pct", 0.05))
        initial_floor = float(ps_settings.get("initial_payment_floor", 3000.0))
        ceiling_threshold = float(ps_settings.get("initial_payment_ceiling_threshold", 70000.0))
        floor_above_ceiling = float(ps_settings.get("initial_payment_floor_above_ceiling", 4000.0))
        completion_pool_pct = float(ps_settings.get("completion_meeting_plus_3rd_pct", 0.35))
        weekly_count = int(ps_settings.get("weekly_payment_count", 4))

        raw_initial = round(basic_build * initial_pct, 2)
        if basic_build <= ceiling_threshold:
            initial_payment = max(raw_initial, initial_floor)
        else:
            initial_payment = max(raw_initial, floor_above_ceiling)

        completion_pool = round(basic_build * completion_pool_pct, 2)

        has_temp_kitchen = temp_kitchen_code.lower() in selected_codes
        has_glazing = any(
            "glazing" in selected_codes or "glazing" in it.get("line_code", "").lower()
            for it in items
        )

        pool_after_stages = round(basic_build - initial_payment - completion_pool, 2)

        if not has_temp_kitchen:
            pool_after_stages += temp_kitchen_cost

        weekly_count = max(weekly_count, 1)
        weekly_amount = round(pool_after_stages / weekly_count, 2)
        final_weekly_adjustment = 0.0
        if not has_temp_kitchen:
            final_weekly_adjustment += temp_kitchen_cost
        if has_glazing:
            final_weekly_adjustment += glazing_cost

        final_weekly = round(weekly_amount + final_weekly_adjustment, 2)
        regular_weekly = round(pool_after_stages - final_weekly, 2)

        payment_schedule = [
            {"stage": "Initial Payment", "amount": initial_payment, "note": ""},
            {"stage": "Com. Meeting", "amount": round(completion_pool / 2, 2), "note": ""},
            {"stage": "3rd Payment", "amount": round(completion_pool / 2, 2), "note": ""},
        ]
        for i in range(1, weekly_count + 1):
            if i == weekly_count:
                payment_schedule.append({
                    "stage": f"{i}{'st' if i == 1 else 'nd' if i == 2 else 'rd' if i == 3 else 'th'} Payment",
                    "amount": final_weekly,
                    "note": "Includes temp kitchen / glazing adjustments" if final_weekly_adjustment else "",
                })
            else:
                payment_schedule.append({
                    "stage": f"{i}{'st' if i == 1 else 'nd' if i == 2 else 'rd' if i == 3 else 'th'} Payment",
                    "amount": regular_weekly,
                    "note": "",
                })

        schedule_total = round(sum(s["amount"] for s in payment_schedule), 2)
        schedule_grand_total = round(schedule_total + (temp_kitchen_cost if has_temp_kitchen else 0.0) + (glazing_cost if has_glazing else 0.0), 2)

        deposit_pct = float(ps_settings.get("deposit_pct", 0.10))
        completion_pct = float(ps_settings.get("completion_pct", 0.10))
        deposit_amount = round(grand_total * deposit_pct, 2)
        completion_amount = round(grand_total * completion_pct, 2)
        middle_balance = round(grand_total - deposit_amount - completion_amount, 2)

        return {
            "groups": group_data,
            "subtotals": subtotals,
            "subtotal": subtotal,
            "adjustments": adjustments,
            "adjustment_total": adjustment_total,
            "grand_total": grand_total,
            "deposit_pct": deposit_pct,
            "completion_pct": completion_pct,
            "deposit_amount": deposit_amount,
            "completion_amount": completion_amount,
            "middle_balance": middle_balance,
            "line_items": items,
            "template_key": template_key,
            "payment_schedule": payment_schedule,
            "schedule_total": schedule_total,
            "schedule_grand_total": schedule_grand_total,
            "basic_build": basic_build,
            "has_temp_kitchen": has_temp_kitchen,
            "has_glazing": has_glazing,
            "temp_kitchen_cost": temp_kitchen_cost,
            "glazing_cost": glazing_cost,
        }

    finally:
        conn.close()


# ── Convenience: save calculated quote to DB ──────────────────────────

def save_calculated_quote(
    template_key: str,
    quote_id: int | None = None,
    form_data: dict[str, Any] | None = None,
    session_overrides: dict[str, Any] | None = None,
    follow_up_data: dict[str, Any] | None = None,
    client_name: str = "",
    client_address: str = "",
    notes: str = "",
) -> int:
    """
    Run calculate_quote() then persist totals + line items to the DB.
    Returns the quote_id.
    """
    result = calculate_quote(template_key, form_data, session_overrides, follow_up_data)
    conn = _get_connection()
    try:
        if quote_id:
            conn.execute(
                """
                UPDATE quotes
                SET subtotal = ?, adjustment_total = ?, grand_total = ?,
                    deposit_pct = ?, completion_pct = ?,
                    deposit_amount = ?, completion_amount = ?,
                    client_name = ?, client_address = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    result["subtotal"],
                    result["adjustment_total"],
                    result["grand_total"],
                    result["deposit_pct"],
                    result["completion_pct"],
                    result["deposit_amount"],
                    result["completion_amount"],
                    client_name,
                    client_address,
                    notes,
                    quote_id,
                ),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO quotes
                    (template_key, status, deposit_pct, completion_pct,
                     subtotal, adjustment_total, grand_total,
                     deposit_amount, completion_amount,
                     client_name, client_address, notes)
                VALUES (?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_key,
                    result["deposit_pct"],
                    result["completion_pct"],
                    result["subtotal"],
                    result["adjustment_total"],
                    result["grand_total"],
                    result["deposit_amount"],
                    result["completion_amount"],
                    client_name,
                    client_address,
                    notes,
                ),
            )
            quote_id = cur.lastrowid

        # Replace line items
        conn.execute(
            "DELETE FROM quote_line_items WHERE quote_id = ?", (quote_id,)
        )
        for item in result["line_items"]:
            conn.execute(
                """
                INSERT INTO quote_line_items
                    (quote_id, line_code, output_group, category,
                     output_title, internal_description,
                     unit_cost, units, line_total,
                     pricing_visibility, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quote_id,
                    item.get("line_code", ""),
                    item.get("output_group", "General"),
                    item.get("category", ""),
                    item.get("output_title", ""),
                    item.get("internal_description", ""),
                    item.get("unit_cost", 0),
                    item.get("units", 1),
                    item.get("line_total", 0),
                    item.get("pricing_visibility", "admin_only"),
                    item.get("sort_order", 0),
                ),
            )

        conn.commit()
        return quote_id  # type: ignore[return-value]
    finally:
        conn.close()


# ── Self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Smoke test with the live database
    import json

    # Try a known template key from page_schemas.json
    import os
    os.chdir(str(Path(__file__).parent.parent))

    # Attempt to find first available form_page
    conn2 = _get_connection()
    try:
        row = conn2.execute(
            "SELECT DISTINCT form_page FROM line_items LIMIT 1"
        ).fetchone()
        if row:
            test_key = row["form_page"]
            print(f"Testing with template_key: {test_key}")
            calc = calculate_quote(test_key)
            print(
                json.dumps(
                    {
                        k: calc[k]
                        for k in [
                            "subtotal",
                            "grand_total",
                            "subtotals",
                            "deposit_amount",
                            "completion_amount",
                            "middle_balance",
                        ]
                    },
                    indent=2,
                )
            )
            print("\nGroups:")
            for g in calc["groups"]:
                print(
                    f"  {g['name']}: {g['subtotal']} ({len(g['items'])} items)"
                )
        else:
            print("No line items found in database. Skipping smoke test.")
    finally:
        conn2.close()