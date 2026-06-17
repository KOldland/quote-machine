import sys
sys.path.insert(0, '/Users/krisoldland/Documents/QM_web_app/app')
import template_store as ts

TEMPLATE_KEY = 'builder_beta'
DB_PATH = '/Users/krisoldland/Documents/QM_web_app/template_store.sqlite3'

# 1. Read current defaults
before = ts.get_payment_schedule_block(TEMPLATE_KEY, db_path=DB_PATH)
print('=== BEFORE ===')
print(before)

# 2. Upsert new values
print()
print('>>> Upserting deposit_pct=0.25, completion_pct=0.35, allow_user_override=True ...')
ts.upsert_payment_schedule_block(
    template_key=TEMPLATE_KEY,
    deposit_pct=0.25,
    completion_pct=0.35,
    allow_user_override=True,
    db_path=DB_PATH,
)

# 3. Read back and confirm
after = ts.get_payment_schedule_block(TEMPLATE_KEY, db_path=DB_PATH)
print()
print('=== AFTER UPSERT ===')
print(after)

# 4. Verify
assert after['deposit_pct'] == 0.25, f'Deposit mismatch: {after["deposit_pct"]}'
assert after['completion_pct'] == 0.35, f'Completion mismatch: {after["completion_pct"]}'
assert after['allow_user_override'] == True, f'Override mismatch: {after["allow_user_override"]}'
print()
print('All assertions passed! Full roundtrip works correctly.')

# 5. Restore originals
print()
print('>>> Restoring original values ...')
ts.upsert_payment_schedule_block(
    template_key=TEMPLATE_KEY,
    deposit_pct=before['deposit_pct'],
    completion_pct=before['completion_pct'],
    allow_user_override=before['allow_user_override'],
    db_path=DB_PATH,
)

# 6. Verify restore
restored = ts.get_payment_schedule_block(TEMPLATE_KEY, db_path=DB_PATH)
print()
print('=== AFTER RESTORE ===')
print(restored)
assert restored == before, f'Restore mismatch: {restored} != {before}'
print('Values restored to original state. Test complete.')