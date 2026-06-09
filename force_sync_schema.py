
import sqlite3
import os

def force_sync_schema():
    db_path = os.path.join('app', 'template_store.sqlite3')
    template_key = os.getenv('QM_TEMPLATE_KEY', 'first_client_template_v1')
    
    pages_to_sync = [
        ('index', 'Project Details'),
        ('special_notes_page', 'Special Notes'),
        ('summary_page', 'Summary'),
        ('materials_page', 'Materials & Details'),
        ('further_requirements_page', 'Further Requirements'),
        ('additional_building_work_page', 'Additional Building Work'),
        ('additional_costs_page', 'Additional Costs'),
        ('optional_extras_page', 'Optional Extras'),
        ('image_upload_page', 'Image Upload')
    ]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get the active template version ID
        cursor.execute("SELECT id FROM form_templates WHERE key = ?", (template_key,))
        template_row = cursor.fetchone()
        if not template_row:
            print(f"Error: Template with key '{template_key}' not found.")
            return
        template_id = template_row[0]

        cursor.execute("SELECT id FROM form_template_versions WHERE form_template_id = ? ORDER BY version DESC LIMIT 1", (template_id,))
        version_row = cursor.fetchone()
        if not version_row:
            print(f"Error: No versions found for template key '{template_key}'.")
            return
        version_id = version_row[0]

        print(f"Syncing pages for template_key='{template_key}', version_id={version_id}...")

        for index, (page_key, title) in enumerate(pages_to_sync):
            # Check if page already exists for this version
            cursor.execute("SELECT id FROM page_templates WHERE page_key = ? AND form_template_version_id = ?", (page_key, version_id))
            existing_page = cursor.fetchone()

            if existing_page:
                print(f"Page '{page_key}' already exists. Skipping.")
                continue

            # Insert if it doesn't exist
            sql = """
                INSERT INTO page_templates (page_key, title, display_order, form_template_version_id, metadata_json)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (page_key, title, index, version_id, '{}'))
            print(f"Inserted page '{page_key}' with display_order {index}.")

        conn.commit()
        print("Schema sync completed successfully.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    force_sync_schema()
