import io
import json
import requests
from urllib.parse import urlparse
import tempfile, os
from flask import Blueprint, render_template, send_file, session, abort
import weasyprint
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from template_store import get_output_template, create_default_output_template
from calculator import calculate_quote

export_bp = Blueprint('export', __name__)

@export_bp.route('/api/export-pdf')
def export_pdf():
    """Produce a PDF of the current quote using the output‑template stored in the DB."""
    # 1️⃣ Determine which form we are exporting
    form_key = session.get('form_key', 'kitchen_only_template_test')  # Default for testing

    # 2️⃣ Load the output template (fallback to default)
    template = get_output_template(form_key)
    if not template:
        template = create_default_output_template(form_key)

    # Parse JSON stored in DB
    try:
        sections = template['sections']
        css = template['css']
    except Exception as e:
        abort(500, description=f'Invalid template data: {e}')

    # 3️⃣ Run the calculator to get fresh quote data
    form_data = session.get('form_data', {})
    calc_result = calculate_quote(form_key, form_data)

    # 4️⃣ Render HTML with template sections and CSS
    rendered_html = render_template(
        'export.html',
        calc_result=calc_result,
        sections=sections,
        css=css
    )

    # 5️⃣ Convert HTML → PDF with WeasyPrint
    pdf_bytes = weasyprint.HTML(string=rendered_html).write_pdf()

    # 6️⃣ Stream the PDF back to the client
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='quote.pdf'
    )

@export_bp.route('/api/export-docx')
def export_docx():
    """Produce a DOCX of the current quote using the output‑template stored in the DB.
    The DOCX is built with python‑docx, applying header/footer and basic styling
    from the template's `sections_json` and `css_json`.
    """
    form_key = session.get('form_key', 'kitchen_only_template_test')  # Default for testing

    # Load template with graceful fallback
    template = get_output_template(form_key)
    if not template:
        template = create_default_output_template(form_key)

    try:
        sections = template['sections']
        css = template['css']
    except Exception as e:
        abort(500, description=f'Invalid template data: {e}')

    # Fresh calculation
    form_data = session.get('form_data', {})
    calc_result = calculate_quote(form_key, form_data)

    # ---------------------------------------------------------------------
    # Build DOCX document
    # ---------------------------------------------------------------------
    doc = Document()

    # ---- Header ----------------------------------------------------------
    header_cfg = sections.get('header', {})
    if header_cfg.get('enabled', True):
        header = doc.sections[0].header
        if header_cfg.get('show_logo') and header_cfg.get('logo_url'):
            # Insert logo image - handle remote URLs safely
            logo_url = header_cfg['logo_url']
            try:
                parsed = urlparse(logo_url)
                if parsed.scheme in ('http', 'https'):
                    # Download remote image to temp file
                    resp = requests.get(logo_url, timeout=5)
                    resp.raise_for_status()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(parsed.path)[1] or '.png') as tmp:
                        tmp.write(resp.content)
                        tmp_path = tmp.name
                    header.paragraphs[0].add_run().add_picture(tmp_path, width=Inches(1.5))
                    os.unlink(tmp_path)
                else:
                    # Local file path
                    header.paragraphs[0].add_run().add_picture(logo_url, width=Inches(1.5))
            except Exception:
                # Fallback to company name if image fails
                header.paragraphs[0].add_run(header_cfg.get('company_name', ''))
        else:
            header.paragraphs[0].text = header_cfg.get('company_name', '')
        header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ---- Footer ----------------------------------------------------------
    footer_cfg = sections.get('footer', {})
    if footer_cfg.get('enabled', True):
        footer = doc.sections[0].footer
        p = footer.paragraphs[0]
        if footer_cfg.get('show_page_numbers'):
            # Simple placeholder; a real field would require low‑level XML manipulation
            p.text = "Page {PAGE}"
            # No further run needed
        if footer_cfg.get('terms_text'):
            p.add_run(' – ' + footer_cfg['terms_text'])
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ---- Body ------------------------------------------------------------
    body_cfg = sections.get('body', {})
    if body_cfg.get('show_client_info', True):
        p = doc.add_paragraph()
        p.add_run('Client Information').bold = True
        p.add_run('\n')
        client_name = calc_result.get('client_name', 'N/A')
        client_addr = calc_result.get('client_address', 'N/A')
        p.add_run(f'Name: {client_name}\nAddress: {client_addr}')
        p.add_run('\n')

    # ---- Line Items Table ------------------------------------------------
    if body_cfg.get('show_line_items_table', True):
        table = doc.add_table(rows=1, cols=5)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Item'
        hdr_cells[1].text = 'Description'
        hdr_cells[2].text = 'Qty'
        hdr_cells[3].text = 'Unit Cost'
        hdr_cells[4].text = 'Total'
        for group in calc_result.get('groups', []):
            for item in group.get('items', []):
                row_cells = table.add_row().cells
                row_cells[0].text = item.get('output_title', '')
                row_cells[1].text = item.get('internal_description', '')
                row_cells[2].text = str(item.get('units', 1))
                row_cells[3].text = f"{item.get('unit_cost', 0):.2f}"
                row_cells[4].text = f"{item.get('line_total', 0):.2f}"
        doc.add_paragraph('\n')

    # ---- Subtotals & Totals ---------------------------------------------
    if body_cfg.get('show_subtotals', True):
        p = doc.add_paragraph()
        p.add_run('Subtotals').bold = True
        for group in calc_result.get('groups', []):
            p.add_run(f"\n{group['name']}: {group['subtotal']:.2f}")
        p.add_run(f"\nGrand Total: {calc_result.get('grand_total', 0):.2f}")
        p.add_run('\n')

    # ---- Payment Schedule ------------------------------------------------
    if body_cfg.get('show_payment_schedule', True):
        p = doc.add_paragraph()
        p.add_run('Payment Schedule').bold = True
        p.add_run(f"\nDeposit ({calc_result.get('deposit_pct', 0)*100:.0f}%): {calc_result.get('deposit_amount',0):.2f}")
        p.add_run(f"\nCompletion ({calc_result.get('completion_pct',0)*100:.0f}%): {calc_result.get('completion_amount',0):.2f}")
        p.add_run(f"\nBalance: {calc_result.get('middle_balance',0):.2f}")

    # ---------------------------------------------------------------------
    # Apply simple CSS styling (font name, size, bold headings)
    # ---------------------------------------------------------------------
    default_font = css.get('fontFamily', 'Times New Roman')
    default_size = css.get('fontSize', 11)
    heading_color = css.get('headingColor')  # optional hex string like "#112233"
    paragraph_spacing = css.get('paragraphSpacing')  # optional number (points)
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.name = default_font
            run.font.size = Pt(default_size)
            if heading_color and paragraph.style.name.startswith('Heading'):
                # Apply heading color if defined and valid hex
                try:
                    color_hex = heading_color.lstrip('#')
                    if len(color_hex) == 6:
                        run.font.color.rgb = RGBColor.from_string(color_hex)
                except Exception:
                    pass  # Ignore invalid color values
            if paragraph_spacing:
                paragraph.paragraph_format.space_after = Pt(paragraph_spacing)
    # ---------------------------------------------------------------------
    # Stream the DOCX back to the client
    # ---------------------------------------------------------------------
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return send_file(
        doc_io,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name='quote.docx'
    )

