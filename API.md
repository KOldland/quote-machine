# Quote Machine API Documentation

## Export Endpoints

### PDF Export

**Endpoint:** `GET /api/export-pdf`

**Description:** Generates a PDF of the current quote using the output template stored in the database.

**Required Session Keys:**
- `form_key` (str): The form template key (e.g., 'standard_build')
- `form_data` (dict): Submitted form values used for quote calculation

**Response:**
- Content-Type: `application/pdf`
- Attachment: `quote.pdf`

**Process:**
1. Loads output template from DB (falls back to default)
2. Parses `sections_json` and `css_json`
3. Runs `Calculator.calculate_quote()` with session form data
4. Renders `export.html` with calc results + template
5. Converts HTML to PDF using WeasyPrint
6. Streams PDF as download

---

### DOCX Export

**Endpoint:** `GET /api/export-docx`

**Description:** Generates a DOCX (Microsoft Word) document of the current quote using the output template stored in the database.

**Required Session Keys:**
- `form_key` (str): The form template key
- `form_data` (dict): Submitted form values

**Response:**
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Attachment: `quote.docx`

**Process:**
1. Loads output template from DB (falls back to default)
2. Parses `sections_json` and `css_json`
3. Runs `Calculator.calculate_quote()`
4. Builds DOCX document with `python-docx`:
   - **Header**: Company name/logo (remote URLs downloaded safely)
   - **Footer**: Optional page numbers placeholder, terms text
   - **Body**: Client info, line‑item table, subtotals, payment schedule
5. Applies CSS styling: `fontFamily`, `fontSize`, `headingColor`, `paragraphSpacing`
6. Streams DOCX as download

**Supported Template Sections (`sections_json`):**
```json
{
  "header": {
    "enabled": true,
    "show_logo": false,
    "logo_url": "/static/logo.png",
    "company_name": "Your Company"
  },
  "footer": {
    "enabled": true,
    "show_page_numbers": false,
    "terms_text": "Terms and conditions apply."
  },
  "body": {
    "show_client_info": true,
    "show_line_items_table": true,
    "show_subtotals": true,
    "show_payment_schedule": true
  }
}
```

**Supported CSS (`css_json`):**
```json
{
  "fontFamily": "Times New Roman",
  "fontSize": 11,
  "headingColor": "#112233",
  "paragraphSpacing": 6
}
```

---

## Error Responses

| Status | Description |
|--------|-------------|
| 400 | `form_key` not found in session |
| 500 | Invalid template JSON or calculation error |

---

## Testing

Run export tests with:
```bash
pytest app/tests/test_export_docx.py -v
```

---

*Generated for Phase 5 – Wire Exports to Output Template*
