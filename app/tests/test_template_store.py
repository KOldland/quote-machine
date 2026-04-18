import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


class TemplateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "template_store_test.sqlite3"
        os.environ["QM_TEMPLATE_DB_PATH"] = str(self.db_path)

        # Import after setting env var so template_store resolves test DB path.
        from template_store import initialize_template_store  # noqa: WPS433

        self.initialize_template_store = initialize_template_store

    def tearDown(self):
        os.environ.pop("QM_TEMPLATE_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_initialize_and_load_template_payload(self):
        from template_store import load_template_payload, get_latest_template_version  # noqa: WPS433

        payload = {
            "pages": {
                "special_notes_page": {
                    "title": "Special Notes",
                    "navigation": {
                        "previous_endpoint": "index",
                        "next_endpoint": "summary_page",
                    },
                    "fields": [
                        {
                            "id": "selected_special_notes",
                            "name": "selected_special_notes",
                            "type": "checkbox_group",
                            "label": "Select notes",
                            "storage": {"kind": "checkbox_data", "key": "selected_special_notes"},
                        }
                    ],
                }
            }
        }

        result = self.initialize_template_store(payload, template_key="test_template")
        self.assertTrue(self.db_path.exists())
        self.assertEqual(result["pages"], 1)
        self.assertEqual(result["questions"], 1)
        self.assertEqual(result["logic_rules"], 8)

        latest = get_latest_template_version("test_template")
        self.assertEqual(latest, 1)

        loaded = load_template_payload("test_template")
        self.assertIsNotNone(loaded)
        self.assertIn("pages", loaded)
        self.assertIn("special_notes_page", loaded["pages"])

    def test_expected_tables_exist(self):
        payload = {"pages": {}}
        self.initialize_template_store(payload, template_key="empty_template")

        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        expected = {
            "tenants",
            "form_templates",
            "form_template_versions",
            "page_templates",
            "question_templates",
            "logic_rules",
            "template_rule_bindings",
        }
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {row[0] for row in cur.fetchall()}
        conn.close()

        self.assertTrue(expected.issubset(names))


if __name__ == "__main__":
    unittest.main()
