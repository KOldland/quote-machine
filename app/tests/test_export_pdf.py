import pytest


def test_export_pdf_endpoint(client, authenticated_admin):
    """Ensure the PDF export endpoint returns a PDF file.

    The test simulates a session where ``quote_html`` has been stored – this is the
    HTML snippet the review page would normally place in the session after the
    calculator runs.  The endpoint should respond with a 200 status, a PDF MIME
    type and a Content‑Disposition header that ends with ``.pdf"``.
    """
    html = "<html><body><h1>Test Quote</h1><p>Sample content</p></body></html>"
    with client.session_transaction() as sess:
        sess["quote_html"] = html
        sess["data"] = {"client_name": "TestClient", "Date": "2024/01/01"}

    response = client.get("/api/export-pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    content_disp = response.headers.get("Content-Disposition", "")
    assert ".pdf" in content_disp.lower()


def test_export_pdf_no_html(client, authenticated_admin):
    """Verify a 400 is returned when quote_html is missing."""
    response = client.get("/api/export-pdf")
    assert response.status_code == 400


def test_export_docx_endpoint(client, authenticated_admin):
    """Ensure the DOCX export endpoint returns a DOCX file.

    Requires calculator to run — we set up minimal session data.
    """
    with client.session_transaction() as sess:
        sess["checkbox_data"] = {}
        sess["data"] = {"client_name": "TestClient", "Date": "2024/01/01"}
        sess["overrides"] = {}

    response = client.get("/api/export-docx")
    assert response.status_code == 200
    assert "application/vnd.openxmlformats" in response.mimetype
    content_disp = response.headers.get("Content-Disposition", "")
    assert ".docx" in content_disp.lower()

