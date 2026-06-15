"import sys

filepath = '/Users/krisoldland/Documents/QM_web_app/app/templates/form.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = (
    '</label>\\n'
    '                        {% if edit_mode %}'
)

# The target: the first occurrence of </label> then {% if edit_mode %}
idx = content.find('</label>' + chr(10) + '                        {% if edit_mode %}')
if idx >= 0:
    # Find the start of the <label> line before it
    label_start = content.rfind('<label class=\"checkbox-label\"', 0, idx)
    if label_start >= 0:
        snippet = content[label_start:idx + 70]
        print('Found target at positions', label_start, 'to', idx + 70)
        print('Snippet:')
        print(repr(snippet))
    else:
        print('Found </label>+edit_mode at', idx, 'but could not find label start')
        print(repr(content[idx-80:idx+70]))
else:
    print('NOT FOUND')
    # Broader search
    idx2 = content.find('{% if edit_mode %}')
    if idx2 >= 0:
        print('First {% if edit_mode %} at', idx2)
        print(repr(content[idx2-100:idx2+30]))
"