"""
Quote Editor Export Endpoints

Provides PDF and DOCX export for block-based quote editor layouts.
"""

import io
import json
from flask import Blueprint, render_template, send_file, request, session, abort
from template_store import get_quote_editor_layout

quote_editor_export_bp = Blueprint('quote_editor_export', __name__)


def _load_blocks():
    form_key = session.get('template_key', 'builder_beta')
    layout_id = request.args.get('layout_id', type=int)
    layout = get_quote_editor_layout(form_key, layout_id=layout_id)
    if not layout:
        layout = get_quote_editor_layout(form_key)
    if not layout:
        return []
    return layout.get('blocks_json', [])


@quote_editor_export_bp.route('/api/quote-editor/export-pdf')
def export_pdf():
    from weasyprint import HTML
    blocks = _load_blocks()
    rendered_html = render_template('quote_editor_export.html', blocks=blocks)
    pdf_bytes = HTML(string=rendered_html).write_pdf()
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='quote.pdf'
    )


@quote_editor_export_bp.route('/api/quote-editor/export-docx')
def export_docx():
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import requests
    import tempfile
    import os

    blocks = _load_blocks()
    doc = Document()

    for block in blocks:
        btype = block.get('type', 'notes')
        settings = block.get('settings', {})
        margin_top = settings.get('margin_top', 8)
        margin_bottom = settings.get('margin_bottom', 8)
        padding = settings.get('padding', 12)
        alignment = settings.get('alignment', 'left')

        if btype == 'page_title':
            snapshot = block.get('snapshot', {})
            title = snapshot.get('title', '')
            if title:
                p = doc.add_heading(title, level=1)
                p.paragraph_format.space_after = Pt(margin_bottom)

        elif btype == 'category_title':
            snapshot = block.get('snapshot', {})
            title = snapshot.get('title', '')
            if title:
                p = doc.add_heading(title, level=2)
                p.paragraph_format.space_after = Pt(margin_bottom)

        elif btype == 'form_question':
            snapshot = block.get('snapshot', {})
            label = snapshot.get('label', '')
            value = snapshot.get('value', '')
            p = doc.add_paragraph()
            if label:
                r = p.add_run(f"{label}: ")
                r.bold = True
            p.add_run(str(value))
            p.paragraph_format.space_after = Pt(margin_bottom)

        elif btype == 'calculator':
            snapshot = block.get('snapshot', {})
            groups = snapshot.get('groups', [])
            if groups:
                table = doc.add_table(rows=1, cols=4)
                hdr = table.rows[0].cells
                hdr[0].text = 'Item'
                hdr[1].text = 'Description'
                hdr[2].text = 'Total'
                hdr[3].text = 'Group'
                for group in groups:
                    for item in group.get('items', []):
                        row = table.add_row().cells
                        row[0].text = item.get('output_title', '')
                        row[1].text = item.get('internal_description', '')
                        row[2].text = f"{item.get('line_total', 0):.2f}"
                        row[3].text = group.get('name', '')
                doc.add_paragraph()
            p = doc.add_paragraph()
            r = p.add_run(f"Grand Total: {snapshot.get('grand_total', 0):.2f}")
            r.bold = True
            p.paragraph_format.space_after = Pt(margin_bottom)

        elif btype == 'notes':
            content = block.get('snapshot', {}).get('content', '')
            if content:
                p = doc.add_paragraph(content)
                p.paragraph_format.space_after = Pt(margin_bottom)

        elif btype in ('image', 'image_group'):
            snapshot = block.get('snapshot', {})
            images = snapshot.get('images', []) if btype == 'image_group' else [snapshot]
            for img in images:
                url = img.get('url', '')
                if url:
                    try:
                        if url.startswith('http'):
                            resp = requests.get(url, timeout=5)
                            resp.raise_for_status()
                            suffix = os.path.splitext(url)[1] or '.png'
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(resp.content)
                                tmp_path = tmp.name
                            doc.add_picture(tmp_path, width=Inches(5.5))
                            os.unlink(tmp_path)
                        else:
                            static_root = os.path.join(os.path.dirname(__file__), 'static')
                            full_path = os.path.join(static_root, url.lstrip('/'))
                            if os.path.exists(full_path):
                                doc.add_picture(full_path, width=Inches(5.5))
                    except Exception:
                        pass
            last = doc.paragraphs[-1] if doc.paragraphs else doc.add_paragraph()
            last.paragraph_format.space_after = Pt(margin_bottom)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name='quote.docx'
    )