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

from QMapp import app, page_schemas, page_schema_path  # noqa: E402


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
        self.assertIn("special_notes_page", html)
        self.assertIn("summary_page", html)

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


if __name__ == "__main__":
    unittest.main()
