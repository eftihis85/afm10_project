# read the "TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv", create a db, and using the data_decode.py store the data that are mapped successfully in one table in  DB.the data that they produce an error in ICEOptionData store them  

import csv
import sqlite3
import json
from pathlib import Path
from typing import Final
from data_decode import ICEOptionData


__DATA_FOLDER:Final = 'data'
__OPTIONS_FILE_NAME = 'TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv'
__OPTIONS_FILE_PATH:Final = Path(__file__).resolve().parent / __DATA_FOLDER / __OPTIONS_FILE_NAME 


def parse_option_csv(csv_file_path: Path):
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        
        fieldnames: list[str] = list(reader.fieldnames) if reader.fieldnames is not None else []
        fieldname_check= set(fieldnames).difference({'ts_event', 'rtype', 'publisher_id', 'instrument_id', 'open', 'high', 'low', 'close', 'volume', 'symbol'})
        if len(fieldnames) == 0 or len(fieldname_check) != 0:
            raise RuntimeError('Invalid fieldnames in the csv file')
        
        for row in reader:
            try:
                print(ICEOptionData(row))
            except Exception or Error as e:  
                print(row)
                
            # ts_event_dt = ICE_ts_event_to_dt(row.get('ts_event'))
            # rtype = row.get('rtype')
            # publisher_id = row.get('publisher_id')
            # instrument_id = row.get('instrument_id')
            # open_price = row.get('open')
            # high_price = row.get('high')
            # low_price = row.get('low')
            # close_price = row.get('close')
            # volume = row.get('volume')
            # symbol = row.get('symbol')
            
            print(row)

row = {'ts_event': '2026-04-20T00:00:00.000000000Z', 
       'rtype': '35', 
       'publisher_id': '85', 
       'instrument_id': '31131494', 
       'open': '3.700000000', 'high': '3.700000000', 'low': '3.700000000', 'close': '3.700000000', 
       'volume': '250', 
       'symbol': 'TFO  22  31131494'}



parse_option_csv(csv_file_path=__OPTIONS_FILE_PATH)


# def process_csv_and_store(csv_file_path: str, db_file_path: str):
#     # Connect to the SQLite database (this creates the file if it doesn't exist)
#     conn = sqlite3.connect(db_file_path)
#     cursor = conn.cursor()

#     # Create table for successful mappings
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS successful_mappings (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             symbol TEXT,
#             contract_code TEXT,
#             contract_type TEXT,
#             contract_delivery_term TEXT,
#             contract_delivery TEXT,
#             option_term TEXT,
#             option_payoff_style TEXT,
#             option_exercise_style TEXT,
#             strike_price REAL,
#             exact_expiry_date TEXT,
#             raw_csv_data TEXT
#         )
#     ''')

#     # Create table for errors
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS error_mappings (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             symbol TEXT,
#             error_message TEXT,
#             raw_csv_data TEXT
#         )
#     ''')
#     conn.commit()

#     with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:
#         reader = csv.DictReader(file)
        
#         # Guess the symbol column name (assuming it might be named 'symbol', 'ticker')
#         symbol_col = None
#         if reader.fieldnames:
#             for field in reader.fieldnames:
#                 if 'symbol' in field.lower() or 'ticker' in field.lower():
#                     symbol_col = field
#                     break
#             if not symbol_col:
#                 # Default to the first column if no common name was found
#                 symbol_col = reader.fieldnames[0]

#         for row in reader:
#             symbol = row.get(symbol_col, "")
#             raw_csv_data_str = json.dumps(row)

#             try:
#                 # Attempt to decode symbol
#                 decoded_data = ICEOptionData(symbol)
                
#                 cursor.execute('''
#                     INSERT INTO successful_mappings (
#                         symbol, contract_code, contract_type, contract_delivery_term, contract_delivery, 
#                         option_term, option_payoff_style, option_exercise_style, strike_price, exact_expiry_date, raw_csv_data
#                     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 ''', (
#                     symbol, decoded_data.contract_code, decoded_data.contract_type.description,
#                     decoded_data.contract_term.description, str(decoded_data.contract_delivery),
#                     decoded_data.option_term.description, decoded_data.option_payoff_style.description,
#                     decoded_data.option_exercise_style.description, decoded_data.strike_price,
#                     str(decoded_data.exact_expiry_date), raw_csv_data_str
#                 ))
#             except Exception as e:
#                 # Save records that throw an error during decoding
#                 cursor.execute('''
#                     INSERT INTO error_mappings (symbol, error_message, raw_csv_data)
#                     VALUES (?, ?, ?)
#                 ''', (symbol, str(e), raw_csv_data_str))

#     conn.commit()
#     conn.close()
#     print(f"Data processing complete. Saved to {db_file_path}.")

# if __name__ == "__main__":
#     csv_filename = "TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv"
#     db_filename = "ice_options.db"
#     process_csv_and_store(csv_filename, db_filename)