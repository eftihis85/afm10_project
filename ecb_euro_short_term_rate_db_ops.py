import csv
import sqlite3
from files import EUR_SHORT_TERM_RATE_FILE_PATH, MAIN_DB_FILE_PATH



# 1. Connect to SQLite database
conn = sqlite3.connect(MAIN_DB_FILE_PATH)
cursor = conn.cursor()

# 2. Explicitly create the table structure
# Note: Column names are sanitized to keep queries simple later.
cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS euro_short_term_rates (
        date TEXT PRIMARY KEY,
        time_period TEXT,
        calculation_method INTEGER,
        euro_short_term_rate REAL
    )
'''
)

# 3. Read CSV and insert records
csv_file = EUR_SHORT_TERM_RATE_FILE_PATH

with open(csv_file, mode='r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # Skip the header row

    # Use a parameterized query to securely insert the data
    insert_query = '''
        INSERT INTO euro_short_term_rates (date, time_period, calculation_method, euro_short_term_rate)
        VALUES (?, ?, ?, ?)
    '''

    # Bulk insert for efficiency
    cursor.executemany(insert_query, reader)

# 4. Commit changes and close the connection
conn.commit()
conn.close()

print('Table created and data uploaded successfully!')