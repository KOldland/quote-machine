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
import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "template_store.sqlite3"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _to_float(value: Any, default: float | None = None) -> float | None:
    """Parse a user-entered money value leniently.

    Prices are typed by hand into builder fields labelled "Price for each
    (£, one per line)", so thousands separators and stray currency symbols are
    common ("3,850", "£4,800.50"). ``float()`` rejects all of those, and the
    price paths used to swallow the resulting ValueError - which silently
    dropped the line to £0 instead of raising. Normalise first, and let the
    caller decide what an unusable value means via ``default``.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    # Keep a leading minus sign, drop currency symbols and separators.
    negative = text.startswith("-")
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    if not cleaned or cleaned == ".":
        return default
    try:
        parsed = float(cleaned)
    except ValueError:
        return default
    return -parsed if negative else parsed


def _extract_checkbox_addons(follow_up_config, follow_up_data, line_code=None):
    addon_total = 0.0
    has_addon = False
    if not follow_up_config or not isinstance(follow_up_data, dict):
        return 0.0
    try:
        fu_configs = json.loads(follow_up_config) if isinstance(follow_up_config, str) else follow_up_config
        if not isinstance(fu_configs, list):
            return 0.0
        for cfg_idx, cfg in enumerate(fu_configs):
            if not isinstance(cfg, dict):
                continue
            cfg_type = cfg.get("type", "")
            if not cfg_type.startswith("Checkbox"):
                continue
            choices = cfg.get("choices", [])
            prices = cfg.get("prices", [])
            if not isinstance(choices, list) or not isinstance(prices, list):
                continue
            field_name = 'follow_up_' + (line_code or '') + '_' + str(cfg_idx)
            checked_values = follow_up_data.get(field_name, [])
            if isinstance(checked_values, str):
                checked_values = [checked_values]
            for i, choice in enumerate(choices):
                if i < len(prices) and str(choice).strip() in [str(v).strip() for v in (checked_values or [])]:
                    price_key = field_name + '_price_' + str(i)
                    user_price = follow_up_data.get(price_key)
                    if user_price is not None and str(user_price).strip() not in ("", "0", "off", "false", "N", "No"):
                        amount = _to_float(user_price)
                        if amount is None:
                            amount = _to_float(prices[i])
                        if amount is not None:
                            addon_total += amount
                            has_addon = True
                    else:
                        amount = _to_float(prices[i])
                        if amount is not None:
                            addon_total += amount
                            has_addon = True
    except Exception:
        pass
    return addon_total if has_addon else 0.0


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
                   include_default, sort_order, form_page, quantity_source, pricing_mode,
                   addon_amount, follow_up_config, price_matrix
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
        calculator_blocks: list[dict[str, Any]] = []

        for row in rows:
            item = dict(row)
            question_id = item["id"]
            base_cost = float(item["unit_cost"] or 0)
            units = float(item["units"] or 1)
            addon_amount = float(item.get("addon_amount") or 0)

            # If quantity_source is set, use the follow-up answer as units
            qty_source = item.get("quantity_source")
            if qty_source and isinstance(follow_up_data, dict):
                fu_val = follow_up_data.get(qty_source)
                if fu_val is not None and str(fu_val).strip() not in ("", "0", "off", "false", "N", "No"):
                    try:
                        units = float(fu_val)
                    except (TypeError, ValueError):
                        pass

            # Per-selection pricing: look up option price from follow-up config
            line_total = None
            pricing_mode = item.get("pricing_mode", "per_unit")
            if pricing_mode == "per_selection" and qty_source and isinstance(follow_up_data, dict):
                selected = follow_up_data.get(qty_source, "")
                selected = str(selected or "").strip()
                option_total = 0.0
                has_price = False
                fu_config_raw = item.get("follow_up_config")
                if fu_config_raw:
                    try:
                        fu_configs = json.loads(fu_config_raw) if isinstance(fu_config_raw, str) else fu_config_raw
                        if isinstance(fu_configs, list):
                            for cfg in fu_configs:
                                if not isinstance(cfg, dict):
                                    continue
                                cfg_type = cfg.get("type", "")
                                choices = cfg.get("choices", [])
                                prices = cfg.get("prices", [])
                                if cfg_type.startswith("Dropdown") and selected:
                                    if isinstance(choices, list) and isinstance(prices, list):
                                        for i, choice in enumerate(choices):
                                            if i < len(prices) and str(choice).strip() == selected:
                                                user_price_key = qty_source + '_price'
                                                user_price = follow_up_data.get(user_price_key)
                                                if user_price is not None and str(user_price).strip() not in ("", "0", "off", "false", "N", "No"):
                                                    amount = _to_float(user_price)
                                                    if amount is None:
                                                        amount = _to_float(prices[i])
                                                    if amount is not None:
                                                        option_total += amount
                                                        has_price = True
                                                else:
                                                    amount = _to_float(prices[i])
                                                    if amount is not None:
                                                        option_total += amount
                                                        has_price = True
                                elif cfg_type.startswith("Checkbox"):
                                    if isinstance(choices, list) and isinstance(prices, list):
                                        for i, choice in enumerate(choices):
                                            if i < len(prices):
                                                field_name = qty_source
                                                checked_values = follow_up_data.get(field_name, [])
                                                if isinstance(checked_values, str):
                                                    checked_values = [checked_values]
                                                if str(choice).strip() in [str(v).strip() for v in (checked_values or [])]:
                                                    price_key = field_name + '_price_' + str(i)
                                                    user_price = follow_up_data.get(price_key)
                                                    if user_price is not None and str(user_price).strip() not in ("", "0", "off", "false", "N", "No"):
                                                        amount = _to_float(user_price)
                                                        if amount is None:
                                                            amount = _to_float(prices[i])
                                                        if amount is not None:
                                                            option_total += amount
                                                            has_price = True
                                                    else:
                                                        amount = _to_float(prices[i])
                                                        if amount is not None:
                                                            option_total += amount
                                                            has_price = True
                    except Exception:
                        pass
                if has_price:
                    line_total = option_total + addon_amount
                    units = 1

            # Per-unit-rate pricing: dropdown selects a rate per unit, quantity from follow-up, checkboxes add fixed amounts
            if pricing_mode == "per_unit_rate" and qty_source and isinstance(follow_up_data, dict):
                fu_config_raw = item.get("follow_up_config")
                rate = None
                quantity = None
                addon_total = 0.0
                has_rate = False
                has_qty = False
                rate_source_key = None
                if fu_config_raw:
                    try:
                        fu_configs = json.loads(fu_config_raw) if isinstance(fu_config_raw, str) else fu_config_raw
                        if isinstance(fu_configs, list):
                            for cfg_idx, cfg in enumerate(fu_configs):
                                if not isinstance(cfg, dict):
                                    continue
                                cfg_type = cfg.get("type", "")
                                choices = cfg.get("choices", [])
                                prices = cfg.get("prices", [])
                                if rate is None and cfg_type.startswith("Dropdown"):
                                    candidate_key = qty_source.rsplit('_', 1)[0] + '_' + str(cfg_idx)
                                    selected = follow_up_data.get(candidate_key, "")
                                    selected = str(selected or "").strip()
                                    if selected and isinstance(choices, list) and isinstance(prices, list):
                                        for i, choice in enumerate(choices):
                                            if i < len(prices) and str(choice).strip() == selected:
                                                user_price_key = candidate_key + '_price'
                                                user_price = follow_up_data.get(user_price_key)
                                                if user_price is not None and str(user_price).strip() not in ("", "0", "off", "false", "N", "No"):
                                                    amount = _to_float(user_price)
                                                    if amount is None:
                                                        amount = _to_float(prices[i])
                                                    if amount is not None:
                                                        rate = amount
                                                        has_rate = True
                                                        rate_source_key = candidate_key
                                                else:
                                                    amount = _to_float(prices[i])
                                                    if amount is not None:
                                                        rate = amount
                                                        has_rate = True
                                                        rate_source_key = candidate_key
                                elif cfg_type.startswith("Checkbox"):
                                    if isinstance(choices, list) and isinstance(prices, list):
                                        for i, choice in enumerate(choices):
                                            if i < len(prices):
                                                checked_values = follow_up_data.get(qty_source, [])
                                                if isinstance(checked_values, str):
                                                    checked_values = [checked_values]
                                                if str(choice).strip() in [str(v).strip() for v in (checked_values or [])]:
                                                    price_key = qty_source + '_price_' + str(i)
                                                    user_price = follow_up_data.get(price_key)
                                                    if user_price is not None and str(user_price).strip() not in ("", "0", "off", "false", "N", "No"):
                                                        amount = _to_float(user_price)
                                                        if amount is None:
                                                            amount = _to_float(prices[i])
                                                        if amount is not None:
                                                            addon_total += amount
                                                    else:
                                                        amount = _to_float(prices[i])
                                                        if amount is not None:
                                                            addon_total += amount
                    except Exception:
                        pass
                if not has_rate:
                    try:
                        fu_configs = json.loads(fu_config_raw) if isinstance(fu_config_raw, str) else fu_config_raw
                        if isinstance(fu_configs, list):
                            for cfg in fu_configs:
                                if isinstance(cfg, dict) and cfg.get("type", "").startswith("Dropdown"):
                                    choices = cfg.get("choices", [])
                                    prices = cfg.get("prices", [])
                                    if isinstance(choices, list) and isinstance(prices, list):
                                        for i, choice in enumerate(choices):
                                            if i < len(prices):
                                                amount = _to_float(prices[i])
                                                if amount is not None:
                                                    rate = amount
                                                    has_rate = True
                                                    break
                                if has_rate:
                                    break
                    except Exception:
                        pass
                qty_val = follow_up_data.get(qty_source)
                if qty_val is not None and str(qty_val).strip() not in ("", "0", "off", "false", "N", "No"):
                    try:
                        quantity = float(qty_val)
                        has_qty = True
                    except (TypeError, ValueError):
                        pass
                if has_rate and has_qty:
                    line_total = (rate * quantity) + addon_total + addon_amount
                    units = quantity

            # Matrix pricing: dropdown(s) select type and/or size, price looked up from price_matrix JSON
            if pricing_mode == "matrix" and isinstance(follow_up_data, dict):
                fu_config_raw = item.get("follow_up_config")
                price_matrix_raw = item.get("price_matrix")
                rate = None
                quantity = None
                if fu_config_raw and price_matrix_raw:
                    try:
                        fu_configs = json.loads(fu_config_raw) if isinstance(fu_config_raw, str) else fu_config_raw
                        price_matrix = json.loads(price_matrix_raw) if isinstance(price_matrix_raw, str) else price_matrix_raw
                        if isinstance(fu_configs, list) and isinstance(price_matrix, dict):
                            dropdown_cfgs = [cfg for cfg in fu_configs if isinstance(cfg, dict) and cfg.get("type", "").startswith("Dropdown")]
                            if len(dropdown_cfgs) == 1:
                                size_cfg = dropdown_cfgs[0]
                                size_idx = fu_configs.index(size_cfg)
                                line_code = item.get("line_code", "")
                                size_key = 'follow_up_' + (line_code or '') + '_' + str(size_idx)
                                selected_size = str(follow_up_data.get(size_key, "") or "").strip()
                                if selected_size:
                                    sizes = price_matrix.get("sizes", [])
                                    prices = price_matrix.get("prices", [])
                                    if isinstance(sizes, list) and isinstance(prices, list) and len(prices) > 0:
                                        try:
                                            size_col = sizes.index(selected_size)
                                            if size_col < len(prices[0]):
                                                rate = _to_float(prices[0][size_col])
                                        except (ValueError, TypeError, IndexError):
                                            pass
                            elif len(dropdown_cfgs) >= 2:
                                type_cfg = dropdown_cfgs[0]
                                size_cfg = dropdown_cfgs[1]
                                type_idx = fu_configs.index(type_cfg)
                                size_idx = fu_configs.index(size_cfg)
                                line_code = item.get("line_code", "")
                                type_key = 'follow_up_' + (line_code or '') + '_' + str(type_idx)
                                size_key = 'follow_up_' + (line_code or '') + '_' + str(size_idx)
                                selected_type = str(follow_up_data.get(type_key, "") or "").strip()
                                selected_size = str(follow_up_data.get(size_key, "") or "").strip()
                                if selected_type and selected_size:
                                    types = price_matrix.get("types", [])
                                    sizes = price_matrix.get("sizes", [])
                                    prices = price_matrix.get("prices", [])
                                    if isinstance(types, list) and isinstance(sizes, list) and isinstance(prices, list):
                                        try:
                                            type_row = types.index(selected_type)
                                            size_col = sizes.index(selected_size)
                                            if type_row < len(prices) and size_col < len(prices[type_row]):
                                                rate = _to_float(prices[type_row][size_col])
                                        except (ValueError, TypeError, IndexError):
                                            pass
                    except Exception:
                        pass
                if rate is not None:
                    if qty_source:
                        qty_val = follow_up_data.get(qty_source)
                        if qty_val is not None and str(qty_val).strip() not in ("", "0", "off", "false", "N", "No"):
                            try:
                                quantity = float(qty_val)
                            except (TypeError, ValueError):
                                pass
                    if quantity is not None:
                        line_total = rate * quantity
                        units = quantity
                    else:
                        line_total = rate
                        units = 1
                     # Checkbox extras still apply
                    checkbox_addons = _extract_checkbox_addons(item.get("follow_up_config"), follow_up_data, item.get("line_code"))
                    line_total = line_total + checkbox_addons + addon_amount
             # Apply user price override if present (API-driven overrides bypass allow_user_override)
            if str(question_id) in overrides:
                override_val = overrides[str(question_id)]
                user_price = _to_float(override_val)
                if user_price is not None:
                    line_total = user_price
                    item["overridden"] = True
                    item["override_source"] = "user"
                    item["unit_cost"] = user_price
                else:
                    if line_total is None:
                        line_total = base_cost * units + addon_amount
                    item["overridden"] = False
                    item["unit_cost"] = base_cost
            else:
                if line_total is None:
                    line_total = base_cost * units + addon_amount
                checkbox_addons = _extract_checkbox_addons(item.get("follow_up_config"), follow_up_data, item.get("line_code"))
                line_total = line_total + checkbox_addons
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

        # ── 3b. Apply cost group overrides from form_data ───────────────────
        cost_group_overrides = {}
        if isinstance(form_data, dict):
            for key, val in form_data.items():
                if key.endswith('_override') and val is not None:
                    # Extract the cost group name from the form_data
                    # The key is like: {page_id}_cost_group_{name}_override
                    # We map it to the output_group name stored in the cost group section
                    try:
                        override_val = float(val)
                    except (TypeError, ValueError):
                        continue
                    # Check if any group name matches this override
                    # The override value replaces the group subtotal
                    cost_group_overrides[key] = override_val

        # Apply overrides to group subtotals (match by output_group name)
        # The form stores output_group in the cost group section's meta
        # We also need to check by the override target's group name
        if cost_group_overrides:
            for gname in list(subtotals.keys()):
                # Try to find an override for this group
                for ov_key, ov_val in cost_group_overrides.items():
                    # Direct match: override key contains the group name
                    if gname.lower().replace(' ', '_') in ov_key.lower():
                        subtotals[gname] = round(ov_val, 2)
                        for gd in group_data:
                            if gd['name'] == gname:
                                gd['subtotal'] = round(ov_val, 2)

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