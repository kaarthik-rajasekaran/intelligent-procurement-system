import sqlite3

conn = sqlite3.connect('procurement.db')
cursor = conn.cursor()

# Add expected_delivery_date to quotations if not exists
try:
    cursor.execute('ALTER TABLE quotations ADD COLUMN expected_delivery_date TEXT')
    print('Added expected_delivery_date to quotations')
except Exception as e:
    print(f'Skipped (already exists): {e}')

# Update RFQ statuses
cursor.execute("UPDATE rfqs SET status = 'AWAITING_QUOTATION' WHERE status = 'ISSUED'")
print(f'Updated {cursor.rowcount} RFQs: ISSUED -> AWAITING_QUOTATION')

cursor.execute("UPDATE rfqs SET status = 'QUOTATION_RECEIVED' WHERE status = 'QUOTED'")
print(f'Updated {cursor.rowcount} RFQs: QUOTED -> QUOTATION_RECEIVED')

conn.commit()
conn.close()
print('Migration complete.')
