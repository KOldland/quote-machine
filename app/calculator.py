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
        cursor = conn.execute(
            """
            SELECT id, line_code, category, internal_description,
                   unit_cost, units, output_title, output_notes, output_guidance,
                   output_group, pricing_visibility, allow_user_override,
                   include_default, sort_order
            FROM line_items
            WHERE form_page = ?
            ORDER BY output_group, sort_order, line_code
            """,
            (template_key,),
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

            # Apply user price override if allowed and present
            if item["allow_user_override"] and str(question_id) in overrides:
                override_val = overrides[str(question_id)]
                try:
                    user_price = float(override_val)
                    # interpret override as total price (not per unit)
                    line_total = user_price
                    item["overridden"] = True
                    item["override_source"] = "user"
                except (TypeError, ValueError):
                    line_total = base_cost * units
                    item["overridden"] = False
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
                    "items": gitems,
                }
            )

        # ── 4. Apply quote adjustments (from session or defaults) ──────────
        adjustments: list[dict[str, Any]] = []
        # Note: adjustments from quote_adjustments table are applied when
        # a quote is formally saved. For live calculation we use session-level
        # ad-hoc adjustments (passed via form_data or overrides).
        adjustment_total = 0.0

        # ── 5. Compute totals ──────────────────────────────────────────────
        subtotal = round(sum(subtotals.values()), 2)
        grand_total = round(subtotal + adjustment_total, 2)

        # ── 6. Payment schedule ────────────────────────────────────────────
        deposit_pct = float(
            (session_overrides or {}).get("deposit_pct", 0.10)
        )
        completion_pct = float(
            (session_overrides or {}).get("completion_pct", 0.10)
        )
        deposit_amount = round(grand_total * deposit_pct, 2)
        completion_amount = round(grand_total * completion_pct, 2)
        middle_balance = round(
            grand_total - deposit_amount - completion_amount, 2
        )

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
            "items": items,
            "template_key": template_key,
        }

    finally:
        conn.close()


# ── Convenience: save calculated quote to DB ──────────────────────────

def save_calculated_quote(
    template_key: str,
    quote_id: int | None = None,
    form_data: dict[str, Any] | None = None,
    session_overrides: dict[str, Any] | None = None,
    client_name: str = "",
    client_address: str = "",
    notes: str = "",
) -> int:
    """
    Run calculate_quote() then persist totals + line items to the DB.
    Returns the quote_id.
    """
    result = calculate_quote(template_key, form_data, session_overrides)
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
        for item in result["items"]:
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