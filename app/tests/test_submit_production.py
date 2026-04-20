import os
import json
import re
import sys
import unittest
from pathlib import Path
from copy import deepcopy

# Ensure app imports in local test mode without external Google credentials.
os.environ.setdefault("QM_TEST_MODE", "1")
os.environ.setdefault("QM_SECRET_KEY", "test-secret-key")

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from QMapp import app, page_schemas, page_schema_path, published_schema_path  # noqa: E402


def extract_csrf_token(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r"X-CSRFToken'\s*:\s*'([^']+)'", html)
    return match.group(1) if match else None


def find_first_value(html, field_name, fallback):
    pattern = rf'name="{re.escape(field_name)}" value="([^"]+)"'
    match = re.search(pattern, html)
    return match.group(1) if match else fallback


class SubmitProductionFlowTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with self.client.session_transaction() as session_data:
            session_data["role"] = "admin"
            session_data["username"] = "test-admin"

    def test_core_routes_available(self):
        routes = [
            "/",
            "/special_notes_page",
            "/summary_page",
            "/materials_page",
            "/further_requirements_page",
            "/additional_building_work_page",
            "/additional_costs_page",
            "/optional_extras_page",
            "/image_upload_page",
            "/review",
            "/production-page",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertLess(response.status_code, 400)

    def test_admin_routes_require_login(self):
        with self.client.session_transaction() as session_data:
            session_data.pop("role", None)
            session_data.pop("username", None)

        response = self.client.get("/form_builder_demo", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_special_notes_page_uses_schema_renderer(self):
        response = self.client.get("/special_notes_page")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Select any selected notes to be included:", html)
        self.assertIn('name="selected_special_notes"', html)

    def test_summary_page_building_works_uses_schema_renderer(self):
        response = self.client.get("/summary_page")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Building Works", html)
        self.assertIn('name="selected_building_works"', html)

    def test_form_builder_demo_page_available(self):
        response = self.client.get("/form_builder_demo")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Form Builder", html)
        self.assertIn("Edit Existing Page", html)
        self.assertIn("special_notes_page", html)
        self.assertIn("summary_page", html)

    def test_form_builder_page_editor_route_available(self):
        response = self.client.get("/form_builder_demo/page/special_notes_page")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Page Editor:", html)
        self.assertIn("Back to full builder", html)
        self.assertIn("special_notes_page", html)

    def test_builder_beta_page_editor_route_available(self):
        response = self.client.get("/builder_beta/page/special_notes_page")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Builder Beta", html)
        self.assertIn("Question Bank", html)
        self.assertIn("Inspector", html)

    def test_builder_beta_runtime_route_available(self):
        response = self.client.get("/builder_beta/render/special_notes_page")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Builder Beta Runtime Preview", html)
        self.assertIn("Save Runtime Draft", html)
        self.assertIn("Next Page", html)

    def test_builder_beta_runtime_payload_preview_endpoint(self):
        original_schema = deepcopy(page_schemas)
        try:
            page_schemas.setdefault("builder_beta", {}).setdefault("pages", {}).setdefault("special_notes_page", {}).setdefault("blocks", [])
            blocks = page_schemas["builder_beta"]["pages"]["special_notes_page"]["blocks"]
            blocks.append(
                {
                    "id": "special_notes_page__priced_text",
                    "block_type": "text_input",
                    "standard": {
                        "label": "Priced Text",
                        "name": "priced_text",
                        "required": False,
                        "help_text": "",
                        "source_prefix": "",
                        "placeholder": "",
                        "dropdown_choices": [],
                        "static_content": "",
                        "static_variant": "body",
                    },
                    "logic_options": {"visibility": "always", "depends_on_field": "", "depends_on_value": ""},
                    "pricing_options": {"enabled": True, "mode": "fixed", "fixed_amount": 125.5, "entered_key": "", "rate": 0.0, "quantity_key": "", "percent_of_subtotal": 0.0},
                    "output_options": {"include_in_output": True, "output_label": "Priced Text Output", "group": "General", "sort_order": 3, "value_mode": "show_value"},
                }
            )

            runtime_response = self.client.get("/builder_beta/render/special_notes_page")
            self.assertEqual(runtime_response.status_code, 200)
            html = runtime_response.get_data(as_text=True)
            csrf_token = extract_csrf_token(html)
            self.assertIsNotNone(csrf_token)

            submit_response = self.client.post(
                "/builder_beta/render/special_notes_page",
                data={
                    "csrf_token": csrf_token,
                    "priced_text": "Client value",
                },
                follow_redirects=True,
            )
            self.assertEqual(submit_response.status_code, 200)

            payload_response = self.client.get("/builder_beta/runtime_payload_json/special_notes_page")
            self.assertEqual(payload_response.status_code, 200)
            payload = payload_response.get_json()
            self.assertIsInstance(payload, dict)
            self.assertGreaterEqual(payload.get("total_pricing_amount", 0.0), 125.5)
            line_items = payload.get("line_items", [])
            self.assertTrue(any(item.get("output_label") == "Priced Text Output" and item.get("amount") == 125.5 for item in line_items))
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_builder_beta_runtime_payload_aggregates_across_answered_pages(self):
        original_schema = deepcopy(page_schemas)
        try:
            builder_beta_pages = page_schemas.setdefault("builder_beta", {}).setdefault("pages", {})
            builder_beta_pages.setdefault("special_notes_page", {}).setdefault("blocks", [])
            builder_beta_pages.setdefault("materials_page", {}).setdefault("blocks", [])

            special_blocks = builder_beta_pages["special_notes_page"]["blocks"]
            materials_blocks = builder_beta_pages["materials_page"]["blocks"]

            special_blocks.append(
                {
                    "id": "special_notes_page__fixed_total",
                    "block_type": "text_input",
                    "standard": {
                        "label": "Special Fixed",
                        "name": "special_fixed",
                        "required": False,
                        "help_text": "",
                        "source_prefix": "",
                        "placeholder": "",
                        "dropdown_choices": [],
                        "static_content": "",
                        "static_variant": "body",
                    },
                    "logic_options": {"visibility": "always", "depends_on_field": "", "depends_on_value": ""},
                    "pricing_options": {"enabled": True, "mode": "fixed", "fixed_amount": 100.0, "entered_key": "", "rate": 0.0, "quantity_key": "", "percent_of_subtotal": 0.0},
                    "output_options": {"include_in_output": True, "output_label": "Special Fixed", "group": "General", "sort_order": 0, "value_mode": "show_value"},
                }
            )

            materials_blocks.append(
                {
                    "id": "materials_page__fixed_total",
                    "block_type": "text_input",
                    "standard": {
                        "label": "Materials Fixed",
                        "name": "materials_fixed",
                        "required": False,
                        "help_text": "",
                        "source_prefix": "",
                        "placeholder": "",
                        "dropdown_choices": [],
                        "static_content": "",
                        "static_variant": "body",
                    },
                    "logic_options": {"visibility": "always", "depends_on_field": "", "depends_on_value": ""},
                    "pricing_options": {"enabled": True, "mode": "fixed", "fixed_amount": 50.0, "entered_key": "", "rate": 0.0, "quantity_key": "", "percent_of_subtotal": 0.0},
                    "output_options": {"include_in_output": True, "output_label": "Materials Fixed", "group": "General", "sort_order": 0, "value_mode": "show_value"},
                }
            )

            with self.client.session_transaction() as session_data:
                session_data["builder_beta_answers"] = {
                    "special_notes_page": {},
                    "materials_page": {},
                }

            response = self.client.get("/builder_beta/runtime_payload_json/special_notes_page")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIsInstance(payload, dict)
            self.assertEqual(payload.get("total_pricing_amount"), 150.0)
            self.assertEqual(payload.get("current_page", {}).get("total_pricing_amount"), 100.0)
            self.assertTrue(any(summary.get("page_id") == "materials_page" and summary.get("total_pricing_amount") == 50.0 for summary in payload.get("page_summaries", [])))
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_builder_beta_can_add_block(self):
        original_schema = deepcopy(page_schemas)
        try:
            response = self.client.get("/builder_beta/page/special_notes_page")
            self.assertEqual(response.status_code, 200)
            csrf_token = extract_csrf_token(response.get_data(as_text=True))
            self.assertIsNotNone(csrf_token)

            payload = {
                "csrf_token": csrf_token,
                "action": "add_block",
                "new_block_type": "text_input",
                "selected_block_id": "",
            }
            save_response = self.client.post(
                "/builder_beta/page/special_notes_page",
                data=payload,
                follow_redirects=True,
            )
            self.assertEqual(save_response.status_code, 200)
            html = save_response.get_data(as_text=True)
            self.assertIn("Builder beta changes saved", html)
            self.assertIn("text_input", html)

            builder_beta = page_schemas.get("builder_beta", {})
            page_blocks = builder_beta.get("pages", {}).get("special_notes_page", {}).get("blocks", [])
            self.assertTrue(any(block.get("block_type") == "text_input" for block in page_blocks))
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_builder_beta_save_block_persists_dropdown_and_static_payload(self):
        original_schema = deepcopy(page_schemas)
        try:
            page_schemas.setdefault("builder_beta", {}).setdefault("pages", {}).setdefault("special_notes_page", {}).setdefault("blocks", [])
            blocks = page_schemas["builder_beta"]["pages"]["special_notes_page"]["blocks"]

            blocks.append(
                {
                    "id": "special_notes_page__dropdown_test",
                    "block_type": "dropdown_select",
                    "standard": {
                        "label": "Dropdown Test",
                        "name": "dropdown_test",
                        "required": False,
                        "help_text": "",
                        "source_prefix": "",
                        "placeholder": "",
                        "dropdown_choices": ["One"],
                        "static_content": "",
                        "static_variant": "body",
                    },
                    "logic_options": {"visibility": "always", "depends_on_field": "", "depends_on_value": ""},
                    "pricing_options": {"enabled": False, "mode": "none", "fixed_amount": 0.0, "entered_key": "", "rate": 0.0, "quantity_key": "", "percent_of_subtotal": 0.0},
                    "output_options": {"include_in_output": True, "output_label": "Dropdown Test", "group": "General", "sort_order": 0, "value_mode": "show_value"},
                }
            )

            blocks.append(
                {
                    "id": "special_notes_page__static_test",
                    "block_type": "static_text_heading",
                    "standard": {
                        "label": "Static Test",
                        "name": "static_test",
                        "required": False,
                        "help_text": "",
                        "source_prefix": "",
                        "placeholder": "",
                        "dropdown_choices": [],
                        "static_content": "old",
                        "static_variant": "body",
                    },
                    "logic_options": {"visibility": "always", "depends_on_field": "", "depends_on_value": ""},
                    "pricing_options": {"enabled": False, "mode": "none", "fixed_amount": 0.0, "entered_key": "", "rate": 0.0, "quantity_key": "", "percent_of_subtotal": 0.0},
                    "output_options": {"include_in_output": True, "output_label": "Static Test", "group": "General", "sort_order": 1, "value_mode": "show_value"},
                }
            )

            response = self.client.get("/builder_beta/page/special_notes_page")
            self.assertEqual(response.status_code, 200)
            csrf_token = extract_csrf_token(response.get_data(as_text=True))
            self.assertIsNotNone(csrf_token)

            dropdown_payload = {
                "csrf_token": csrf_token,
                "action": "save_block",
                "block_id": "special_notes_page__dropdown_test",
                "selected_block_id": "special_notes_page__dropdown_test",
                "standard_label": "Dropdown Updated",
                "standard_name": "dropdown_updated",
                "standard_help_text": "",
                "standard_source_prefix": "",
                "standard_dropdown_choices": "Choice A\nChoice B\nChoice C",
                "logic_visibility": "always",
                "logic_depends_on_field": "",
                "logic_depends_on_value": "",
                "pricing_mode": "none",
                "pricing_fixed_amount": "0",
                "pricing_entered_key": "",
                "pricing_rate": "0",
                "pricing_quantity_key": "",
                "pricing_percent_of_subtotal": "0",
                "output_label": "Dropdown Updated",
                "output_group": "General",
                "output_sort_order": "0",
                "output_value_mode": "show_value",
            }
            save_dropdown = self.client.post("/builder_beta/page/special_notes_page", data=dropdown_payload, follow_redirects=True)
            self.assertEqual(save_dropdown.status_code, 200)

            static_payload = {
                "csrf_token": csrf_token,
                "action": "save_block",
                "block_id": "special_notes_page__static_test",
                "selected_block_id": "special_notes_page__static_test",
                "standard_label": "Static Updated",
                "standard_name": "static_updated",
                "standard_help_text": "",
                "standard_source_prefix": "",
                "standard_static_variant": "heading",
                "standard_static_content": "Important heading content",
                "logic_visibility": "always",
                "logic_depends_on_field": "",
                "logic_depends_on_value": "",
                "pricing_mode": "none",
                "pricing_fixed_amount": "0",
                "pricing_entered_key": "",
                "pricing_rate": "0",
                "pricing_quantity_key": "",
                "pricing_percent_of_subtotal": "0",
                "output_label": "Static Updated",
                "output_group": "General",
                "output_sort_order": "1",
                "output_value_mode": "show_value",
            }
            save_static = self.client.post("/builder_beta/page/special_notes_page", data=static_payload, follow_redirects=True)
            self.assertEqual(save_static.status_code, 200)

            persisted_blocks = page_schemas["builder_beta"]["pages"]["special_notes_page"]["blocks"]
            dropdown_block = next(block for block in persisted_blocks if block["id"] == "special_notes_page__dropdown_test")
            static_block = next(block for block in persisted_blocks if block["id"] == "special_notes_page__static_test")

            self.assertEqual(dropdown_block["standard"]["dropdown_choices"], ["Choice A", "Choice B", "Choice C"])
            self.assertEqual(static_block["standard"]["static_variant"], "heading")
            self.assertEqual(static_block["standard"]["static_content"], "Important heading content")
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_builder_beta_runtime_submission_persists_answers(self):
        response = self.client.get("/builder_beta/render/special_notes_page")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        csrf_token = extract_csrf_token(html)
        self.assertIsNotNone(csrf_token)

        selected_special_notes_value = find_first_value(html, "selected_special_notes", "sn1")
        payload = {
            "csrf_token": csrf_token,
            "selected_special_notes": selected_special_notes_value,
        }
        submit_response = self.client.post(
            "/builder_beta/render/special_notes_page",
            data=payload,
            follow_redirects=True,
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertIn("Builder beta runtime submission saved", submit_response.get_data(as_text=True))

        with self.client.session_transaction() as session_data:
            self.assertIn("builder_beta_answers", session_data)
            self.assertIn("special_notes_page", session_data["builder_beta_answers"])
            saved = session_data["builder_beta_answers"]["special_notes_page"]
            self.assertIn("selected_special_notes", saved)
            self.assertIn(selected_special_notes_value, saved["selected_special_notes"])

    def test_builder_beta_preview_json_uses_block_types(self):
        original_schema = deepcopy(page_schemas)
        try:
            page_schemas.setdefault("builder_beta", {}).setdefault("pages", {}).setdefault("special_notes_page", {}).setdefault("blocks", [])
            blocks = page_schemas["builder_beta"]["pages"]["special_notes_page"]["blocks"]

            blocks.append(
                {
                    "id": "special_notes_page__dropdown_type_test",
                    "block_type": "dropdown_select",
                    "standard": {
                        "label": "Stage",
                        "name": "stage",
                        "required": False,
                        "help_text": "",
                        "source_prefix": "",
                        "placeholder": "",
                        "dropdown_choices": ["A", "B"],
                        "static_content": "",
                        "static_variant": "body",
                    },
                    "logic_options": {"visibility": "always", "depends_on_field": "", "depends_on_value": ""},
                    "pricing_options": {"enabled": False, "mode": "none", "fixed_amount": 0.0, "entered_key": "", "rate": 0.0, "quantity_key": "", "percent_of_subtotal": 0.0},
                    "output_options": {"include_in_output": True, "output_label": "Stage", "group": "General", "sort_order": 1, "value_mode": "show_value"},
                }
            )

            blocks.append(
                {
                    "id": "special_notes_page__static_type_test",
                    "block_type": "static_text_heading",
                    "standard": {
                        "label": "Header",
                        "name": "header",
                        "required": False,
                        "help_text": "",
                        "source_prefix": "",
                        "placeholder": "",
                        "dropdown_choices": [],
                        "static_content": "Header content",
                        "static_variant": "heading",
                    },
                    "logic_options": {"visibility": "always", "depends_on_field": "", "depends_on_value": ""},
                    "pricing_options": {"enabled": False, "mode": "none", "fixed_amount": 0.0, "entered_key": "", "rate": 0.0, "quantity_key": "", "percent_of_subtotal": 0.0},
                    "output_options": {"include_in_output": True, "output_label": "Header", "group": "General", "sort_order": 2, "value_mode": "show_value"},
                }
            )

            response = self.client.get("/builder_beta/preview_json/special_notes_page")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIsInstance(payload, dict)
            fields = payload.get("fields", [])
            self.assertTrue(any(field.get("id") == "special_notes_page__dropdown_type_test" and field.get("type") == "dropdown_select" for field in fields))
            self.assertTrue(any(field.get("id") == "special_notes_page__static_type_test" and field.get("type") == "static_text_heading" for field in fields))
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_template_store_status_endpoint_available(self):
        response = self.client.get("/admin/template_store_status")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn("template_key", payload)
        self.assertIn("latest_version", payload)
        self.assertIn("tables", payload)
        self.assertIn("page_templates", payload["tables"])

    def test_template_store_templates_endpoint_available(self):
        response = self.client.get("/admin/template_store_templates")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn("templates", payload)
        self.assertIsInstance(payload["templates"], list)
        self.assertIn("active_template_key", payload)

    def test_template_clone_endpoint_creates_clone(self):
        clone_key = "kitchen_only_template_test"
        response = self.client.get(
            "/admin/template_clone",
            query_string={
                "new_template_key": clone_key,
                "scenario_key": "kitchen_only",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("template_key"), clone_key)
        self.assertIn("version", payload)
        self.assertIn("pages", payload)
        self.assertIn("questions", payload)

    def test_catalog_import_endpoint_imports_mock_data(self):
        response = self.client.post("/admin/catalog_import", json={})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn("prefixes_written", payload)
        self.assertIn("items_written", payload)
        self.assertGreater(payload["prefixes_written"], 0)
        self.assertGreater(payload["items_written"], 0)

    def test_catalog_import_endpoint_then_load_option_set(self):
        # Import the mock catalog.
        import_resp = self.client.post("/admin/catalog_import", json={})
        self.assertEqual(import_resp.status_code, 200)

        # After import, load_option_set should return data for a known prefix.
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from template_store import load_option_set
        options = load_option_set("sn")
        self.assertIsNotNone(options)
        self.assertGreater(len(options), 0)
        self.assertIn("value", options[0])
        self.assertIn("label", options[0])
        self.assertIn("is_included", options[0])

    def test_form_builder_demo_save_updates_live_label(self):
        original_schema = deepcopy(page_schemas)
        try:
            response = self.client.get("/form_builder_demo")
            self.assertEqual(response.status_code, 200)
            csrf_token = extract_csrf_token(response.get_data(as_text=True))
            self.assertIsNotNone(csrf_token)

            payload = {
                "csrf_token": csrf_token,
                "label__special_notes_page__0": "Demo Label Updated",
                "order__special_notes_page__0": "0",
                "label__summary_page__0": "Select items to include:",
                "order__summary_page__0": "0",
            }
            save_response = self.client.post(
                "/form_builder_demo",
                data=payload,
                follow_redirects=True,
            )
            self.assertEqual(save_response.status_code, 200)

            special_notes_response = self.client.get("/special_notes_page")
            self.assertEqual(special_notes_response.status_code, 200)
            self.assertIn("Demo Label Updated", special_notes_response.get_data(as_text=True))
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_form_builder_can_create_new_page_draft(self):
        original_schema = deepcopy(page_schemas)
        try:
            response = self.client.get("/form_builder_demo")
            self.assertEqual(response.status_code, 200)
            csrf_token = extract_csrf_token(response.get_data(as_text=True))
            self.assertIsNotNone(csrf_token)

            payload = {
                "csrf_token": csrf_token,
                "new_page_id": "site_survey_page",
                "new_page_title": "Site Survey",
                "new_page_prev": "additional_building_work_page",
                "new_page_next": "review",
            }
            save_response = self.client.post(
                "/form_builder_demo",
                data=payload,
                follow_redirects=True,
            )
            self.assertEqual(save_response.status_code, 200)

            self.assertIn("site_survey_page", page_schemas["pages"])
            self.assertEqual(page_schemas["pages"]["site_survey_page"]["title"], "Site Survey")

            builder_page = self.client.get("/form_builder_demo")
            self.assertEqual(builder_page.status_code, 200)
            self.assertIn("site_survey_page", builder_page.get_data(as_text=True))
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_submit_and_trigger_production(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        csrf_token = extract_csrf_token(response.get_data(as_text=True))
        self.assertIsNotNone(csrf_token)

        response = self.client.post(
            "/",
            data={
                "csrf_token": csrf_token,
                "client_address": "Test Address",
                "Date": "2026-04-15",
            },
            follow_redirects=True,
        )
        self.assertLess(response.status_code, 400)

        flow_steps = [
            ("/special_notes_page", "selected_special_notes", "sn1"),
            ("/summary_page", "selected_building_works", "bw1"),
            ("/materials_page", "selected_ew", "ew1"),
            ("/further_requirements_page", "selected_frc", "frc1"),
            ("/additional_building_work_page", "selected_ab", "ab1"),
        ]

        for path, field_name, fallback in flow_steps:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            csrf_token = extract_csrf_token(html)
            self.assertIsNotNone(csrf_token)
            value = find_first_value(html, field_name, fallback)

            post_data = {
                "csrf_token": csrf_token,
                field_name: value,
            }
            if path == "/further_requirements_page":
                post_data["selected_dw"] = find_first_value(html, "selected_dw", "dw1")

            response = self.client.post(path, data=post_data, follow_redirects=True)
            self.assertLess(response.status_code, 400)

        review_response = self.client.get("/review")
        self.assertEqual(review_response.status_code, 200)
        review_html = review_response.get_data(as_text=True)
        review_csrf = extract_csrf_token(review_html)
        self.assertIsNotNone(review_csrf)

        submit_response = self.client.post(
            "/submit",
            json={"smoke": True},
            headers={"X-CSRFToken": review_csrf},
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertIn("success", submit_response.get_data(as_text=True).lower())

        production_response = self.client.get("/trigger_production")
        self.assertEqual(production_response.status_code, 200)
        self.assertIn("open it in a new tab", production_response.get_data(as_text=True).lower())

    def test_additional_costs_uses_builder_pricing_rules(self):
        original_schema = deepcopy(page_schemas)
        try:
            builder_response = self.client.get("/form_builder_demo")
            self.assertEqual(builder_response.status_code, 200)
            csrf_token = extract_csrf_token(builder_response.get_data(as_text=True))
            self.assertIsNotNone(csrf_token)

            builder_payload = {
                "csrf_token": csrf_token,
                "label__special_notes_page__0": "Select any selected notes to be included:",
                "order__special_notes_page__0": "0",
                "label__summary_page__0": "Select items to include:",
                "order__summary_page__0": "0",
                "rules__kitchen_light_rate": "100",
                "rules__kitchen_point_rate": "200",
                "rules__loft_light_rate": "300",
                "rules__loft_point_rate": "400",
                "rules__rounding_precision": "2",
                "rules__deposit_percent": "10",
                "rules__stage_1_name": "Weeks 1-8",
                "rules__stage_1_percent": "50",
                "rules__stage_2_name": "Weeks 9-12",
                "rules__stage_2_percent": "30",
                "rules__stage_3_name": "Completion",
                "rules__stage_3_percent": "10",
            }
            save_response = self.client.post(
                "/form_builder_demo",
                data=builder_payload,
                follow_redirects=True,
            )
            self.assertEqual(save_response.status_code, 200)

            costs_page = self.client.get("/additional_costs_page")
            self.assertEqual(costs_page.status_code, 200)
            cost_csrf = extract_csrf_token(costs_page.get_data(as_text=True))
            self.assertIsNotNone(cost_csrf)

            post_response = self.client.post(
                "/additional_costs_page",
                data={
                    "csrf_token": cost_csrf,
                    "selected_kitchen_option": "elk0",
                    "selected_loft_option": "ell0",
                    "elkl0_amount": "2",
                    "elkp0_amount": "3",
                    "elll0_amount": "4",
                    "ellp0_amount": "5",
                },
                follow_redirects=False,
            )
            self.assertEqual(post_response.status_code, 302)

            with self.client.session_transaction() as session_data:
                self.assertEqual(session_data["data"]["elk0_cost"], 800.0)
                self.assertEqual(session_data["data"]["ell0_cost"], 3200.0)
                self.assertEqual(session_data["data"]["additional_costs_subtotal"], 4000.0)
                plan = session_data["data"]["payment_plan_preview"]
                self.assertEqual(plan["total_amount"], 4000.0)
                self.assertEqual(len(plan["entries"]), 4)
                self.assertEqual(plan["entries"][0]["name"], "Deposit")
                self.assertEqual(plan["entries"][0]["amount"], 400.0)
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)

    def test_publish_and_rollback_endpoints_work(self):
        original_schema = deepcopy(page_schemas)
        had_published_snapshot = published_schema_path.exists()
        published_snapshot_bytes = published_schema_path.read_bytes() if had_published_snapshot else None
        try:
            publish_response = self.client.post("/admin/publish_draft", json={})
            self.assertEqual(publish_response.status_code, 200)
            publish_payload = publish_response.get_json()
            self.assertTrue(publish_payload.get("ok"))
            self.assertTrue(published_schema_path.exists())

            page_schemas.setdefault("settings", {})["_rollback_test_flag"] = "changed-after-publish"
            with page_schema_path.open("w") as f:
                json.dump(page_schemas, f, indent=2)

            rollback_response = self.client.post("/admin/rollback", json={})
            self.assertEqual(rollback_response.status_code, 200)
            rollback_payload = rollback_response.get_json()
            self.assertTrue(rollback_payload.get("ok"))
            self.assertNotIn("_rollback_test_flag", page_schemas.get("settings", {}))
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)
            if had_published_snapshot and published_snapshot_bytes is not None:
                published_schema_path.write_bytes(published_snapshot_bytes)
            elif published_schema_path.exists() and not had_published_snapshot:
                published_schema_path.unlink()

    def test_entered_pricing_mode_renders_runtime_input(self):
        original_schema = deepcopy(page_schemas)
        try:
            field = page_schemas["pages"]["special_notes_page"]["fields"][0]
            field["pricing_options"] = {
                "enabled": True,
                "mode": "entered",
                "entered_key": "entered_amount_test",
            }
            with page_schema_path.open("w") as f:
                json.dump(page_schemas, f, indent=2)

            response = self.client.get("/special_notes_page")
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn('name="entered_amount_test"', html)
            self.assertIn("Enter amount", html)
        finally:
            page_schemas.clear()
            page_schemas.update(original_schema)
            with page_schema_path.open("w") as f:
                json.dump(original_schema, f, indent=2)


if __name__ == "__main__":
    unittest.main()
