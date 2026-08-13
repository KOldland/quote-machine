"""
Quote Editor Export Endpoints

Provides PDF and DOCX export for block-based quote editor layouts.
"""

import io
import json
from flask import Blueprint, render_template, send_file, request, session, abort
from template_store import get_quote_editor_layout

quote_editor_export_bp = Blueprint('quote_editor_export', __name__)

SYSTEM_FONTS = {
    'Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Courier New',
    'Verdana', 'Trebuchet MS', 'Palatino', 'Garamond', 'Comic Sans MS',
    'Impact', 'Lucida Sans', 'Tahoma', 'Geneva', 'Segoe UI',
}

GOOGLE_FONTS = [
    'Roboto', 'Open Sans', 'Lora', 'Merriweather', 'Montserrat', 'Poppins',
]


def _is_system_font(font_family):
    if not font_family:
        return True
    primary = font_family.split(',')[0].strip().strip('"').strip("'")
    return primary.lower() in {f.lower() for f in SYSTEM_FONTS}


def _replace_placeholders(text, blocks):
    result = text
    result = result.replace('{{quote_ref}}', session.get('quote_ref', ''))
    result = result.replace('{{client_name}}', session.get('client_name', ''))
    result = result.replace('{{client_address}}', session.get('client_address', ''))
    result = result.replace('{{proposal_date}}', session.get('proposal_date', ''))
    grand_total = _get_grand_total(blocks)
    result = result.replace('{{grand_total}}', f'{grand_total:.2f}')
    return result


def _get_grand_total(blocks):
    for block in blocks:
        if block.get('type') == 'calculator':
            snapshot = block.get('snapshot', {})
            return snapshot.get('grand_total', 0)
    return 0


def _build_divider_html(style, thickness, css_mode=True):
    t = float(thickness) if thickness else 1
    if not style or style == 'none':
        return ''
    border_style_map = {
        'single': 'solid',
        'japanese_dots': 'dotted',
        'double': 'double',
        'circles': 'dotted',
    }
    border_style = border_style_map.get(style, 'solid')
    if css_mode:
        extra = 'border-top-style: round;' if style == 'circles' else ''
        return (
            f'<hr class="hf-divider" style="border:none; '
            f'border-top-width:{t}px; border-top-style:{border_style}; '
            f'{extra} border-top-color:#000; margin:4px 0;" />'
        )
    else:
        return f'<div style="border-top:{t}px {border_style} #000; margin:4px 0;"></div>'


def _build_doc_id_text(doc_id_type, doc_id_manual, quote_ref, client_address):
    if doc_id_type == 'customer_address':
        return client_address or ''
    elif doc_id_type == 'quote_number':
        return quote_ref or ''
    elif doc_id_type == 'manual':
        return doc_id_manual or ''
    return ''


def _generate_header_html(document_styles, blocks, css_mode=True):
    hdr = document_styles.get('header') or {}
    if not hdr.get('enabled', True):
        return ''

    logo_url = hdr.get('logo_url', '')
    logo_width = hdr.get('logo_width', 120)
    logo_height = hdr.get('logo_height', 40)
    logo_alignment = hdr.get('logo_alignment', 'center')
    doc_id_type = hdr.get('document_id_type', 'quote_number')
    doc_id_manual = hdr.get('document_id_manual', '')
    doc_id_alignment = hdr.get('doc_id_alignment', 'center')
    quote_ref = session.get('quote_ref', '')
    client_address = session.get('client_address', '')
    divider_style = hdr.get('divider_style', 'single')
    divider_thickness = hdr.get('divider_thickness', 1)
    header_font_size = document_styles.get('header_font_size', 10)
    margin_top = hdr.get('margin_top', 0)
    margin_bottom = hdr.get('margin_bottom', 0)
    margin_left = hdr.get('margin_left', 0)
    margin_right = hdr.get('margin_right', 0)

    parts = []
    if logo_url:
        margin_left_css = '0' if logo_alignment == 'left' else 'auto' if logo_alignment == 'center' else 'auto'
        margin_right_css = 'auto' if logo_alignment == 'center' else '0' if logo_alignment == 'right' else 'auto'
        parts.append(
            f'<img src="{logo_url}" style="max-width:{logo_width}px; max-height:{logo_height}px; '
            f'display:block; margin:0 {margin_right_css} 4px {margin_left_css}; object-fit:contain;" />'
        )

    doc_id_text = _build_doc_id_text(doc_id_type, doc_id_manual, quote_ref, client_address)
    if doc_id_text:
        parts.append(f'<div class="hf-doc-id" style="text-align:{doc_id_alignment};">{_replace_placeholders(doc_id_text, blocks)}</div>')

    parts.append(_build_divider_html(divider_style, divider_thickness, css_mode))

    if css_mode:
        wrapper_style = f'padding:0; margin:0 {margin_right}mm {margin_bottom}mm {margin_left}mm;'
        if margin_top:
            wrapper_style = f'margin-top:{margin_top}mm; {wrapper_style}'
    else:
        wrapper_style = ''

    inner = '\n'.join(parts)
    if wrapper_style:
        return f'<div class="preview-header" style="{wrapper_style} font-size:{header_font_size}px;">{inner}</div>'
    return inner


def _generate_footer_html(document_styles, blocks, css_mode=True):
    ftr = document_styles.get('footer') or {}
    if not ftr.get('enabled', True):
        return ''

    divider_style = ftr.get('divider_style', 'single')
    divider_thickness = ftr.get('divider_thickness', 1)
    page_number_mode = ftr.get('page_number_mode', 'on')
    page_number_alignment = ftr.get('page_number_alignment', 'center')
    footer_font_size = document_styles.get('footer_font_size', 8)

    parts = []
    parts.append(_build_divider_html(divider_style, divider_thickness, css_mode))

    if page_number_mode != 'off':
        page_num_html = '<span class="page-number"></span>'
        page_total_html = '<span class="page-total"></span>'
        parts.append(f'<div class="hf-page-num" style="text-align:{page_number_alignment};">Page {page_num_html} of {page_total_html}</div>')

    return '\n'.join(parts)


def _typo_css(selector, t):
    """Build a CSS declaration block for one typography element."""
    if not t:
        return ''
    decls = []
    if t.get('family'):
        decls.append(f"font-family: {t['family']};")
    if t.get('weight'):
        decls.append(f"font-weight: {t['weight']};")
    if t.get('size'):
        decls.append(f"font-size: {t['size']}px;")
    if t.get('bold'):
        decls.append("font-weight: bold;")
    if t.get('italic'):
        decls.append("font-style: italic;")
    if t.get('underline'):
        decls.append("text-decoration: underline;")
    elif t.get('bold') is False and t.get('italic') is False:
        pass
    if t.get('color'):
        decls.append(f"color: {t['color']};")
    if not decls:
        return ''
    return f"{selector} {{ {' '.join(decls)} }}\n"


def _theme_css(document_styles):
    """Return a CSS string derived from the document_styles theme object."""
    if not document_styles:
        return ''
    css = []

    typo = document_styles.get('typography') or {}
    css.append(_typo_css('h1', typo.get('h1')))
    css.append(_typo_css('h2', typo.get('h2')))
    css.append(_typo_css('h3', typo.get('h3')))
    css.append(_typo_css('.qe-para', typo.get('para')))
    css.append(_typo_css('.qe-notes', typo.get('notes')))
    css.append(_typo_css('.qe-guide', typo.get('guide')))

    tables = document_styles.get('tables') or {}
    if tables:
        border = tables.get('border', '1px solid #ccc')
        header_bg = tables.get('header_bg', '#f5f5f5')
        row_bg = tables.get('row_bg', '#ffffff')
        alt_row_bg = tables.get('alt_row_bg', '#fafafa')
        font_size = tables.get('font_size', 14)
        css.append(
            f".calc-table {{ border-collapse: collapse; width: 100%; font-size: {font_size}px; }}\n"
        )
        css.append(
            f".calc-table th, .calc-table td {{ border: {border}; padding: 6px; text-align: left; }}\n"
        )
        css.append(f".calc-table th {{ background: {header_bg}; }}\n")
        css.append(f".calc-table tbody tr {{ background: {row_bg}; }}\n")
        css.append(
            f".calc-table tbody tr:nth-child(even) {{ background: {alt_row_bg}; }}\n"
        )

    images = document_styles.get('images') or {}
    if images:
        frame = images.get('frame', 'none')
        shadow = images.get('shadow', False)
        img_decls = []
        if frame and frame != 'none':
            img_decls.append(f"border: {frame};")
        if shadow:
            img_decls.append("box-shadow: 0 4px 12px rgba(0,0,0,0.2);")
        if img_decls:
            css.append(f".block-image img, .block-image_group img {{ {' '.join(img_decls)} }}\n")

    links = document_styles.get('links') or {}
    if links:
        color = links.get('color', '#0d6efd')
        decoration = 'underline' if links.get('underline', True) else 'none'
        css.append(f"a {{ color: {color}; text-decoration: {decoration}; }}\n")

    return '\n'.join(c for c in css if c)


def _apply_typo_to_run(run, typo):
    """Best-effort DOCX run styling from a typography element dict."""
    if not typo:
        return
    from docx.shared import Pt, RGBColor
    if typo.get('size'):
        run.font.size = Pt(typo['size'])
    if typo.get('bold'):
        run.font.bold = True
    if typo.get('italic'):
        run.font.italic = True
    if typo.get('underline'):
        run.font.underline = True
    weight = typo.get('weight')
    if weight in ('bold', '700', '600', '500'):
        run.font.bold = True
    color = typo.get('color')
    if color and isinstance(color, str) and color.startswith('#'):
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            run.font.color.rgb = RGBColor(r, g, b)
        except Exception:
            pass


def _load_blocks():
    form_key = session.get('template_key', 'builder_beta')
    layout_id = request.args.get('layout_id', type=int)
    layout = get_quote_editor_layout(form_key, layout_id=layout_id)
    if not layout:
        layout = get_quote_editor_layout(form_key)
    if not layout:
        return [], {}
    return layout.get('blocks_json', []), layout.get('settings_json', {}).get('document_styles', {})


@quote_editor_export_bp.route('/api/quote-editor/export-pdf')
def export_pdf():
    from weasyprint import HTML
    blocks, document_styles = _load_blocks()
    grand_total = _get_grand_total(blocks)
    theme_css = _theme_css(document_styles)

    hdr = (document_styles or {}).get('header') or {}
    ftr = (document_styles or {}).get('footer') or {}

    header_html = _generate_header_html(document_styles, blocks) if hdr.get('enabled', True) else ''
    footer_html = _generate_footer_html(document_styles, blocks) if ftr.get('enabled', True) else ''

    rendered_html = render_template(
        'quote_editor_export.html',
        blocks=blocks,
        document_styles=document_styles,
        theme_css=theme_css,
        quote_ref=session.get('quote_ref', ''),
        client_name=session.get('client_name', ''),
        client_address=session.get('client_address', ''),
        proposal_date=session.get('proposal_date', ''),
        grand_total=grand_total,
        header_html=header_html,
        footer_html=footer_html,
        header_hide_on_cover=hdr.get('hide_on_cover', False),
        footer_hide_on_cover=ftr.get('hide_on_cover', False),
    )
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

    blocks, document_styles = _load_blocks()
    doc = Document()

    default_font = document_styles.get('font_family', 'Arial, sans-serif')
    if ',' in default_font:
        default_font = default_font.split(',')[0].strip()
    doc.styles['Normal'].font.name = default_font

    section = doc.sections[0]
    margins = document_styles.get('margins', {})
    if margins:
        section.top_margin = Pt(margins.get('margin_top', 20))
        section.bottom_margin = Pt(margins.get('margin_bottom', 20))
        section.left_margin = Pt(margins.get('margin_left', 25))
        section.right_margin = Pt(margins.get('margin_right', 25))

    hdr = (document_styles or {}).get('header') or {}
    ftr = (document_styles or {}).get('footer') or {}

    header_html = _generate_header_html(document_styles, blocks, css_mode=False) if hdr.get('enabled', True) else ''
    footer_html = _generate_footer_html(document_styles, blocks, css_mode=False) if ftr.get('enabled', True) else ''

    if header_html or footer_html:
        for sec in doc.sections:
            if header_html:
                hdr_sec = sec.header
                hdr_sec.is_linked_to_previous = False
                hp = hdr_sec.paragraphs[0] if hdr_sec.paragraphs else hdr_sec.add_paragraph()
                hp.text = _replace_placeholders(header_html, blocks)
            if footer_html:
                ftr_sec = sec.footer
                ftr_sec.is_linked_to_previous = False
                fp = ftr_sec.paragraphs[0] if ftr_sec.paragraphs else ftr_sec.add_paragraph()
                fp.text = _replace_placeholders(footer_html, blocks)

    for block in blocks:
        btype = block.get('type', 'notes')
        settings = block.get('settings', {})
        margin_top = settings.get('margin_top', 8)
        margin_bottom = settings.get('margin_bottom', 8)
        padding = settings.get('padding', 12)
        alignment = settings.get('alignment', 'left')
        font_size = settings.get('font_size', 16)
        typo = (document_styles.get('typography') or {}) if document_styles else {}
        list_type = block.get('list_type')
        list_style = 'List Bullet' if list_type == 'ul' else 'List Number' if list_type == 'ol' else None

        # Skip page_break blocks in DOCX (they're handled by page breaks in PDF via CSS)
        if btype == 'page_break':
            doc.add_page_break()
            continue

        if btype == 'page_title':
            snapshot = block.get('snapshot', {})
            title = snapshot.get('title', '')
            if title:
                p = doc.add_heading(title, level=1)
                p.paragraph_format.space_after = Pt(margin_bottom)
                for run in p.runs:
                    _apply_typo_to_run(run, typo.get('h1'))

        elif btype == 'category_title':
            snapshot = block.get('snapshot', {})
            title = snapshot.get('title', '')
            if title:
                p = doc.add_heading(title, level=2)
                p.paragraph_format.space_after = Pt(margin_bottom)
                for run in p.runs:
                    _apply_typo_to_run(run, typo.get('h2'))

        elif btype == 'form_question':
            snapshot = block.get('snapshot', {})
            label = snapshot.get('label', '')
            value = snapshot.get('value', '')
            override_content = (block.get('editor_overrides') or {}).get('content')
            if isinstance(override_content, str) and override_content.strip():
                p = doc.add_paragraph(style=list_style)
                p.add_run(override_content)
                p.paragraph_format.space_after = Pt(margin_bottom)
                if alignment == 'center':
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif alignment == 'right':
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                continue
            p = doc.add_paragraph(style=list_style)
            if label:
                r = p.add_run(f"{label}: ")
                r.bold = True
                r.font.size = Pt(font_size)
                _apply_typo_to_run(r, typo.get('para'))
            run = p.add_run(str(value))
            run.font.size = Pt(font_size)
            _apply_typo_to_run(run, typo.get('para'))
            p.paragraph_format.space_after = Pt(margin_bottom)
            if alignment == 'center':
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif alignment == 'right':
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

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
            r.font.size = Pt(font_size)
            p.paragraph_format.space_after = Pt(margin_bottom)

        elif btype == 'notes':
            content = block.get('snapshot', {}).get('content', '')
            if content:
                p = doc.add_paragraph(content, style=list_style)
                for run in p.runs:
                    run.font.size = Pt(font_size)
                    _apply_typo_to_run(run, typo.get('notes'))
                p.paragraph_format.space_after = Pt(margin_bottom)

        elif btype in ('image', 'image_group'):
            snapshot = block.get('snapshot', {})
            images = snapshot.get('images', []) if btype == 'image_group' else [snapshot]
            for img in images:
                url = img.get('url', '')
                if url:
                    try:
                        from io import BytesIO
                        import requests as req
                        img_resp = req.get(url, timeout=10)
                        if img_resp.status_code == 200:
                            img_bytes = BytesIO(img_resp.content)
                            doc.add_picture(img_bytes, width=Inches(5.5))
                            last_paragraph = doc.paragraphs[-1]
                            last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    except Exception:
                        pass
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