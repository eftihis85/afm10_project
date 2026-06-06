import sqlite3
import csv

from sqlite3_helper.sqlite3_helper import Sqlite3ConnectionProvider
from files import MAIN_DB_FILE_PATH, MONTH_PUT_CALL_PARITY


def export_month_difference_to_csv():
    # 2. Define the month difference SQL query using single quotes
    query = '''
    SELECT 
        contract_delivery_period,
        option_expiry_date,
        ( (strftime('%Y', option_expiry_date) - strftime('%Y', contract_delivery_period || '-01')) * 12 + 
          (strftime('%m', option_expiry_date) - strftime('%m', contract_delivery_period || '-01')) ) AS standard_months_apart
    FROM 
        ice_options_data_month;
    '''
    with Sqlite3ConnectionProvider(db_path=MAIN_DB_FILE_PATH).connection as conn:
        cursor = conn.cursor()


    # 1. Read the query string from your external sql file
        try:
            with open(MONTH_PUT_CALL_PARITY, 'r', encoding='utf-8') as sql_file:
                query = sql_file.read()
        except FileNotFoundError:
            print('Error: The file query.sql was not found.')
            return
        try:
            # 3. Execute the calculation query
            cursor.execute(query)
            
            # 4. Fetch all rows and extract column headers from the cursor description
            rows = cursor.fetchall()
            headers = [description[0] for description in cursor.description]

            # 5. Open and write the data directly to a CSV file
            with open('month_differences.csv', 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                
                # Write column titles first
                writer.writerow(headers)
                
                # Write all data sets
                writer.writerows(rows)
                
            print(f'Successfully exported {len(rows)} rows to month_differences.csv')

        except sqlite3.Error as error:
            print(f'An error occurred: {error}')
            
        finally:
            # 6. Securely close database connection elements
            cursor.close()

if __name__ == '__main__':
    export_month_difference_to_csv()