#!/usr/bin/env python3

import argparse
import sys
from urllib.parse import urljoin

import requests

DEFAULT_ROUTES = [
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


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke check core Quote Machine routes")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5000",
        help="Base URL where QM app is running",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    failures = []

    with requests.Session() as session:
        for route in DEFAULT_ROUTES:
            url = urljoin(args.base_url, route)
            try:
                response = session.get(url, timeout=args.timeout)
                status_ok = response.status_code < 400
                print(f"{response.status_code} {route}")
                if not status_ok:
                    failures.append((route, response.status_code, "HTTP error"))
            except requests.RequestException as exc:
                print(f"ERR {route} {exc}")
                failures.append((route, None, str(exc)))

    if failures:
        print("\nSmoke check failed:")
        for route, status, reason in failures:
            if status is None:
                print(f"- {route}: {reason}")
            else:
                print(f"- {route}: HTTP {status} ({reason})")
        return 1

    print("\nSmoke check passed for all routes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
