# read the "TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv", create a db, and using the data_decode.py store the data that are mapped successfully in one table in  DB.the data that they produce an error in ICEOptionData store them  

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from options_data_decode import (ICEOptionsData_QSY, ICEOptionsData_Unencoded_QSY_TruncationIssue, ICEOptionsData_Unencoded_Unknown, ICEOptionsDataUnion, ICEOptionsDataABC, ICEOptionsData_Month, ICEOptionsData_Undencoded_Month, ICEOptionsData_Unencoded_RecordsWithId)
from sqlite3_helper.table_management import DbDatatype, DbField, DbTableMixin, TableTemplateEnum
from sqlite3_helper.sqlite3_helper import create_database_pass_if_exists, dynamic_database_connection_closer, Sqlite3ConnectionProvider

from files import MAIN_DB_FILE_PATH, OPTIONS_FILE_PATH

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Create database
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

create_database_pass_if_exists(db_filepath=MAIN_DB_FILE_PATH)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Table definition
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
class ICEOptionsDataMonthTable(DbTableMixin, TableTemplateEnum):
    
    # The event timestamp as the number of nanoseconds since the UNIX epoch.
    ts_event = DbField(datatype=DbDatatype.DATETIME_TEXT, is_pk=True)

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
    volume = DbField(datatype=DbDatatype.INT)
    
    contract_code = DbField(datatype=DbDatatype.TEXT)
    contract_type = DbField(datatype=DbDatatype.TEXT)
    contract_term = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period = DbField(datatype=DbDatatype.TEXT)
    
    option_term = DbField(datatype=DbDatatype.TEXT)
    option_payoff_style = DbField(datatype=DbDatatype.TEXT)
    option_exercise_style = DbField(datatype=DbDatatype.TEXT)
    option_strike_decimals = DbField(datatype=DbDatatype.INT)
    option_strike_price = DbField(datatype=DbDatatype.REAL)
    option_expiry_date = DbField(datatype=DbDatatype.DATETIME_TEXT)

    @classmethod
    def get_table_name(cls) -> str:
        return 'ice_options_data_month'
    
    @classmethod
    def get_row_data(cls, *args: Any, **kwargs: Any) -> dict[Any, Any]:
        return {}
    
class ICEOptionsDataQSYTable(DbTableMixin, TableTemplateEnum):
    
    # The event timestamp as the number of nanoseconds since the UNIX epoch.
    ts_event = DbField(datatype=DbDatatype.DATETIME_TEXT, is_pk=True)

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
    volume = DbField(datatype=DbDatatype.INT)
    
    contract_code = DbField(datatype=DbDatatype.TEXT)
    contract_type = DbField(datatype=DbDatatype.TEXT)
    contract_term = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period_from = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period_to = DbField(datatype=DbDatatype.TEXT)
    
    option_term = DbField(datatype=DbDatatype.TEXT)
    option_payoff_style = DbField(datatype=DbDatatype.TEXT)
    option_exercise_style = DbField(datatype=DbDatatype.TEXT)
    option_strike_decimals = DbField(datatype=DbDatatype.INT)
    option_strike_price = DbField(datatype=DbDatatype.REAL)
    option_expiry_date = DbField(datatype=DbDatatype.DATETIME_TEXT)

    @classmethod
    def get_table_name(cls) -> str:
        return 'ice_options_data_qsy'
    
    @classmethod
    def get_row_data(cls, *args: Any, **kwargs: Any) -> dict[Any, Any]:
        return {}

    
class ICEOptionsDataQSYTruncationIssueTable(DbTableMixin, TableTemplateEnum):
    
    # The event timestamp as the number of nanoseconds since the UNIX epoch.
    ts_event = DbField(datatype=DbDatatype.DATETIME_TEXT, is_pk=True)

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
    volume = DbField(datatype=DbDatatype.INT)
    
    contract_code = DbField(datatype=DbDatatype.TEXT)
    contract_type = DbField(datatype=DbDatatype.TEXT)
    contract_term = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period_from = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period_to = DbField(datatype=DbDatatype.TEXT)
    
    option_term = DbField(datatype=DbDatatype.TEXT)
    option_payoff_style = DbField(datatype=DbDatatype.TEXT)
    option_exercise_style = DbField(datatype=DbDatatype.TEXT)
    option_strike_decimals = DbField(datatype=DbDatatype.INT)
    option_strike_price = DbField(datatype=DbDatatype.REAL)
    # option_expiry_date = DbField(datatype=DbDatatype.DATETIME_TEXT)

    @classmethod
    def get_table_name(cls) -> str:
        return 'ice_options_data_qsy_truncation_issue'
    
    @classmethod
    def get_row_data(cls, *args: Any, **kwargs: Any) -> dict[Any, Any]:
        return {}

    

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Create table
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

init_sql=f'''{ICEOptionsDataMonthTable.get_create_table_sql(ICEOptionsDataMonthTable)}

{ICEOptionsDataQSYTable.get_create_table_sql(ICEOptionsDataQSYTable)}

{ICEOptionsDataQSYTruncationIssueTable.get_create_table_sql(ICEOptionsDataQSYTruncationIssueTable)}
'''
@dynamic_database_connection_closer
def create_table(sqlite3_connection_provider: Sqlite3ConnectionProvider):
    with sqlite3_connection_provider.connection as conn:
        conn.executescript(init_sql)


sqlite3_connection_provider = Sqlite3ConnectionProvider(db_path=MAIN_DB_FILE_PATH)
create_table(sqlite3_connection_provider=sqlite3_connection_provider)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Parse csv and import to db
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

@dataclass
class parse_options_csv_res:
    ice_options_data_month_list: list[ICEOptionsData_Month]
    ice_options_data_undecoded_month_list: list[ICEOptionsData_Undencoded_Month]
    ice_options_data_qsy_list: list[ICEOptionsData_QSY]
    ice_options_data_undecoded_truncation_issue: list[ICEOptionsData_Unencoded_QSY_TruncationIssue]
    ice_options_data_undecoded_unknown_list: list[ICEOptionsData_Unencoded_Unknown]
    

def parse_options_csv(csv_file_path: Path)-> parse_options_csv_res:
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        fieldnames: list[str] = list(reader.fieldnames) if reader.fieldnames is not None else []
        fieldname_check= set(fieldnames).difference({'ts_event', 'rtype', 'publisher_id', 'instrument_id', 'open', 'high', 'low', 'close', 'volume', 'symbol'})
        if len(fieldnames) == 0 or len(fieldname_check) != 0:
            raise RuntimeError('Invalid fieldnames in the csv file')
        
        ice_options_data_month_list: list[ICEOptionsData_Month] =[]
        ice_options_data_undecoded_month_list: list[ICEOptionsData_Undencoded_Month] =[]
        ice_options_data_qsy_list: list[ICEOptionsData_QSY] =[]
        ice_options_data_undecoded_truncation_issue: list[ICEOptionsData_Unencoded_QSY_TruncationIssue] =[]
        ice_options_data_undecoded_unknown_list: list[ICEOptionsData_Unencoded_Unknown] =[]
        
        for row in reader:    
            row_decoded:ICEOptionsDataUnion = ICEOptionsDataABC.decode_csv_row(row)
            
            match row_decoded:
                case ICEOptionsData_Month():
                    ice_options_data_month_list.append(row_decoded)
                
                case ICEOptionsData_Undencoded_Month():
                    ice_options_data_undecoded_month_list.append(row_decoded)
                
                case ICEOptionsData_QSY():
                    ice_options_data_qsy_list.append(row_decoded)
                    
                case ICEOptionsData_Unencoded_RecordsWithId():
                    pass
                
                case ICEOptionsData_Unencoded_QSY_TruncationIssue():
                    ice_options_data_undecoded_truncation_issue.append(row_decoded)
                    
                case ICEOptionsData_Unencoded_Unknown():
                    ice_options_data_undecoded_unknown_list.append(row_decoded)
                    
        return parse_options_csv_res(ice_options_data_month_list=ice_options_data_month_list,
                                     ice_options_data_undecoded_month_list=ice_options_data_undecoded_month_list,
                                     ice_options_data_qsy_list=ice_options_data_qsy_list,
                                     ice_options_data_undecoded_truncation_issue=ice_options_data_undecoded_truncation_issue,
                                     ice_options_data_undecoded_unknown_list=ice_options_data_undecoded_unknown_list)
    
    
res = parse_options_csv(csv_file_path=OPTIONS_FILE_PATH)

def upload_data_to_db(ice_options_data_month_list: list[ICEOptionsData_Month], 
                      ice_options_data_qsy_list: list[ICEOptionsData_QSY], 
                      ice_options_data_qsy_truncation_issue_list: list[ICEOptionsData_Unencoded_QSY_TruncationIssue]):
        with Sqlite3ConnectionProvider(db_path=MAIN_DB_FILE_PATH).connection as conn:
            query = '''
                INSERT INTO ice_options_data_month (
                    ts_event,
                    publisher_id,
                    instrument_id,
                    symbol,
                    rtype,
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
                    option_strike_decimals,
                    option_strike_price,
                    option_expiry_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            conn.executemany(query,
                              [(d.ts_event.strftime('%Y-%m-%d'), d.publisher_id,
                                d.instrument_id, d.symbol, d.rtype, d.open, d.high,
                                d.low, d.close, d.volume,
                                d.contract_code, d.contract_type.code, d.contract_term.code,
                                d.contract_delivery_period.__str__(), d.option_term.code, d.option_payoff_style.code,
                                d.option_exercise_style.code, d.option_strike_decimals, d.option_strike_price,
                                d.option_expiry_date.strftime('%Y-%m-%d'))
                                 for d in ice_options_data_month_list])

            query = '''
                INSERT INTO ice_options_data_qsy (
                    ts_event,
                    publisher_id,
                    instrument_id,
                    symbol,
                    rtype,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    contract_code,
                    contract_type,
                    contract_term,
                    contract_delivery_period_from,
                    contract_delivery_period_to,
                    option_term,
                    option_payoff_style,
                    option_exercise_style,
                    option_strike_decimals,
                    option_strike_price,
                    option_expiry_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            conn.executemany(query,
                              [(d.ts_event.strftime('%Y-%m-%d'), d.publisher_id,
                                d.instrument_id, d.symbol, d.rtype, d.open, d.high,
                                d.low, d.close, d.volume,
                                d.contract_code, d.contract_type.code, d.contract_term.code,
                                d.contract_delivery_period_from.__str__(), d.contract_delivery_period_to.__str__(),
                                d.option_term.code, d.option_payoff_style.code,
                                d.option_exercise_style.code, d.strike_decimals, d.strike_price,
                                d.option_expiry_date.strftime('%Y-%m-%d'))
                                 for d in ice_options_data_qsy_list])

            query = '''
                INSERT INTO ice_options_data_qsy_truncation_issue (
                    ts_event,
                    publisher_id,
                    instrument_id,
                    symbol,
                    rtype,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    contract_code,
                    contract_type,
                    contract_term,
                    contract_delivery_period_from,
                    contract_delivery_period_to,
                    option_term,
                    option_payoff_style,
                    option_exercise_style,
                    option_strike_decimals,
                    option_strike_price --,
                    -- option_expiry_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            conn.executemany(query,
                              [(d.ts_event.strftime('%Y-%m-%d'), d.publisher_id,
                                d.instrument_id, d.symbol, d.rtype, d.open, d.high,
                                d.low, d.close, d.volume,
                                d.contract_code, d.contract_type.code, d.contract_term.code,
                                d.contract_delivery_period_from.__str__(), d.contract_delivery_period_to.__str__(),
                                d.option_term.code, d.option_payoff_style.code,
                                d.option_exercise_style.code, d.strike_decimals, d.strike_price,
                                # d.option_expiry_date.strftime('%Y-%m-%d')
                                )
                                 for d in ice_options_data_qsy_truncation_issue_list])


upload_data_to_db(ice_options_data_month_list=res.ice_options_data_month_list,
                  ice_options_data_qsy_list=res.ice_options_data_qsy_list, 
                  ice_options_data_qsy_truncation_issue_list=res.ice_options_data_undecoded_truncation_issue)


if len(res.ice_options_data_undecoded_unknown_list) >0:
    raise ValueError('Undecoded unknown list is not empty')