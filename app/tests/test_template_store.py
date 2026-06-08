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
            "option_sets",
            "option_items",
        }
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {row[0] for row in cur.fetchall()}
        conn.close()

        self.assertTrue(expected.issubset(names))

    def test_catalog_import_and_load_parity(self):
        """Importing sheet rows then loading via load_option_set must match
        the result of filtering the same rows in Python (the legacy path)."""
        from template_store import import_sheet_rows_to_catalog, load_option_set  # noqa: WPS433

        # Bootstrap a minimal template so a version row exists.
        payload = {"pages": {"special_notes_page": {"title": "SN", "navigation": {}, "fields": []}}}
        self.initialize_template_store(payload, template_key="parity_test_template")

        # Build a representative sheet dataset covering two prefixes.
        sheet_rows = [
            {"Line Code": "sn1", "Internal Description": "Special note A", "Include": "Y"},
            {"Line Code": "sn2", "Internal Description": "Special note B", "Include": "N"},
            {"Line Code": "sn3", "Internal Description": "Special note C", "Include": "Y"},
            {"Line Code": "bw1", "Internal Description": "Building works A", "Include": "N"},
            {"Line Code": "bw2", "Internal Description": "Building works B", "Include": "Y"},
        ]

        result = import_sheet_rows_to_catalog(
            sheet_rows,
            template_key="parity_test_template",
        )
        self.assertEqual(result["prefixes_written"], 2)
        self.assertEqual(result["items_written"], 5)

        # --- parity check for prefix 'sn' ---
        db_sn = load_option_set("sn", template_key="parity_test_template")
        self.assertIsNotNone(db_sn)

        # Legacy path: filter sheet_rows by startswith('sn')
        legacy_sn = [
            {"value": r["Line Code"], "label": r["Internal Description"], "is_included": r["Include"] == "Y"}
            for r in sheet_rows
            if r["Line Code"].startswith("sn")
        ]

        self.assertEqual(len(db_sn), len(legacy_sn))
        for db_item, legacy_item in zip(db_sn, legacy_sn):
            self.assertEqual(db_item["value"], legacy_item["value"])
            self.assertEqual(db_item["label"], legacy_item["label"])
            self.assertEqual(db_item["is_included"], legacy_item["is_included"])

        # --- parity check for prefix 'bw' ---
        db_bw = load_option_set("bw", template_key="parity_test_template")
        self.assertIsNotNone(db_bw)
        self.assertEqual(len(db_bw), 2)
        self.assertFalse(db_bw[0]["is_included"])  # bw1 is N
        self.assertTrue(db_bw[1]["is_included"])   # bw2 is Y

        # --- missing prefix returns None ---
        self.assertIsNone(load_option_set("xx", template_key="parity_test_template"))


if __name__ == "__main__":
    unittest.main()
