#!/usr/bin/env python3
"""Reset demo state to known-good baseline."""
import json
import sys
from pathlib import Path

def reset_demo():
    app_dir = Path(__file__).parent.parent
    published_path = app_dir / 'page_schemas_published.json'
    
    if not published_path.exists():
        print(f"ERROR: baseline not found at {published_path}")
        return False
    
    try:
        with published_path.open('r') as f:
            baseline = json.load(f)
        draft_path = app_dir / 'page_schemas.json'
        with draft_path.open('w') as f:
            json.dump(baseline, f, indent=2)
        print(f"✓ RESET OK: draft restored from baseline")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == '__main__':
    sys.exit(0 if reset_demo() else 1)
