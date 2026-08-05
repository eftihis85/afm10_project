import csv
from pathlib import Path
import sqlite3
from files import (
                  EXPORTS_PATH,MAIN_DB_FILE_PATH, 
                   MONTH_PUT_CALL_PARITY, 
                   MONTH_PUT_CALL_IV_RESULTS, 
                   MONTH_PUT_CALL_SVI_RESULTS, 
                   MONTH_PUT_CALL_SSVI_RESULTS, 
                   MONTH_PUT_CALL_SSVI_DENSE_GRID)

def export_query_to_csv(db_path:Path, sql_file_path:Path, csv_file_name:str):
    try:
        # 1. Read the SQL query from the file
        with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
            query = sql_file.read()

        # 2. Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 3. Execute the query
        cursor.execute(query)

        # 4. Fetch headers (column names)
        # cursor.description contains metadata about the matching columns
        headers = [description[0] for description in cursor.description]

        # 5. Write results to CSV
        with open(
            EXPORTS_PATH / csv_file_name, 'w', newline='', encoding='utf-8'
        ) as csv_file:
            writer = csv.writer(csv_file)

            # Write the header row
            writer.writerow(headers)

            # Write the data rows
            # Using fetchall() works well for small-to-medium datasets.
            # For massive datasets, use fetchmany() in a loop to save memory.
            writer.writerows(cursor.fetchall())

        print(f'Success! Data exported to {csv_file_name}')

    except sqlite3.Error as e:
        print(f'Database error: {e}')
    except FileNotFoundError as e:
        print(f'File error: {e}')
    finally:
        # Clean up connection
        if 'conn' in locals():
            conn.close()


# --- Example Usage ---
export_query_to_csv(MAIN_DB_FILE_PATH, MONTH_PUT_CALL_SSVI_RESULTS, 'output_results.csv')