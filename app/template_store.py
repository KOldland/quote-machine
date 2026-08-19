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
    """Return the internal “question kind” for a field."""
    field_type = str(field.get("type", "")).strip()
    if field_type:
        return field_type

    validation = str(field.get("validation", "")).strip().lower()
    if validation == "currency":
        return "currency_input"

    return "unknown"


from typing import Union
def _connect(db_path: Union[Path, str]) -> sqlite3.Connection:
    """Open a SQLite connection, ensuring the directory exists.

    ``db_path`` may be a pathlib.Path instance or a plain string.
    sqlite3.connect requires a string path, so we normalise the value to a
    Path first (so we can safely use ``parent`` for directory creation) and
    then convert back to ``str`` for the actual connection call.
    """
    # Normalise to ``Path`` so we can safely call ``parent``.
    db_path_obj = Path(db_path) if not isinstance(db_path, Path) else db_path
    db_path_obj.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path_obj))
    conn.row_factory = sqlite3.Row
    return conn


def _next_version(conn: sqlite3.Connection, template_id: int) -> int:
    """Return the next version number for a given template."""
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) AS max_version "
        "FROM form_template_versions WHERE form_template_id = ?",
        (template_id,),
    ).fetchone()
    return int(row["max_version"]) + 1 if row else 1


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS output_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_template_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            sections_json TEXT NOT NULL DEFAULT '{}',
            css_json TEXT NOT NULL DEFAULT '{}',
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (form_template_id) REFERENCES form_templates(id) ON DELETE CASCADE
        );

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

        CREATE TABLE IF NOT EXISTS saved_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
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
            settings_json TEXT NOT NULL DEFAULT '{}',
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

        CREATE TABLE IF NOT EXISTS category_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_template_version_id INTEGER NOT NULL,
            page_template_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            output_group TEXT DEFAULT 'General',
            image_url TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (page_template_id, name),
            FOREIGN KEY (form_template_version_id) REFERENCES form_template_versions(id) ON DELETE CASCADE,
            FOREIGN KEY (page_template_id) REFERENCES page_templates(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS question_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_template_id INTEGER NOT NULL,
            question_key TEXT NOT NULL,
            question_type TEXT NOT NULL,
            label TEXT,
            storage_key TEXT,
            display_order INTEGER NOT NULL,
            allow_user_override INTEGER NOT NULL DEFAULT 0,
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
            is_follow_up         INTEGER NOT NULL DEFAULT 0,
            follow_up_type       TEXT,
            follow_up_config     TEXT,
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
    # SAFE: use INSERT OR IGNORE so existing UI-created pages are never deleted.
    # The old DELETE+INSERT pattern was wiping pages on every restart.

    page_ids: Dict[str, int] = {}
    for idx, (page_key, page_data) in enumerate(pages.items()):
        nav = page_data.get("navigation", {}) if isinstance(page_data, dict) else {}
        conn.execute(
            """
            INSERT OR IGNORE INTO page_templates (
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
        page_id = int(row["id"])
        page_ids[page_key] = page_id

        categories = page_data.get("categories", [])
        if isinstance(categories, list):
            for cat in categories:
                if isinstance(cat, dict):
                    cat_name = str(cat.get("name", ""))
                    sort_order = int(cat.get("sort_order", 0))
                    if cat_name:
                        output_group = str(cat.get("output_group", "General"))
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO category_templates (
                                form_template_version_id, page_template_id, name, display_order, output_group
                            ) VALUES (?, ?, ?, ?, ?)
                            """,
                            (version_id, page_id, cat_name, sort_order, output_group)
                        )

    return page_ids


def _replace_questions(conn: sqlite3.Connection, page_ids: Dict[str, int], pages: Dict[str, Any]) -> int:
    total = 0
    for page_key, page_id in page_ids.items():
        conn.execute("DELETE FROM question_templates WHERE page_template_id = ?", (page_id,))
        page = pages.get(page_key, {}) if isinstance(pages, dict) else {}
        # SaaS: Read "blocks" (builder_beta format), fall back to "fields" (legacy)
        fields: Iterable[Dict[str, Any]] = (
            page.get("blocks", []) or page.get("fields", [])
        ) if isinstance(page, dict) else []
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

    # -----------------------------------------------------------------
    # Open (or create) the SQLite file and make sure the schema exists.
    # -----------------------------------------------------------------
    with _connect(db_path) as conn:
        _create_schema(conn)

        # -----------------------------------------------------------------
        # Create the default tenant and the top‑level form_template row.
        # -----------------------------------------------------------------
        tenant_id = _upsert_tenant(conn, slug="default", name="Default Tenant")
        template_id = _upsert_form_template(
            conn,
            tenant_id=tenant_id,
            key=template_key,
            name="First Client Template V1",
            description="Baseline template mirrored from current first-client configuration.",
        )

        # -----------------------------------------------------------------
        # IDEMPOTENT GUARD:
        # If ANY version already exists for this template we treat the
        # database as the source of truth and skip seeding.  This prevents
        # server restarts from creating duplicate versions and wiping UI‑created pages.
        # -----------------------------------------------------------------
        existing_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM form_template_versions WHERE form_template_id = ?",
            (template_id,),
        ).fetchone()["cnt"]

        if existing_count > 0:
            create_default_output_template(template_key, db_path=db_path)
            latest = conn.execute(
                "SELECT id, version FROM form_template_versions "
                "WHERE form_template_id = ? ORDER BY version DESC LIMIT 1",
                (template_id,),
            ).fetchone()
            return {
                "db_path": str(db_path),
                "template_key": template_key,
                "version": int(latest["version"]),
                "pages": "skipped (already seeded — database is source of truth)",
                "questions": 0,
                "logic_rules": 0,
            }

        # -----------------------------------------------------------------
        # Fresh DB – create the first version and populate pages, questions
        # and logic‑rule bindings.
        # -----------------------------------------------------------------
        version = 1
        version_id = _upsert_version(conn, template_id, version=version, payload=page_schemas)

        page_ids = _replace_page_templates(conn, version_id, pages)
        question_count = _replace_questions(conn, page_ids, pages)
        logic_rule_count = _sync_logic_rules(conn, version_id)

        # Seed a default output template for this form
        create_default_output_template(template_key, db_path=db_path)
        
        conn.commit()

    return {
        "db_path": str(db_path),
        "template_key": template_key,
        "version": version,
        "pages": len(page_ids),
        "questions": question_count,
        "logic_rules": logic_rule_count,
    }

def initialize_template_store(
    page_schemas: Dict[str, Any],
    *,
    template_key: str = "kitchen_only_template_test",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Bootstrap and sync Template V1 metadata into a lightweight SQLite store.

    This is Phase 1 infrastructure only and does not change runtime form rendering.
    """
    # Use the supplied path (e.g. a temporary test DB) or fall back to the default.
    db_path = db_path or _default_db_path()

    # -----------------------------------------------------------------
    # Normalise the incoming page schema – we only care about the
    # ``pages`` dict, everything else is ignored for the initial seed.
    # -----------------------------------------------------------------
    # For SaaS: Read from builder_beta.pages (canonical), fall back to pages (legacy)
    if isinstance(page_schemas, dict):
        # Try builder_beta.pages first (SaaS structure with blocks)
        pages = page_schemas.get("builder_beta", {}).get("pages", {})
        # Fall back to legacy pages key if builder_beta not found
        if not pages:
            pages = page_schemas.get("pages", {})
    else:
        pages = {}

    # -----------------------------------------------------------------
    # Open (or create) the SQLite file and make sure the schema exists.
    # -----------------------------------------------------------------
    with _connect(db_path) as conn:
        _create_schema(conn)

        # -----------------------------------------------------------------
        # Create the default tenant and the top‑level form_template row.
        # -----------------------------------------------------------------
        tenant_id = _upsert_tenant(conn, slug="default", name="Default Tenant")
        template_id = _upsert_form_template(
            conn,
            tenant_id=tenant_id,
            key=template_key,
            name="First Client Template V1",
            description="Baseline template mirrored from current first-client configuration.",
        )

        # -----------------------------------------------------------------
        # IDEMPOTENT GUARD:
        # If ANY version already exists for this template we treat the
        # database as the source of truth and skip seeding.  This prevents
        # server restarts from creating duplicate versions and wiping UI‑created pages.
        # -----------------------------------------------------------------
        existing_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM form_template_versions WHERE form_template_id = ?",
            (template_id,),
        ).fetchone()["cnt"]

        if existing_count > 0:
            create_default_output_template(template_key, db_path=db_path)
            latest = conn.execute(
                "SELECT id, version FROM form_template_versions "
                "WHERE form_template_id = ? ORDER BY version DESC LIMIT 1",
                (template_id,),
            ).fetchone()
            return {
                "db_path": str(db_path),
                "template_key": template_key,
                "version": int(latest["version"]),
                "pages": "skipped (already seeded — database is source of truth)",
                "questions": 0,
                "logic_rules": 0,
            }

        # -----------------------------------------------------------------
        # Fresh DB – create the first version and populate pages, questions
        # and logic‑rule bindings.
        # -----------------------------------------------------------------
        version = 1
        version_id = _upsert_version(conn, template_id, version=version, payload=page_schemas)

        page_ids = _replace_page_templates(conn, version_id, pages)
        question_count = _replace_questions(conn, page_ids, pages)
        logic_rule_count = _sync_logic_rules(conn, version_id)

        # Seed a default output template for this form
        create_default_output_template(template_key, db_path=db_path)
        
        conn.commit()

    return {
        "db_path": str(db_path),
        "template_key": template_key,
        "version": version,
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
            '''
            SELECT ft.key, ft.name, COALESCE(MAX(ftv.version), 0) AS latest_version
            FROM form_templates ft
            LEFT JOIN form_template_versions ftv ON ftv.form_template_id = ft.id
            GROUP BY ft.id, ft.key, ft.name
            ORDER BY ft.key ASC
            '''
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


def get_form_template(template_key: str, db_path: Optional[Path] = None) -> Optional[dict]:
    '''Return the form_template row for a given template_key.'''
    path = db_path or _default_db_path()
    conn = _connect(path)
    row = conn.execute(
        "SELECT * FROM form_templates WHERE key = ?",
        (template_key,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_form_template(template_key: str, name: str, description: str, db_path: Optional[Path] = None):
    '''Update the name and description for a given template_key.'''
    path = db_path or _default_db_path()
    conn = _connect(path)
    conn.execute(
        "UPDATE form_templates SET name = ?, description = ? WHERE key = ?",
        (name, description, template_key),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
def duplicate_form(old_key: str, new_title: str, new_description: str, db_path: Optional[Path] = None) -> str:
    '''Duplicates a form, its pages, categories, and questions.'''
    import json
    import uuid
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    new_key = f"form_{uuid.uuid4().hex[:8]}"
    
    # 1. Create new form entry (tenant_id uses default 1 for now)
    conn.execute(
        "INSERT INTO form_templates (tenant_id, key, name, description) VALUES (?, ?, ?, ?)",
        (1, new_key, new_title, new_description)
    )
    
    # 2. Duplicate pages via page_schemas.json handling
    schemas_path = path.parent / 'page_schemas.json'
    if schemas_path.exists():
        with open(schemas_path, 'r') as f:
            schemas = json.load(f)
            
        if old_key in schemas:
            schemas[new_key] = json.loads(json.dumps(schemas[old_key])) # Deep copy
            # Update form_key references if needed inside pages? Usually pages belong to the key top-level
            with open(schemas_path, 'w') as f:
                json.dump(schemas, f, indent=2)
                
    # 3. Duplicate pages in DB
    # Fetch old version ID
    old_version_row = conn.execute(
        "SELECT ftv.id FROM form_template_versions ftv JOIN form_templates ft ON ft.id = ftv.form_template_id WHERE ft.key = ? ORDER BY ftv.version DESC LIMIT 1",
        (old_key,)
    ).fetchone()
    old_version_id = old_version_row["id"] if old_version_row else None

    # Get new form_template_id
    new_template_id = conn.execute("SELECT id FROM form_templates WHERE key = ?", (new_key,)).fetchone()["id"]
    
    # Create an initial version for the new form
    conn.execute("INSERT INTO form_template_versions (form_template_id, version, payload_json) VALUES (?, ?, ?)", (new_template_id, 1, "{}"))
    new_version_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    if old_version_id:
        pages = conn.execute("SELECT id, page_key, title, display_order, description, metadata_json FROM page_templates WHERE form_template_version_id = ?", (old_version_id,)).fetchall()
        
        for p in pages:
            conn.execute(
                "INSERT INTO page_templates (form_template_version_id, page_key, title, display_order, description, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
                (new_version_id, p['page_key'], p['title'], p['display_order'], p.get('description', ''), p.get('metadata_json', '{}'))
            )
            
            new_page_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            
            # 4. Duplicate categories
            categories = conn.execute("SELECT id, name, display_order, description FROM category_templates WHERE page_template_id = ?", (p['id'],)).fetchall()
            
            for c in categories:
                conn.execute(
                    "INSERT INTO category_templates (form_template_version_id, page_template_id, name, display_order, description) VALUES (?, ?, ?, ?, ?)",
                    (new_version_id, new_page_id, c['name'], c['display_order'], c.get('description', ''))
                )
            
            # 5. Duplicate line items (questions)
            # Find old line items by checking their page_key and category
            # line_items table currently links via form_page (string)
            items = conn.execute("SELECT * FROM line_items WHERE form_page = ?", (p['page_key'],)).fetchall()
            for item in items:
                # To prevent unique line_code conflicts on duplicate, we'll generate new line_codes for duplicate items
                import string
                import random
                def get_rand():
                    return "Q_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                
                new_code = get_rand()
                cols = [k for k in item.keys() if k not in ["id", "line_code", "created_at", "updated_at"]]
                placeholders = ', '.join(['?'] * len(cols))
                vals = [item[k] for k in cols]
                
                # Insert with new code
                q = f"INSERT INTO line_items (line_code, {', '.join(cols)}) VALUES (?, {placeholders})"
                conn.execute(q, [new_code] + vals)
                
    conn.commit()
    conn.close()
    return new_key

def delete_form(form_key: str, db_path: Optional[Path] = None):
    '''Deletes a form and all associated data.'''
    import json
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    # 1. Get all pages
    pages = conn.execute("SELECT id, page_key FROM page_templates WHERE form_key = ?", (form_key,)).fetchall()
    
    for p in pages:
        # Get categories
        categories = conn.execute("SELECT name FROM category_templates WHERE page_id = ?", (p['id'],)).fetchall()
        for c in categories:
            # Delete line items
            conn.execute("DELETE FROM line_items WHERE page_key = ? AND category = ?", (p['page_key'], c['name']))
            
        # Delete categories
        conn.execute("DELETE FROM category_templates WHERE page_id = ?", (p['id'],))
        
    # Delete pages
    conn.execute("DELETE FROM page_templates WHERE form_key = ?", (form_key,))
    
    # Delete form template
    conn.execute("DELETE FROM form_templates WHERE key = ?", (form_key,))
    
    conn.commit()
    conn.close()
    
    # Remove from JSON
    schemas_path = path.parent / 'page_schemas.json'
    if schemas_path.exists():
        with open(schemas_path, 'r') as f:
            schemas = json.load(f)
        if form_key in schemas:
            del schemas[form_key]
            with open(schemas_path, 'w') as f:
                json.dump(schemas, f, indent=2)

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
    category_templates.display_order ASC, then sort_order ASC, line_code ASC.
    Only rows with form_visible=1 are included.
    """
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    # Get ordered categories
    cat_query = """
        SELECT c.name
        FROM category_templates c
        JOIN page_templates p ON c.page_template_id = p.id
        WHERE p.page_key = ?
        ORDER BY c.display_order ASC
    """
    cat_rows = conn.execute(cat_query, (form_page,)).fetchall()
    result: Dict[str, list] = {}
    for r in cat_rows:
        result[r['name']] = []
        
    cat_fallback = len(result) == 0

    rows = conn.execute(
        "SELECT id, line_code, form_page, category, internal_description, include_default, "
        "unit_cost, units, pricing_visibility, output_title, output_notes, output_guidance, "
        "parent_code, item_role, input_type, trigger_parent_code, form_visible, sort_order, "
        "is_follow_up, follow_up_type, follow_up_config, allow_user_override, output_group "
        "FROM line_items WHERE form_page=? AND form_visible=1 AND item_role != 'auto_child' "
        "ORDER BY sort_order ASC, line_code ASC",
        (form_page,),
    ).fetchall()
    conn.close()
    
    for row in rows:
        cat = row["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(dict(row))
        
    if cat_fallback:
        result = dict(sorted(result.items()))
        
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

def get_all_pages(template_key: str = "first_client_template_v1", db_path: Optional[Path] = None) -> list:
    """Return all page_templates for the latest version of a template, ordered by display_order."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    version_id = _get_latest_version_id(conn, template_key)
    if version_id is None:
        conn.close()
        return []
        
    rows = conn.execute(
        "SELECT id, page_key, title, display_order FROM page_templates WHERE form_template_version_id = ? ORDER BY display_order ASC",
        (version_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_page(page_key: str, title: str, template_key: str = "first_client_template_v1", db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Create a new page_template."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    version_id = _get_latest_version_id(conn, template_key)
    if version_id is None:
        conn.close()
        return {"success": False, "error": "Template version not found"}
        
    try:
        max_order_row = conn.execute(
            "SELECT MAX(display_order) as max_order FROM page_templates WHERE form_template_version_id = ?",
            (version_id,)
        ).fetchone()
        
        next_order = 0
        if max_order_row and max_order_row["max_order"] is not None:
            next_order = int(max_order_row["max_order"]) + 1
            
        conn.execute(
            """
            INSERT INTO page_templates (
                form_template_version_id, page_key, title, display_order, metadata_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (version_id, page_key, title, next_order, "{}")
        )
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def duplicate_page(source_page_key: str, new_page_key: str, new_title: str, template_key: str = "first_client_template_v1", db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Duplicate an existing page, its categories, and line items."""
    import uuid
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        # Get source page (using max version id available for that page)
        source_page = conn.execute(
            "SELECT * FROM page_templates WHERE page_key = ? ORDER BY form_template_version_id DESC LIMIT 1",
            (source_page_key,)
        ).fetchone()
        
        if not source_page:
            conn.rollback()
            return {"success": False, "error": f"Source page '{source_page_key}' not found"}
            
        version_id = source_page["form_template_version_id"]
        
        if not source_page:
            conn.rollback()
            return {"success": False, "error": f"Source page '{source_page_key}' not found"}
            
        # Determine next display order
        max_order_row = conn.execute(
            "SELECT MAX(display_order) as max_order FROM page_templates WHERE form_template_version_id = ?",
            (version_id,)
        ).fetchone()
        
        next_order = 0
        if max_order_row and max_order_row["max_order"] is not None:
            next_order = int(max_order_row["max_order"]) + 1
            
        # 1. Insert new page
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO page_templates 
               (form_template_version_id, page_key, title, metadata_json, display_order)
               VALUES (?, ?, ?, ?, ?)
            """,
            (version_id, new_page_key, new_title, source_page["metadata_json"], next_order)
        )
        new_page_id = cur.lastrowid
        
        # 2. Copy Categories
        source_cats = conn.execute(
            "SELECT * FROM category_templates WHERE form_template_version_id = ? AND page_template_id = ?",
            (version_id, source_page["id"])
        ).fetchall()
        
        for cat in source_cats:
            conn.execute(
                """INSERT INTO category_templates 
                   (form_template_version_id, page_template_id, name, display_order)
                   VALUES (?, ?, ?, ?)
                """,
                (version_id, new_page_id, cat["name"], cat["display_order"])
            )
            
        # 3. Copy Line Items
        source_items = conn.execute(
            "SELECT * FROM line_items WHERE form_page = ?",
            (source_page_key,)
        ).fetchall()
        
        for item in source_items:
            import string
            import random
            def get_rand():
                return "Q_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            new_code = get_rand()
            
            # Reconstruct columns
            columns = [key for key in item.keys() if key not in ["id", "line_code", "form_page", "created_at", "updated_at"]]
            placeholders = ", ".join(["?"] * len(columns))
            cols_str = ", ".join(columns)
            
            vals = [item[c] for c in columns]
            
            # Execute insert
            q = f"INSERT INTO line_items (line_code, form_page, {cols_str}) VALUES (?, ?, {placeholders})"
            conn.execute(q, [new_code, new_page_key] + vals)
            
        conn.commit()
        return {"success": True, "page_key": new_page_key}
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return {"success": False, "error": f"Integrity error: {str(e)}"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
    finally:
        conn.close()

def add_category(page_key: str, category_name: str, template_key: str = "first_client_template_v1", db_path: Optional[Path] = None, output_group: str = "General") -> Dict[str, Any]:
    """Create a new category_template for a page."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    version_id = _get_latest_version_id(conn, template_key)
    if version_id is None:
        conn.close()
        return {"success": False, "error": "Template version not found"}
        
    try:
        page_row = conn.execute(
            "SELECT id FROM page_templates WHERE form_template_version_id = ? AND page_key = ?",
            (version_id, page_key)
        ).fetchone()
        
        if not page_row:
            return {"success": False, "error": "Page not found"}
            
        page_id = page_row["id"]
        
        # Check for duplicate category name on this page
        existing = conn.execute(
            "SELECT id FROM category_templates WHERE page_template_id = ? AND name = ?",
            (page_id, category_name)
        ).fetchone()
        if existing:
            conn.close()
            return {
                "success": False,
                "error": f"Category '{category_name}' already exists on this page.",
                "duplicate": True,
            }
        
        max_order_row = conn.execute(
            "SELECT MAX(display_order) as max_order FROM category_templates WHERE page_template_id = ?",
            (page_id,)
        ).fetchone()
        
        next_order = 0
        if max_order_row and max_order_row["max_order"] is not None:
            next_order = int(max_order_row["max_order"]) + 1
            
        conn.execute(
            """
            INSERT INTO category_templates (
                form_template_version_id, page_template_id, name, display_order, output_group
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (version_id, page_id, category_name, next_order, output_group)
        )
        conn.commit()
        
        # Also persist into the JSON schema so BUILD MODE sees the new category.
        try:
            import json as _json
            from pathlib import Path as _Path
            _schema_path = _Path(__file__).parent / 'page_schemas.json'
            if _schema_path.exists():
                with _schema_path.open('r') as _f:
                    _schemas = _json.load(_f)
                _bb = _schemas.get('builder_beta', _schemas)
                _pages = _bb.get('pages', {})
                _page = _pages.get(page_key, {})
                _cats = _page.get('categories', [])
                if not any(c.get('name') == category_name for c in _cats):
                    _cats.append({
                        'name': category_name,
                        'sort_order': next_order,
                        'description': '',
                    })
                    _page['categories'] = _cats
                    _pages[page_key] = _page
                    _bb['pages'] = _pages
                    _schemas['builder_beta'] = _bb
                    with _schema_path.open('w') as _f:
                        _json.dump(_schemas, _f, indent=2)
        except Exception:
            pass
        
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ── Quote Calculator ─────────────────────────────────────────────────────
def upsert_payment_schedule_block(
    template_key: str,
    deposit_pct: float = 0.10,
    completion_pct: float = 0.10,
    allow_user_override: bool = False,
    initial_payment_pct: float = 0.05,
    initial_payment_floor: float = 3000.0,
    initial_payment_ceiling_threshold: float = 70000.0,
    initial_payment_floor_above_ceiling: float = 4000.0,
    completion_meeting_plus_3rd_pct: float = 0.35,
    weekly_payment_count: int = 4,
    optional_line_codes: Optional[list[str]] = None,
    temp_kitchen_line_code: str = "pl6",
    temp_kitchen_cost: float = 250.0,
    glazing_cost: float = 500.0,
    db_path: Optional[Path] = None,
) -> None:
    """Persist payment-schedule defaults into form_templates.settings_json."""
    import json
    path = db_path or _default_db_path()
    conn = _connect(path)

    row = conn.execute(
        "SELECT id, settings_json FROM form_templates WHERE key = ?",
        (template_key,),
    ).fetchone()

    if not row:
        conn.close()
        return

    settings = json.loads(row["settings_json"] or "{}")
    settings["payment_schedule"] = {
        "deposit_pct": deposit_pct,
        "completion_pct": completion_pct,
        "allow_user_override": allow_user_override,
        "initial_payment_pct": initial_payment_pct,
        "initial_payment_floor": initial_payment_floor,
        "initial_payment_ceiling_threshold": initial_payment_ceiling_threshold,
        "initial_payment_floor_above_ceiling": initial_payment_floor_above_ceiling,
        "completion_meeting_plus_3rd_pct": completion_meeting_plus_3rd_pct,
        "weekly_payment_count": weekly_payment_count,
        "optional_line_codes": optional_line_codes or ["pl6", "glazing"],
        "temp_kitchen_line_code": temp_kitchen_line_code,
        "temp_kitchen_cost": temp_kitchen_cost,
        "glazing_cost": glazing_cost,
    }

    conn.execute(
        "UPDATE form_templates SET settings_json = ? WHERE key = ?",
        (json.dumps(settings), template_key),
    )
    conn.commit()
    conn.close()


def get_payment_schedule_block(
    template_key: str,
    db_path: Optional[Path] = None,
) -> dict:
    """Return payment-schedule settings dict with defaults if not set."""
    import json
    path = db_path or _default_db_path()
    conn = _connect(path)

    row = conn.execute(
        "SELECT settings_json FROM form_templates WHERE key = ?",
        (template_key,),
    ).fetchone()
    conn.close()

    if row:
        settings = json.loads(row["settings_json"] or "{}")
        return settings.get("payment_schedule", {
            "deposit_pct": 0.10,
            "completion_pct": 0.10,
            "allow_user_override": False,
            "initial_payment_pct": 0.05,
            "initial_payment_floor": 3000.0,
            "initial_payment_ceiling_threshold": 70000.0,
            "initial_payment_floor_above_ceiling": 4000.0,
            "completion_meeting_plus_3rd_pct": 0.35,
            "weekly_payment_count": 4,
            "optional_line_codes": ["pl6", "glazing"],
            "temp_kitchen_line_code": "pl6",
            "temp_kitchen_cost": 250.0,
            "glazing_cost": 500.0,
        })

    return {
        "deposit_pct": 0.10,
        "completion_pct": 0.10,
        "allow_user_override": False,
        "initial_payment_pct": 0.05,
        "initial_payment_floor": 3000.0,
        "initial_payment_ceiling_threshold": 70000.0,
        "initial_payment_floor_above_ceiling": 4000.0,
        "completion_meeting_plus_3rd_pct": 0.35,
        "weekly_payment_count": 4,
        "optional_line_codes": ["pl6", "glazing"],
        "temp_kitchen_line_code": "pl6",
        "temp_kitchen_cost": 250.0,
        "glazing_cost": 500.0,
    }

# ── Output Template CRUD ──────────────────────────────────────────────

DEFAULT_OUTPUT_SECTIONS = {
    "header": {
        "enabled": True,
        "show_logo": True,
        "logo_url": "/static/images/logo.png",
        "show_quote_number": True,
        "show_date": True,
        "company_name": "Quote Machine",
        "tagline": ""
    },
    "body": {
        "show_client_info": True,
        "show_line_items_table": True,
        "show_subtotals": True,
        "show_payment_schedule": True,
        "group_by_category": True
    },
    "footer": {
        "enabled": True,
        "show_page_numbers": True,
        "terms_text": "Terms and conditions apply...",
        "contact_info": ""
    }
}


def create_default_output_template(form_key: str, db_path: Optional[Path] = None) -> dict:
    """Create a default output template for the given form template key.

    If one already exists with is_default=1, returns that one instead.
    """
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_row = conn.execute(
            "SELECT id FROM form_templates WHERE key = ?", (form_key,)
        ).fetchone()
        if not ft_row:
            return {"error": f"Form template '{form_key}' not found"}
        ft_id = int(ft_row["id"])

        existing = conn.execute(
            "SELECT id FROM output_templates WHERE form_template_id = ? AND is_default = 1",
            (ft_id,)
        ).fetchone()
        if existing:
            return {"template_id": int(existing["id"]), "action": "already_exists"}

        cur = conn.execute(
            """
            INSERT INTO output_templates
                (form_template_id, name, sections_json, is_default)
            VALUES (?, ?, ?, 1)
            """,
            (ft_id, "Default", json.dumps(DEFAULT_OUTPUT_SECTIONS))
        )
        conn.commit()
        return {"template_id": cur.lastrowid, "action": "created"}
    finally:
        conn.close()


def update_saved_quote(quote_id: int, form_key: str, name: str, blocks_json: list, settings: dict, client_name: str = '', notes: str = '', user_id: Optional[int] = None, db_path: Optional[Path] = None, form_data: Optional[dict] = None) -> Optional[dict]:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return None
        conn.execute(
            """
            UPDATE saved_quotes
            SET name = ?, client_name = ?, notes = ?, blocks_json = ?, settings_json = ?, form_data = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND form_template_id = ?
            """,
            (
                name,
                client_name,
                notes,
                json.dumps(blocks_json),
                json.dumps(settings or {}),
                json.dumps(form_data or {}),
                quote_id,
                ft_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM saved_quotes WHERE id = ?", (quote_id,)).fetchone()
        result = dict(row) if row else None
        if result:
            result["blocks_json"] = json.loads(result.get("blocks_json", "[]"))
            result["settings_json"] = json.loads(result.get("settings_json", "{}"))
            result["form_data"] = json.loads(result.get("form_data", "{}"))
        return result
    finally:
        conn.close()


def get_output_template(form_key: str, db_path: Optional[Path] = None) -> Optional[dict]:
    """Return the default output template dict for a form template key, or None."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        row = conn.execute(
            """
            SELECT ot.id, ot.name, ot.sections_json, ot.css_json,
                   ot.is_default, ot.created_at, ot.updated_at
            FROM output_templates ot
            JOIN form_templates ft ON ft.id = ot.form_template_id
            WHERE ft.key = ? AND ot.is_default = 1
            ORDER BY ot.created_at DESC
            LIMIT 1
            """,
            (form_key,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["sections"] = json.loads(result.pop("sections_json", "{}"))
        result["css"] = json.loads(result.pop("css_json", "{}"))
        return result
    finally:
        conn.close()


def update_output_template(
    template_id: int,
    sections: Optional[dict] = None,
    css: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> bool:
    """Update sections_json and/or css_json for an output template."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        sets = []
        params = []
        if sections is not None:
            sets.append("sections_json = ?")
            params.append(json.dumps(sections))
        if css is not None:
            sets.append("css_json = ?")
            params.append(json.dumps(css))
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        conn.execute(
            f"UPDATE output_templates SET {', '.join(sets)} WHERE id = ?",
            params
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def list_output_templates(form_key: str, db_path: Optional[Path] = None) -> list:
    """Return all output templates for a form, ordered by is_default DESC, name."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        rows = conn.execute(
            """
            SELECT ot.id, ot.name, ot.is_default, ot.created_at, ot.updated_at
            FROM output_templates ot
            JOIN form_templates ft ON ft.id = ot.form_template_id
            WHERE ft.key = ?
            ORDER BY ot.is_default DESC, ot.name ASC
            """,
            (form_key,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Quote Editor Layouts ─────────────────────────────────────────────

def _get_form_template_id(conn: sqlite3.Connection, form_key: str) -> Optional[int]:
    row = conn.execute("SELECT id FROM form_templates WHERE key = ?", (form_key,)).fetchone()
    return int(row["id"]) if row else None


def create_quote_editor_layout(
    form_key: str,
    name: str = "Default",
    blocks_json: Optional[list] = None,
    is_default: bool = True,
    settings: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return None
        cur = conn.execute(
            """
            INSERT INTO quote_editor_layouts
                (form_template_id, name, blocks_json, is_default, settings_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ft_id, name, json.dumps(blocks_json or []), 1 if is_default else 0, json.dumps(settings or {})),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM quote_editor_layouts WHERE id = ?", (cur.lastrowid,)).fetchone()
        result = dict(row) if row else None
        if result:
            result["blocks_json"] = json.loads(result.get("blocks_json", "[]"))
            result["settings_json"] = json.loads(result.get("settings_json", "{}"))
        return result
    finally:
        conn.close()


def get_quote_editor_layout(
    form_key: str,
    layout_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return None
        if layout_id is not None:
            row = conn.execute(
                "SELECT * FROM quote_editor_layouts WHERE id = ? AND form_template_id = ?",
                (layout_id, ft_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM quote_editor_layouts
                WHERE form_template_id = ? AND is_default = 1
                ORDER BY created_at DESC LIMIT 1
                """,
                (ft_id,),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["blocks_json"] = json.loads(result.get("blocks_json", "[]"))
        result["settings_json"] = json.loads(result.get("settings_json", "{}"))
        return result
    finally:
        conn.close()


def list_quote_editor_layouts(form_key: str, db_path: Optional[Path] = None) -> list:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return []
        rows = conn.execute(
            """
            SELECT id, name, is_default, created_at, updated_at, settings_json
            FROM quote_editor_layouts
            WHERE form_template_id = ?
            ORDER BY is_default DESC, updated_at DESC
            """,
            (ft_id,),
        ).fetchall()
        result = []
        for r in rows:
            row = dict(r)
            row["settings_json"] = json.loads(row.get("settings_json") or "{}")
            result.append(row)
        return result
    finally:
        conn.close()


def update_quote_editor_layout(
    layout_id: int,
    form_key: str,
    blocks_json: Optional[list] = None,
    settings: Optional[dict] = None,
    name: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> bool:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        sets = []
        params = []
        if blocks_json is not None:
            sets.append("blocks_json = ?")
            params.append(json.dumps(blocks_json))
        if settings is not None:
            sets.append("settings_json = ?")
            params.append(json.dumps(settings))
        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([layout_id])
        conn.execute(
            f"UPDATE quote_editor_layouts SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def delete_quote_editor_layout(layout_id: int, form_key: str, db_path: Optional[Path] = None) -> bool:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return False
        conn.execute(
            "DELETE FROM quote_editor_layouts WHERE id = ? AND form_template_id = ?",
            (layout_id, ft_id),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def set_quote_editor_layout_default(layout_id: int, form_key: str, db_path: Optional[Path] = None) -> bool:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return False
        conn.execute("UPDATE quote_editor_layouts SET is_default = 0 WHERE form_template_id = ?", (ft_id,))
        conn.execute("UPDATE quote_editor_layouts SET is_default = 1 WHERE id = ? AND form_template_id = ?", (layout_id, ft_id))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def duplicate_quote_editor_layout(
    layout_id: int,
    form_key: str,
    new_name: str,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        row = conn.execute("SELECT * FROM quote_editor_layouts WHERE id = ?", (layout_id,)).fetchone()
        if not row:
            return None
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return None
        cur = conn.execute(
            """
            INSERT INTO quote_editor_layouts
                (form_template_id, name, blocks_json, settings_json, is_default)
            VALUES (?, ?, ?, ?, 0)
            """,
            (ft_id, new_name, row["blocks_json"], row["settings_json"]),
        )
        conn.commit()
        new_row = conn.execute("SELECT * FROM quote_editor_layouts WHERE id = ?", (cur.lastrowid,)).fetchone()
        result = dict(new_row) if new_row else None
        if result:
            result["blocks_json"] = json.loads(result.get("blocks_json", "[]"))
            result["settings_json"] = json.loads(result.get("settings_json", "{}"))
        return result
    finally:
        conn.close()


# ── Saved Quotes ─────────────────────────────────────────────────────

def save_quote(
    form_key: str,
    blocks_json: list,
    name: str,
    client_name: str = "",
    notes: str = "",
    layout_id: Optional[int] = None,
    user_id: Optional[int] = None,
    settings: Optional[dict] = None,
    form_data: Optional[dict] = None,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return None
        cur = conn.execute(
            """
            INSERT INTO saved_quotes
                (form_template_id, layout_id, name, client_name, notes, blocks_json, settings_json, form_data, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ft_id,
                layout_id,
                name,
                client_name,
                notes,
                json.dumps(blocks_json),
                json.dumps(settings or {}),
                json.dumps(form_data or {}),
                user_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM saved_quotes WHERE id = ?", (cur.lastrowid,)).fetchone()
        result = dict(row) if row else None
        if result:
            result["blocks_json"] = json.loads(result.get("blocks_json", "[]"))
            result["settings_json"] = json.loads(result.get("settings_json", "{}"))
            result["form_data"] = json.loads(result.get("form_data", "{}"))
        return result
    finally:
        conn.close()


def get_saved_quote(quote_id: int, form_key: str, db_path: Optional[Path] = None) -> Optional[dict]:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return None
        row = conn.execute(
            "SELECT * FROM saved_quotes WHERE id = ? AND form_template_id = ?",
            (quote_id, ft_id),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["blocks_json"] = json.loads(result.get("blocks_json", "[]"))
        result["settings_json"] = json.loads(result.get("settings_json", "{}"))
        result["form_data"] = json.loads(result.get("form_data", "{}"))
        return result
    finally:
        conn.close()


def list_saved_quotes(form_key: str, user_id: Optional[int] = None, db_path: Optional[Path] = None) -> list:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return []
        if user_id is not None:
            rows = conn.execute(
                """
                SELECT id, name, client_name, status, created_at, updated_at
                FROM saved_quotes
                WHERE form_template_id = ? AND (user_id = ? OR user_id IS NULL)
                ORDER BY updated_at DESC
                """,
                (ft_id, user_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, name, client_name, status, created_at, updated_at
                FROM saved_quotes
                WHERE form_template_id = ?
                ORDER BY updated_at DESC
                """,
                (ft_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_saved_quote(quote_id: int, form_key: str, db_path: Optional[Path] = None) -> bool:
    path = db_path or _default_db_path()
    conn = _connect(path)
    try:
        ft_id = _get_form_template_id(conn, form_key)
        if not ft_id:
            return False
        conn.execute(
            "DELETE FROM saved_quotes WHERE id = ? AND form_template_id = ?",
            (quote_id, ft_id),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()