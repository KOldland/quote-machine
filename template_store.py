import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Iterable, Optional


LOGIC_RULE_SEEDS = [
    ("LR-VIS-CHECKBOX-TRIGGER", "show target input when trigger checkbox selected"),
    ("LR-VIS-DROPDOWN-TRIGGER", "show target block when trigger dropdown option selected"),
    ("LR-RESET-ON-DESELECT", "clear dependent values when parent trigger is removed"),
    ("LR-CALC-RATE-MULTIPLY", "subtotal equals quantity multiplied by configured rate"),
    ("LR-CALC-SUM", "page subtotal equals sum of rule outputs"),
    ("LR-VALID-PERCENT-TOTAL", "payment stage percentages must total 100"),
    ("LR-INCLUDE-PARENT-CHILD", "parent selection can propagate include flags to variants"),
    ("LR-NAV-GUARD", "validate navigation chain does not produce dead-end routes"),
]


SCENARIO_PRESETS = {
    "full_extension": [],
    "kitchen_only": [],
    "no_images_fast_quote": ["image_upload_page"],
}


def _default_db_path() -> Path:
    here = Path(__file__).resolve().parent
    override = os.getenv("QM_TEMPLATE_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return here / "template_store.sqlite3"


def _question_kind(field: Dict[str, Any]) -> str:
    field_type = str(field.get("type", "")).strip()
    if field_type:
        return field_type

    validation = str(field.get("validation", "")).strip().lower()
    if validation == "currency":
        return "currency_input"

    return "unknown"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _next_version(conn: sqlite3.Connection, template_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) AS max_version FROM form_template_versions WHERE form_template_id = ?",
        (template_id,),
    ).fetchone()
    return int(row["max_version"]) + 1 if row else 1


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS form_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tenant_id, key),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS form_template_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_template_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'page_schemas_json',
            is_published INTEGER NOT NULL DEFAULT 1,
            payload_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (form_template_id, version),
            FOREIGN KEY (form_template_id) REFERENCES form_templates(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS page_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_template_version_id INTEGER NOT NULL,
            page_key TEXT NOT NULL,
            title TEXT NOT NULL,
            previous_endpoint TEXT,
            next_endpoint TEXT,
            display_order INTEGER NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (form_template_version_id, page_key),
            FOREIGN KEY (form_template_version_id) REFERENCES form_template_versions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS question_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_template_id INTEGER NOT NULL,
            question_key TEXT NOT NULL,
            question_type TEXT NOT NULL,
            label TEXT,
            storage_key TEXT,
            display_order INTEGER NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (page_template_id, question_key),
            FOREIGN KEY (page_template_id) REFERENCES page_templates(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS logic_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS template_rule_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_template_version_id INTEGER NOT NULL,
            rule_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (form_template_version_id, rule_id),
            FOREIGN KEY (form_template_version_id) REFERENCES form_template_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (rule_id) REFERENCES logic_rules(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS option_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_template_version_id INTEGER NOT NULL,
            prefix TEXT NOT NULL,
            label TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (form_template_version_id, prefix),
            FOREIGN KEY (form_template_version_id) REFERENCES form_template_versions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS option_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            option_set_id INTEGER NOT NULL,
            line_code TEXT NOT NULL,
            label TEXT NOT NULL,
            is_included INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (option_set_id, line_code),
            FOREIGN KEY (option_set_id) REFERENCES option_sets(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS line_items (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            line_code            TEXT NOT NULL UNIQUE,
            form_page            TEXT,
            category             TEXT NOT NULL,
            internal_description TEXT,
            include_default      TEXT NOT NULL DEFAULT 'N',
            unit_cost            REAL DEFAULT 0.0,
            units                REAL DEFAULT 0.0,
            pricing_visibility   TEXT NOT NULL DEFAULT 'admin_only',
            output_title         TEXT,
            output_notes         TEXT,
            output_guidance      TEXT,
            parent_code          TEXT,
            item_role            TEXT NOT NULL DEFAULT 'standalone',
            input_type           TEXT,
            trigger_parent_code  TEXT,
            form_visible         INTEGER NOT NULL DEFAULT 1,
            sort_order           INTEGER NOT NULL DEFAULT 0,
            created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _upsert_tenant(conn: sqlite3.Connection, slug: str, name: str) -> int:
    conn.execute(
        """
        INSERT INTO tenants (slug, name) VALUES (?, ?)
        ON CONFLICT(slug) DO UPDATE SET name = excluded.name
        """,
        (slug, name),
    )
    row = conn.execute("SELECT id FROM tenants WHERE slug = ?", (slug,)).fetchone()
    return int(row["id"])


def _upsert_form_template(conn: sqlite3.Connection, tenant_id: int, key: str, name: str, description: str) -> int:
    conn.execute(
        """
        INSERT INTO form_templates (tenant_id, key, name, description)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tenant_id, key) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            updated_at = CURRENT_TIMESTAMP
        """,
        (tenant_id, key, name, description),
    )
    row = conn.execute(
        "SELECT id FROM form_templates WHERE tenant_id = ? AND key = ?",
        (tenant_id, key),
    ).fetchone()
    return int(row["id"])


def _upsert_version(conn: sqlite3.Connection, template_id: int, version: int, payload: Dict[str, Any]) -> int:
    conn.execute(
        """
        INSERT INTO form_template_versions (form_template_id, version, payload_json)
        VALUES (?, ?, ?)
        ON CONFLICT(form_template_id, version) DO UPDATE SET
            payload_json = excluded.payload_json,
            source = 'page_schemas_json'
        """,
        (template_id, version, json.dumps(payload, sort_keys=True)),
    )
    row = conn.execute(
        "SELECT id FROM form_template_versions WHERE form_template_id = ? AND version = ?",
        (template_id, version),
    ).fetchone()
    return int(row["id"])


def _replace_page_templates(conn: sqlite3.Connection, version_id: int, pages: Dict[str, Any]) -> Dict[str, int]:
    conn.execute("DELETE FROM page_templates WHERE form_template_version_id = ?", (version_id,))

    page_ids: Dict[str, int] = {}
    for idx, (page_key, page_data) in enumerate(pages.items()):
        nav = page_data.get("navigation", {}) if isinstance(page_data, dict) else {}
        conn.execute(
            """
            INSERT INTO page_templates (
                form_template_version_id, page_key, title, previous_endpoint, next_endpoint,
                display_order, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                page_key,
                str(page_data.get("title", page_key)),
                str(nav.get("previous_endpoint", "")),
                str(nav.get("next_endpoint", "")),
                idx,
                json.dumps(page_data, sort_keys=True),
            ),
        )
        row = conn.execute(
            "SELECT id FROM page_templates WHERE form_template_version_id = ? AND page_key = ?",
            (version_id, page_key),
        ).fetchone()
        page_ids[page_key] = int(row["id"])

    return page_ids


def _replace_questions(conn: sqlite3.Connection, page_ids: Dict[str, int], pages: Dict[str, Any]) -> int:
    total = 0
    for page_key, page_id in page_ids.items():
        conn.execute("DELETE FROM question_templates WHERE page_template_id = ?", (page_id,))
        page = pages.get(page_key, {}) if isinstance(pages, dict) else {}
        fields: Iterable[Dict[str, Any]] = page.get("fields", []) if isinstance(page, dict) else []
        for idx, field in enumerate(fields):
            field_id = str(field.get("id", f"field_{idx}"))
            question_type = _question_kind(field)
            storage = field.get("storage", {}) if isinstance(field.get("storage"), dict) else {}
            conn.execute(
                """
                INSERT INTO question_templates (
                    page_template_id, question_key, question_type, label,
                    storage_key, display_order, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page_id,
                    field_id,
                    question_type,
                    str(field.get("label", "")),
                    str(storage.get("key", "")),
                    idx,
                    json.dumps(field, sort_keys=True),
                ),
            )
            total += 1
    return total


def _sync_logic_rules(conn: sqlite3.Connection, version_id: int) -> int:
    for code, desc in LOGIC_RULE_SEEDS:
        conn.execute(
            """
            INSERT INTO logic_rules (code, description)
            VALUES (?, ?)
            ON CONFLICT(code) DO UPDATE SET description = excluded.description
            """,
            (code, desc),
        )

    conn.execute("DELETE FROM template_rule_bindings WHERE form_template_version_id = ?", (version_id,))

    rows = conn.execute("SELECT id FROM logic_rules ORDER BY code ASC").fetchall()
    for row in rows:
        conn.execute(
            """
            INSERT INTO template_rule_bindings (form_template_version_id, rule_id)
            VALUES (?, ?)
            ON CONFLICT(form_template_version_id, rule_id) DO NOTHING
            """,
            (version_id, int(row["id"])),
        )

    return len(rows)


def initialize_template_store(page_schemas: Dict[str, Any], *, template_key: str = "first_client_template_v1") -> Dict[str, Any]:
    """
    Bootstrap and sync Template V1 metadata into a lightweight SQLite store.

    This is Phase 1 infrastructure only and does not change runtime form rendering.
    """
    db_path = _default_db_path()

    pages = page_schemas.get("pages", {}) if isinstance(page_schemas, dict) else {}
    if not isinstance(pages, dict):
        pages = {}

    with _connect(db_path) as conn:
        _create_schema(conn)

        tenant_id = _upsert_tenant(conn, slug="default", name="Default Tenant")
        template_id = _upsert_form_template(
            conn,
            tenant_id=tenant_id,
            key=template_key,
            name="First Client Template V1",
            description="Baseline template mirrored from current first-client configuration.",
        )
        version_id = _upsert_version(conn, template_id, version=1, payload=page_schemas)

        page_ids = _replace_page_templates(conn, version_id, pages)
        question_count = _replace_questions(conn, page_ids, pages)
        logic_rule_count = _sync_logic_rules(conn, version_id)

        conn.commit()

    return {
        "db_path": str(db_path),
        "template_key": template_key,
        "version": 1,
        "pages": len(page_ids),
        "questions": question_count,
        "logic_rules": logic_rule_count,
    }


def _apply_page_flags(payload: Dict[str, Any], scenario_key: str, disabled_pages: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    result = json.loads(json.dumps(payload))
    pages = result.get("pages", {}) if isinstance(result.get("pages"), dict) else {}

    preset_disabled = set(SCENARIO_PRESETS.get(scenario_key, []))
    manual_disabled = set(disabled_pages or [])
    disabled_all = preset_disabled.union(manual_disabled)

    for page_key, page_data in pages.items():
        if not isinstance(page_data, dict):
            continue
        page_data["enabled"] = page_key not in disabled_all

    settings = result.setdefault("settings", {})
    if isinstance(settings, dict):
        settings["scenario_key"] = scenario_key
        settings["disabled_pages"] = sorted(disabled_all)

    return result


def clone_template(
    source_template_key: str,
    new_template_key: str,
    *,
    new_template_name: Optional[str] = None,
    scenario_key: str = "full_extension",
    disabled_pages: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    payload = load_template_payload(source_template_key)
    if not payload:
        raise ValueError(f"Source template '{source_template_key}' not found.")

    if scenario_key not in SCENARIO_PRESETS:
        raise ValueError(f"Unknown scenario_key '{scenario_key}'.")

    normalized_payload = _apply_page_flags(payload, scenario_key, disabled_pages)

    db_path = _default_db_path()
    with _connect(db_path) as conn:
        _create_schema(conn)

        tenant_id = _upsert_tenant(conn, slug="default", name="Default Tenant")
        template_id = _upsert_form_template(
            conn,
            tenant_id=tenant_id,
            key=new_template_key,
            name=new_template_name or new_template_key.replace("_", " ").title(),
            description=f"Cloned from {source_template_key}",
        )
        version = _next_version(conn, template_id)
        version_id = _upsert_version(conn, template_id, version=version, payload=normalized_payload)

        pages = normalized_payload.get("pages", {}) if isinstance(normalized_payload, dict) else {}
        if not isinstance(pages, dict):
            pages = {}
        page_ids = _replace_page_templates(conn, version_id, pages)
        question_count = _replace_questions(conn, page_ids, pages)
        logic_rule_count = _sync_logic_rules(conn, version_id)

        conn.commit()

    return {
        "db_path": str(db_path),
        "source_template_key": source_template_key,
        "template_key": new_template_key,
        "version": version,
        "scenario_key": scenario_key,
        "disabled_pages": sorted(set(disabled_pages or []).union(SCENARIO_PRESETS.get(scenario_key, []))),
        "pages": len(page_ids),
        "questions": question_count,
        "logic_rules": logic_rule_count,
    }


def get_latest_template_version(template_key: str = "first_client_template_v1") -> int:
    db_path = _default_db_path()
    if not db_path.exists():
        return 0

    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT MAX(ftv.version) AS latest_version
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            """,
            (template_key,),
        ).fetchone()

    if not row or row["latest_version"] is None:
        return 0
    return int(row["latest_version"])


def load_template_payload(template_key: str = "first_client_template_v1", version: Optional[int] = None) -> Optional[Dict[str, Any]]:
    db_path = _default_db_path()
    if not db_path.exists():
        return None

    with _connect(db_path) as conn:
        if version is None:
            row = conn.execute(
                """
                SELECT ftv.payload_json
                FROM form_template_versions ftv
                JOIN form_templates ft ON ft.id = ftv.form_template_id
                WHERE ft.key = ?
                ORDER BY ftv.version DESC
                LIMIT 1
                """,
                (template_key,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT ftv.payload_json
                FROM form_template_versions ftv
                JOIN form_templates ft ON ft.id = ftv.form_template_id
                WHERE ft.key = ? AND ftv.version = ?
                LIMIT 1
                """,
                (template_key, version),
            ).fetchone()

    if not row:
        return None

    try:
        payload = json.loads(row["payload_json"])
    except (TypeError, ValueError):
        return None

    return payload if isinstance(payload, dict) else None


def get_template_store_status(template_key: str = "first_client_template_v1") -> Dict[str, Any]:
    db_path = _default_db_path()
    status: Dict[str, Any] = {
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
        "template_key": template_key,
        "latest_version": 0,
        "tables": {},
    }

    if not db_path.exists():
        return status

    table_names = [
        "tenants",
        "form_templates",
        "form_template_versions",
        "page_templates",
        "question_templates",
        "logic_rules",
        "template_rule_bindings",
    ]

    with _connect(db_path) as conn:
        for table_name in table_names:
            try:
                row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
                status["tables"][table_name] = int(row["count"]) if row else 0
            except sqlite3.OperationalError:
                status["tables"][table_name] = None

    status["latest_version"] = get_latest_template_version(template_key)
    return status


def get_template_store_overview() -> Dict[str, Any]:
    db_path = _default_db_path()
    overview: Dict[str, Any] = {
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
        "templates": [],
    }
    if not db_path.exists():
        return overview

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT ft.key, ft.name, COALESCE(MAX(ftv.version), 0) AS latest_version
            FROM form_templates ft
            LEFT JOIN form_template_versions ftv ON ftv.form_template_id = ft.id
            GROUP BY ft.id, ft.key, ft.name
            ORDER BY ft.key ASC
            """
        ).fetchall()

    overview["templates"] = [
        {
            "template_key": row["key"],
            "name": row["name"],
            "latest_version": int(row["latest_version"]),
        }
        for row in rows
    ]
    return overview


# ---------------------------------------------------------------------------
# Catalog / option-set layer
# ---------------------------------------------------------------------------

import re as _re


def _extract_prefix(line_code: str) -> str:
    """Return the leading letter group of an alphanumeric line code.

    Examples: 'bw1' -> 'bw', 'sn3' -> 'sn', 'frc1' -> 'frc', 'rro1' -> 'rro'
    """
    alphanumeric = _re.sub(r"[^a-zA-Z0-9]", "", line_code).lower()
    match = _re.match(r"^([a-z]+)", alphanumeric)
    return match.group(1) if match else ""


def _get_latest_version_id(conn: sqlite3.Connection, template_key: str) -> Optional[int]:
    row = conn.execute(
        """
        SELECT ftv.id
        FROM form_template_versions ftv
        JOIN form_templates ft ON ft.id = ftv.form_template_id
        WHERE ft.key = ?
        ORDER BY ftv.version DESC
        LIMIT 1
        """,
        (template_key,),
    ).fetchone()
    return int(row["id"]) if row else None


def import_sheet_rows_to_catalog(
    sheet_rows: Iterable[Dict[str, Any]],
    template_key: str = "first_client_template_v1",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Import sheet row data into the option_sets / option_items catalog tables.

    Each row must have at minimum:
        'Line Code'           - e.g. 'bw1'
        'Internal Description'- human-readable label
        'Include'             - 'Y' or 'N'

    Rows are grouped by the leading letter group of their line code (the
    *prefix*).  Any existing option data for the target template version is
    replaced on a per-prefix basis (upsert semantics on line_code).

    Returns a summary dict with counts of sets and items written.
    """
    resolved_path = db_path or _default_db_path()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Template store DB not found at {resolved_path}")

    rows_list = list(sheet_rows)

    # Group by prefix
    prefix_groups: Dict[str, list] = {}
    for row in rows_list:
        raw_code = str(row.get("Line Code", "")).strip()
        if not raw_code:
            continue
        prefix = _extract_prefix(raw_code)
        if not prefix:
            continue
        prefix_groups.setdefault(prefix, []).append(row)

    sets_written = 0
    items_written = 0

    with _connect(resolved_path) as conn:
        version_id = _get_latest_version_id(conn, template_key)
        if version_id is None:
            raise ValueError(
                f"No template version found for key '{template_key}'. "
                "Run initialize_template_store first."
            )

        for prefix, group_rows in sorted(prefix_groups.items()):
            # Upsert option_set for this prefix
            conn.execute(
                """
                INSERT INTO option_sets (form_template_version_id, prefix, label)
                VALUES (?, ?, ?)
                ON CONFLICT(form_template_version_id, prefix) DO UPDATE SET
                    label = excluded.label
                """,
                (version_id, prefix, prefix.upper()),
            )
            set_row = conn.execute(
                "SELECT id FROM option_sets WHERE form_template_version_id = ? AND prefix = ?",
                (version_id, prefix),
            ).fetchone()
            set_id = int(set_row["id"])
            sets_written += 1

            for sort_order, row in enumerate(group_rows):
                line_code = str(row.get("Line Code", "")).strip()
                label = str(row.get("Internal Description", "")).strip()
                is_included = 1 if str(row.get("Include", "N")).strip().upper() == "Y" else 0

                conn.execute(
                    """
                    INSERT INTO option_items
                        (option_set_id, line_code, label, is_included, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(option_set_id, line_code) DO UPDATE SET
                        label = excluded.label,
                        is_included = excluded.is_included,
                        sort_order = excluded.sort_order
                    """,
                    (set_id, line_code, label, is_included, sort_order),
                )
                items_written += 1

        conn.commit()

    return {
        "template_key": template_key,
        "version_id": version_id,
        "prefixes_written": sets_written,
        "items_written": items_written,
    }


def load_option_set(
    prefix: str,
    template_key: str = "first_client_template_v1",
    db_path: Optional[Path] = None,
) -> Optional[list]:
    """Return option items for *prefix* from the catalog tables.

    Returns a list of dicts with keys ``value``, ``label``, ``is_included``,
    matching the shape produced by ``_builder_beta_checkbox_options``.

    Returns ``None`` if no catalog data exists for this prefix (so the caller
    can fall back to the sheet-data path).
    """
    resolved_path = db_path or _default_db_path()
    if not resolved_path.exists():
        return None

    with _connect(resolved_path) as conn:
        rows = conn.execute(
            """
            SELECT oi.line_code, oi.label, oi.is_included
            FROM option_items oi
            JOIN option_sets os ON os.id = oi.option_set_id
            JOIN form_template_versions ftv ON ftv.id = os.form_template_version_id
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ? AND os.prefix = ?
            ORDER BY oi.sort_order ASC, oi.line_code ASC
            """,
            (template_key, prefix),
        ).fetchall()

    if not rows:
        return None

    return [
        {
            "value": row["line_code"],
            "label": row["label"],
            "is_included": bool(row["is_included"]),
        }
        for row in rows
    ]


def get_line_items_by_category(category: str, db_path: Optional[Path] = None) -> list:
    """Return all line_items for a given category."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    rows = conn.execute(
        "SELECT * FROM line_items WHERE category = ? ORDER BY sort_order ASC, line_code ASC",
        (category,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_structured_line_items_for_page(form_page: str, db_path: Optional[Path] = None) -> Dict[str, list]:
    """
    Return form-visible line_items for a page, structured into parent/child
    relationships and grouped by category.
    """
    path = db_path or _default_db_path()
    conn = _connect(path)
    # Fetch ALL items for the page, including children that might be hidden at the top level
    rows = conn.execute(
        "SELECT * FROM line_items WHERE form_page=? ORDER BY category ASC, sort_order ASC, line_code ASC",
        (form_page,),
    ).fetchall()
    conn.close()

    if not rows:
        return {}

    # First pass: create a lookup map for all items
    items_by_code = {dict(row)['line_code']: dict(row) for row in rows}
    for item in items_by_code.values():
        item['children'] = []

    # Second pass: build the hierarchy
    top_level_items = []
    for item in items_by_code.values():
        parent_code = item.get('parent_code')
        if parent_code and parent_code in items_by_code:
            # This is a child, add it to its parent's list
            items_by_code[parent_code]['children'].append(item)
        else:
            # This is a top-level item
            top_level_items.append(item)

    # Third pass: group the top-level items by category
    result: Dict[str, list] = {}
    for item in top_level_items:
        # Only include items that are supposed to be visible on the form
        if item.get('form_visible'):
            cat = item["category"]
            if cat not in result:
                result[cat] = []
            result[cat].append(item)

    return result


def get_line_items_for_page(form_page: str, db_path: Optional[Path] = None) -> Dict[str, list]:
    """Return form-visible line_items for a given form_page, grouped by category.

    Returns an ordered dict: {category_name: [row_dict, ...]} sorted by
    category ASC, sort_order ASC, line_code ASC.
    Only rows with form_visible=1 are included.
    """
    path = db_path or _default_db_path()
    conn = _connect(path)
    rows = conn.execute(
        "SELECT id, line_code, form_page, category, internal_description, include_default, "
        "unit_cost, units, pricing_visibility, output_title, output_notes, output_guidance, "
        "parent_code, item_role, input_type, trigger_parent_code, form_visible, sort_order "
        "FROM line_items WHERE form_page=? AND form_visible=1 AND item_role != 'auto_child' "
        "ORDER BY category ASC, sort_order ASC, line_code ASC",
        (form_page,),
    ).fetchall()
    conn.close()
    result: Dict[str, list] = {}
    for row in rows:
        cat = row["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(dict(row))
    return result


def get_line_items_by_codes(codes: list, db_path=None) -> list:
    """Return full line_item rows for a list of line_codes, ordered by category + sort_order."""
    if not codes:
        return []
    path = db_path or _default_db_path()
    conn = _connect(path)
    placeholders = ','.join('?' * len(codes))
    rows = conn.execute(
        f"SELECT * FROM line_items WHERE line_code IN ({placeholders}) "
        "ORDER BY category ASC, sort_order ASC, line_code ASC",
        codes
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
