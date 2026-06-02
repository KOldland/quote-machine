#!/usr/bin/env python3

import argparse
import re
import sys

import requests


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


def expect_ok(response, step_name):
    if response.status_code >= 400:
        print(f"FAIL: {step_name} {response.status_code}")
        sys.exit(1)


def get_form(session, base_url, path):
    response = session.get(f"{base_url}{path}")
    expect_ok(response, f"GET {path}")
    csrf_token = extract_csrf_token(response.text)
    if not csrf_token:
        print(f"FAIL: GET {path} missing csrf_token")
        sys.exit(1)
    return response.text, csrf_token


def post_form(session, base_url, path, data):
    response = session.post(f"{base_url}{path}", data=data, allow_redirects=True)
    expect_ok(response, f"POST {path}")
    return response


def main(base_url):
    session = requests.Session()

    html, csrf_token = get_form(session, base_url, "/")
    post_form(
        session,
        base_url,
        "/",
        {
            "csrf_token": csrf_token,
            "client_address": "Test Address",
            "Date": "2026-04-15",
        },
    )

    html, csrf_token = get_form(session, base_url, "/special_notes_page")
    special_note = find_first_value(html, "selected_special_notes", "sn1")
    post_form(
        session,
        base_url,
        "/special_notes_page",
        {
            "csrf_token": csrf_token,
            "selected_special_notes": special_note,
        },
    )

    html, csrf_token = get_form(session, base_url, "/summary_page")
    building_work = find_first_value(html, "selected_building_works", "bw1")
    post_form(
        session,
        base_url,
        "/summary_page",
        {
            "csrf_token": csrf_token,
            "selected_building_works": building_work,
        },
    )

    html, csrf_token = get_form(session, base_url, "/materials_page")
    wall_option = find_first_value(html, "selected_ew", "ew1")
    post_form(
        session,
        base_url,
        "/materials_page",
        {
            "csrf_token": csrf_token,
            "selected_ew": wall_option,
        },
    )

    html, csrf_token = get_form(session, base_url, "/further_requirements_page")
    frc_option = find_first_value(html, "selected_frc", "frc1")
    demolition_option = find_first_value(html, "selected_dw", "dw1")
    post_form(
        session,
        base_url,
        "/further_requirements_page",
        {
            "csrf_token": csrf_token,
            "selected_frc": frc_option,
            "selected_dw": demolition_option,
        },
    )

    html, csrf_token = get_form(session, base_url, "/additional_building_work_page")
    ab_option = find_first_value(html, "selected_ab", "ab1")
    post_form(
        session,
        base_url,
        "/additional_building_work_page",
        {
            "csrf_token": csrf_token,
            "selected_ab": ab_option,
        },
    )

    html, csrf_token = get_form(session, base_url, "/additional_costs_page")
    html, csrf_token = get_form(session, base_url, "/optional_extras_page")
    html, csrf_token = get_form(session, base_url, "/image_upload_page")

    html, csrf_token = get_form(session, base_url, "/review")
    submit_response = session.post(
        f"{base_url}/submit",
        json={"smoke": True},
        headers={"X-CSRFToken": csrf_token},
    )
    expect_ok(submit_response, "POST /submit")
    if "success" not in submit_response.text.lower():
        print("FAIL: POST /submit response did not indicate success")
        sys.exit(1)

    production_response = session.get(f"{base_url}/trigger_production")
    expect_ok(production_response, "GET /trigger_production")
    if "open it in a new tab" not in production_response.text.lower():
        print("FAIL: /trigger_production did not return a document link block")
        sys.exit(1)

    print("PASS: submit-to-production smoke flow completed.")
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test full submit-to-production flow")
    parser.add_argument("--base-url", default="http://127.0.0.1:5051")
    args = parser.parse_args()
    main(args.base_url)
