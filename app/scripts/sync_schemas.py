
import sys
from pathlib import Path
import json

# Add app directory to sys.path to allow for absolute imports
app_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(app_dir))

try:
    from template_store import initialize_template_store
except ImportError:
    print("Error: Could not import 'initialize_template_store' from 'template_store'.")
    print("Please ensure the app directory is in the Python path and the file exists.")
    sys.exit(1)

# The page_schemas are loaded in QMapp.py, so we need to replicate that logic
# to pass the object to the initialization function.
page_schema_path = app_dir / 'page_schemas.json'
if not page_schema_path.exists():
    print(f"Error: page_schemas.json not found at {page_schema_path}")
    sys.exit(1)

with page_schema_path.open() as f:
    page_schemas = json.load(f)

print("Loaded page_schemas.json...")
print("Synchronizing database with latest schemas...")

try:
    result = initialize_template_store(page_schemas)
    print("\nSynchronization complete!")
    print("Summary:")
    for key, value in result.items():
        print(f"- {key}: {value}")
except Exception as e:
    print(f"\nAn error occurred during synchronization: {e}")
    sys.exit(1)

print("\nDatabase successfully synchronized with page_schemas.json.")
