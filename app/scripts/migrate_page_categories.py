import json

def migrate_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    pages = data.get('builder_beta', {}).get('pages', {})
    for page_id, page_data in pages.items():
        blocks = page_data.get('blocks', [])
        categories_extracted = []
        
        for block in blocks:
            if block.get('block_type') == 'line_items_by_category':
                config = block.get('config', {})
                categories = config.get('categories', [])
                if categories:
                    for idx, cat_name in enumerate(categories):
                        categories_extracted.append({"name": cat_name, "sort_order": idx})
                # Remove categories from block config
                if 'categories' in config:
                    del config['categories']
                    
        if categories_extracted:
            page_data['categories'] = categories_extracted

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

migrate_file('app/page_schemas.json')
migrate_file('app/page_schemas_published.json')
print("Migration complete")
