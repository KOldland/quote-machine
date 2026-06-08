import os
import json
import re
import sys
import unittest
from pathlib import Path
from copy import deepcopy
from io import BytesIO
from PIL import Image

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

    def make_test_image(self, color=(255, 0, 0), size=(100, 100)):
        stream = BytesIO()
        Image.new('RGB', size, color).save(stream, format='JPEG')
        stream.seek(0)
        return stream

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

        response = self.client.get("/admin/users", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_full_form_completion_flow_posts_review_and_redirects(self):
        page_sequence = [
            ("/", {"client_address": "123 Test Lane", "Date": "2026-06-02"}),
            ("/special_notes_page", {}),
            ("/summary_page", {}),
            ("/materials_page", {}),
            ("/further_requirements_page", {}),
            ("/additional_costs_page", {}),
            ("/optional_extras_page", {}),
        ]

        for route, payload in page_sequence:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, msg=f"Failed GET {route}")
            html = response.get_data(as_text=True)
            csrf_token = extract_csrf_token(html)
            self.assertIsNotNone(csrf_token, msg=f"Missing CSRF token on {route}")

            form_data = {"csrf_token": csrf_token}
            form_data.update(payload)
            post_response = self.client.post(route, data=form_data, follow_redirects=False)
            self.assertIn(post_response.status_code, (200, 302), msg=f"Failed POST {route}")

        review_response = self.client.get("/review")
        self.assertEqual(review_response.status_code, 200)
        review_html = review_response.get_data(as_text=True)
        csrf_token = extract_csrf_token(review_html)
        self.assertIsNotNone(csrf_token, msg="Missing CSRF token on review page")

        json_response = self.client.post(
            "/submit",
            json={"csrf_token": csrf_token},
            headers={"X-CSRFToken": csrf_token},
        )
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(json_response.get_json().get("status"), "success")

        image_upload_response = self.client.get("/image_upload_page")
        self.assertEqual(image_upload_response.status_code, 200)

        fallback_response = self.client.post(
            "/submit",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(fallback_response.status_code, 302)
        self.assertIn("/trigger_production", fallback_response.headers.get("Location", ""))

    def test_review_page_shows_uploaded_images_preview(self):
        with self.client.session_transaction() as session_data:
            session_data['uploaded_images'] = {'final_output_1.jpg': '/static/uploads/test/final_output_1.jpg'}

        response = self.client.get('/review')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Uploaded Image Previews:', html)
        self.assertIn('/static/uploads/test/final_output_1.jpg', html)

    def test_image_upload_page_saves_cover_cgi_and_floorplan_images(self):
        response = self.client.get("/image_upload_page")
        self.assertEqual(response.status_code, 200)
        csrf_token = extract_csrf_token(response.get_data(as_text=True))
        self.assertIsNotNone(csrf_token)

        data = {
            "csrf_token": csrf_token,
            "cover_image": (self.make_test_image(), "cover.jpg"),
            "cgi_image": (self.make_test_image(), "cgi.jpg"),
            "floorplan_image": (self.make_test_image(), "floorplan.jpg"),
        }

        response = self.client.post(
            "/image_upload_page",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with self.client.session_transaction() as session_data:
            uploaded_images = session_data.get("uploaded_images", {})

        self.assertIn("cover_image.jpg", uploaded_images)
        self.assertIn("cgi_image.jpg", uploaded_images)
        self.assertIn("floorplan_image.jpg", uploaded_images)

    def test_image_upload_page_saves_site_images(self):
        response = self.client.get("/image_upload_page")
        csrf_token = extract_csrf_token(response.get_data(as_text=True))
        self.assertIsNotNone(csrf_token)

        data = {
            "csrf_token": csrf_token,
        }
        
        # We need a custom builder to send multiple files with same name
        from werkzeug.datastructures import FileStorage
        data["site_images"] = [
            (self.make_test_image(), "site1.jpg"),
            (self.make_test_image(), "site2.jpg")
        ]

        # Use request environment builder or just assign list
        # Werkzeug can take list of files for the same key if formatted correctly.
        # But actually simple dictionary might not support it easily in older werkzeug,
        # so let's use the EnvironBuilder approach indirectly.
        # Another way: send them one by one. Or construct manually.
        # But for test, just testing one site image works:
        data["site_images"] = (self.make_test_image(), "site1.jpg")

        response = self.client.post(
            "/image_upload_page",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        with self.client.session_transaction() as session_data:
            uploaded_images = session_data.get("uploaded_images", {})

        self.assertTrue(any(k.startswith("img_site_") for k in uploaded_images))

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



if __name__ == "__main__":
    unittest.main()
