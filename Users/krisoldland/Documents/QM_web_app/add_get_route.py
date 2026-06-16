"import re
with open('app/QMapp.py', 'r') as f:
    content = f.read()

old = \"    return jsonify({'success': True})\\n\\n\\n@app.route('/builder_beta/page_details_save/<page_key>', methods=['POST'])\"

new = \"\"\"    return jsonify({'success': True})


@app.route('/admin/payment-schedule-config', methods=['GET'])
@require_role('admin')
def admin_payment_schedule_config():
    \"\"\"Render admin config page for payment-schedule defaults.\"\"\"
    import template_store as ts
    ps = ts.get_payment_schedule_block('builder_beta')
    return render_template(
        'admin_payment_schedule.html',
        deposit_pct=ps.get('deposit_pct', 0.10),
        completion_pct=ps.get('completion_pct', 0.10),
        allow_user_override=ps.get('allow_user_override', False),
    )


@app.route('/builder_beta/page_details_save/<page_key>', methods=['POST'])
\"\"\"

if old in content:
    content = content.replace(old, new, 1)
    with open('app/QMapp.py', 'w') as f:
        f.write(content)
    print('QMapp.py updated successfully')
else:
    print('Could not find insertion point in QMapp.py')
    idx = content.find('return jsonify')
    if idx > 0:
        print(repr(content[idx:idx+400]))
"