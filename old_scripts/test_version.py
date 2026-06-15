import sys
sys.path.append('app')
import template_store as _ts

path = _ts._default_db_path()
conn = _ts._connect(path)
version_id = _ts._get_latest_version_id(conn, "first_client_template_v1")
print(f"Latest Version ID: {version_id}")

source_page_key = "special_notes_page"
source_page = conn.execute(
    "SELECT * FROM page_templates WHERE form_template_version_id = ? AND page_key = ?",
    (version_id, source_page_key)
).fetchone()

print(f"Source Page result: {dict(source_page) if source_page else None}")

# Find out what versions it DOES exist under
versions = conn.execute("SELECT form_template_version_id, page_key FROM page_templates WHERE page_key=?", (source_page_key,)).fetchall()
print(f"All versions containing {source_page_key}: {[dict(v) for v in versions]}")

