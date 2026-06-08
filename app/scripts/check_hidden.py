import json

data = json.load(open('app/page_schemas.json'))
pages = {p['id']: p for p in data.get('pages', [])}

for page_id in ['materials_page', 'further_requirements_page']:
    page = pages.get(page_id, {})
    blocks = page.get('builder_beta', {}).get('blocks', [])
    print(f'\n=== {page_id} ===')
    for b in blocks:
        print(f"  {b.get('id','?'):30s}  type={b.get('type','?'):20s}  hidden={b.get('hidden', False)}")
