import sys
sys.path.append('app')
import template_store as _ts

print("Testing add_page...")
res_add = _ts.add_page("test_blank_key", "Test Blank Title", template_key="first_client_template_v1")
print(res_add)

print("\nTesting duplicate_page...")
res_dup = _ts.duplicate_page("special_notes_page", "test_dup_key", "Test Dup Title", template_key="first_client_template_v1")
print(res_dup)
