# read the "TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv", create a db, and using the data_decode.py store the data that are mapped successfully in one table in  DB.the data that they produce an error in ICEOptionData store them  

import csv
import sqlite3
from pathlib import Path
from typing import Final, Any
from data_decode_options import (ICEOptionsData_QSY, ICEOptionsData_Unencoded_TruncationIssue, ICEOptionsData_Unencoded_Unknown, ICEOptionsDataUnion, ICEOptionsDataABC, ICEOptionsData_Month, ICEOptionsData_Unencoded_Month, ICEOptionsData_Unencoded_RecordsWithId)
from sqlite3_helper.table_management import DbDatatype, DbField, DbTableMixin, TableTemplateEnum
from sqlite3_helper.sqlite3_helper import create_database, dynamic_database_connection_closer, Sqlite3ConnectionProvider

__DATA_FOLDER:Final = 'data'
__OPTIONS_FILE_NAME = 'TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv'
__FUTURES_FILE_NAME = 'TFM · Dutch TTF Natural Gas Futures - ohlcv-1d - 2021-01-01 00:00 2026-05-21 00:00.csv'
__MAIN_DB_FILENAME = 'database.db'
__OPTIONS_FILE_PATH:Final = Path(__file__).resolve().parent / __DATA_FOLDER / __OPTIONS_FILE_NAME 
__FUTURES_FILE_PATH:Final = Path(__file__).resolve().parent / __DATA_FOLDER / __FUTURES_FILE_NAME 
__MAIN_DB_FILE_PATH:Final = Path(__file__).resolve().parent / __DATA_FOLDER / __MAIN_DB_FILENAME 



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Create database
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

create_database(db_filepath=__MAIN_DB_FILE_PATH)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Table definition
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class ICEOptionsDataMonthTable(DbTableMixin, TableTemplateEnum):
    
    # The event timestamp as the number of nanoseconds since the UNIX epoch.
    ts_event = DbField(datatype=DbDatatype.DATETIME_INT, is_pk=True)

    # he publisher ID assigned by Databento, which denotes the dataset and venue.
    publisher_id = DbField(datatype=DbDatatype.INT, is_pk=True)
    
    # The numeric instrument ID.
    instrument_id = DbField(datatype=DbDatatype.INT, is_pk=True)
    
    # id = DbField(datatype=DbDatatype.INT, is_pk=True)
    symbol = DbField(datatype=DbDatatype.TEXT)
    
    # The record type. Each schema corresponds with a single rtype value
    rtype = DbField(datatype=DbDatatype.INT) 
    
    open = DbField(datatype=DbDatatype.REAL)
    high = DbField(datatype=DbDatatype.REAL)
    low = DbField(datatype=DbDatatype.REAL)
    close = DbField(datatype=DbDatatype.REAL)
    volume = DbField(datatype=DbDatatype.REAL)
    contract_code = DbField(datatype=DbDatatype.TEXT)
    contract_type = DbField(datatype=DbDatatype.TEXT)
    contract_term = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period = DbField(datatype=DbDatatype.TEXT)
    option_term = DbField(datatype=DbDatatype.TEXT)
    option_payoff_style = DbField(datatype=DbDatatype.TEXT)
    option_exercise_style = DbField(datatype=DbDatatype.TEXT)
    strike_decimals = DbField(datatype=DbDatatype.INT)
    strike_price = DbField(datatype=DbDatatype.REAL)
    exact_expiry_date = DbField(datatype=DbDatatype.DATETIME_INT)

    @classmethod
    def get_table_name(cls) -> str:
        return 'ice_options_data_month'
    
    @classmethod
    def get_row_data(cls, *args: Any, **kwargs: Any) -> dict[Any, Any]:
        return {}
    

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Create table
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

init_sql=ICEOptionsDataMonthTable.get_create_table_sql(ICEOptionsDataMonthTable)
@dynamic_database_connection_closer
def create_table(sqlite3_connection_provider: Sqlite3ConnectionProvider):
    with sqlite3_connection_provider.connection as conn:
        conn.executescript(init_sql)


sqlite3_connection_provider = Sqlite3ConnectionProvider(db_path=__MAIN_DB_FILE_PATH)
create_table(sqlite3_connection_provider=sqlite3_connection_provider)



def parse_options_csv(csv_file_path: Path):
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        fieldnames: list[str] = list(reader.fieldnames) if reader.fieldnames is not None else []
        fieldname_check= set(fieldnames).difference({'ts_event', 'rtype', 'publisher_id', 'instrument_id', 'open', 'high', 'low', 'close', 'volume', 'symbol'})
        if len(fieldnames) == 0 or len(fieldname_check) != 0:
            raise RuntimeError('Invalid fieldnames in the csv file')
        
        ice_options_data_month_list: list[ICEOptionsData_Month] =[]
        for row in reader:
            
            # pattern = r'([A-Z\s]{5})([\d\s]{4})([\d]{8})'
            
            # symbol = row['symbol']
            # match = re.match(pattern=pattern, string= symbol) # 'TFO  22  31131494'
            
            # # TFO  65  31143475
            # if match:
            #     print(symbol)
            
            
            a:ICEOptionsDataUnion = ICEOptionsDataABC.decode_csv_row(row)
            
            match a:
                case ICEOptionsData_Month():
                    # print(a)
                    ice_options_data_month_list.append(a)
                case ICEOptionsData_Unencoded_Month():
                    print('Undecoded month' + str(a.symbol))
                case ICEOptionsData_QSY():
                    pass
                case ICEOptionsData_Unencoded_RecordsWithId():
                    pass
                case ICEOptionsData_Unencoded_TruncationIssue():
                    pass
                case ICEOptionsData_Unencoded_Unknown():
                    print('Un-decoded ' + str(a.symbol))
        
        
        with Sqlite3ConnectionProvider(db_path=__MAIN_DB_FILE_PATH).connection as conn:
            query = '''
                INSERT INTO ice_options_data_month (
                    symbol,
                    ts_event,
                    rtype,
                    publisher_id,
                    instrument_id,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    contract_code,
                    contract_type,
                    contract_term,
                    contract_delivery_period,
                    option_term,
                    option_payoff_style,
                    option_exercise_style,
                    strike_decimals,
                    strike_price,
                    exact_expiry_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            conn.executemany(query,
                              [(d.symbol, d.ts_event, d.rtype, d.publisher_id,
                                d.instrument_id, d.open, d.high,
                                d.low, d.close, d.volume,
                                d.contract_code, d.contract_type.code, d.contract_term.code,
                                d.contract_delivery_period.__str__(), d.option_term.code, d.option_payoff_style.code,
                                d.option_exercise_style.code, d.strike_decimals, d.strike_price,
                                d.exact_expiry_date.timestamp())
                                 for d in ice_options_data_month_list])

            
        
                
# parse_options_csv(csv_file_path=__OPTIONS_FILE_PATH)


# def parse_futures_csv(csv_file_path: Path):
#     with open(csv_file_path, mode='r', encoding='utf-8') as file:
#         reader = csv.DictReader(file)
        
        
#         fieldnames: list[str] = list(reader.fieldnames) if reader.fieldnames is not None else []
#         fieldname_check= set(fieldnames).difference({'ts_event', 'rtype', 'publisher_id', 'instrument_id', 'open', 'high', 'low', 'close', 'volume', 'symbol'})
#         if len(fieldnames) == 0 or len(fieldname_check) != 0:
#             raise RuntimeError('Invalid fieldnames in the csv file')
        
#         for row in reader:
            
#             pattern = r'([A-Z\s]{5})([\d\s]{4})([\d]{8})'
            
#             symbol = row['symbol']
#             match = re.match(pattern=pattern, string= symbol) # 'TFO  22  31131494'
            
#             if match:
#                 print(symbol)
            
#             try:
#                 a = ICEFuturesData.decode_csv_row(row)
                
#                 # if isinstance(a, ICEFuturesData_Month):
#                 #     print(a)
#             except ValueError as e:  
                
#                 print('ERROR' + e.__str__() + symbol)


# parse_futures_csv(csv_file_path=__FUTURES_FILE_PATH)

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