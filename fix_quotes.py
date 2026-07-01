#!/usr/bin/env python3
"""Fix curly/smart quotes in QMapp.py by replacing them with straight quotes."""

import sys
import os

def fix_curly_quotes(filepath):
    """Read file, replace curly quotes, write back."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Curly quotes to replace
    replacements = [
        ('\u2018', "'"),   # left single quotation mark
        ('\u2019', "'"),   # right single quotation mark
        ('\u201b', "'"),   # single low-9 quotation mark
        ('\u2039', "'"),   # single left-pointing angle
        ('\u203a', "'"),   # single right-pointing angle
        ('\u201c', '"'),   # left double quotation mark
        ('\u201d', '"'),   # right double quotation mark
        ('\u201e', '"'),   # double low-9 quotation mark
        ('\u00ab', '"'),   # left-pointing double angle
        ('\u00bb', '"'),   # right-pointing double angle
    ]

    original_content = content
    for curly, straight in replacements:
        content = content.replace(curly, straight)

    # Write back if changes were made
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed curly quotes in {filepath}")
        print(f"  Replaced {len(replacements)} types of curly quotes")
    else:
        print(f"ℹ️ No curly quotes found in {filepath}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = os.path.join(os.path.dirname(__file__), 'app', 'QMapp.py')
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    fix_curly_quotes(filepath)