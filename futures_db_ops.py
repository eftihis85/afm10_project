import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from sqlite3_helper.table_management import DbDatatype, DbField, DbTableMixin, TableTemplateEnum
from sqlite3_helper.sqlite3_helper import create_database_pass_if_exists, dynamic_database_connection_closer, Sqlite3ConnectionProvider

from files import MAIN_DB_FILE_PATH, FUTURES_FILE_PATH
from futures_data_decode import ICEFuturesData_Month, ICEFuturesData_Month_TAS, ICEFuturesData_Unencoded_MonthSpread_TAS, ICEFuturesData_Unencoded_recordWithId, ICEFuturesDataUnion, ICEFuturesDataABC, ICEFuturesData_Unencoded, ICEFuturesData_QSY, ICEFuturesData_Spread_Month, ICEFuturesData_Spread_QSY

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Create database
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

create_database_pass_if_exists(db_filepath=MAIN_DB_FILE_PATH)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Table definition
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class ICEFuturesDataMonthTable(DbTableMixin, TableTemplateEnum):
    
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
    
    contract_code = DbField(datatype=DbDatatype.TEXT)
    contract_type = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_term = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period = DbField(datatype=DbDatatype.TEXT)
    
    open = DbField(datatype=DbDatatype.REAL)
    high = DbField(datatype=DbDatatype.REAL)
    low = DbField(datatype=DbDatatype.REAL)
    close = DbField(datatype=DbDatatype.REAL)
    volume = DbField(datatype=DbDatatype.INT)

    @classmethod
    def get_table_name(cls) -> str:
        return 'ice_futures_data_month'
    
    @classmethod
    def get_row_data(cls, *args: Any, **kwargs: Any) -> dict[Any, Any]:
        return {}
    
class ICEFuturesDataMonthTASTable(DbTableMixin, TableTemplateEnum):
    
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
    
    contract_code = DbField(datatype=DbDatatype.TEXT)
    contract_type = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_term = DbField(datatype=DbDatatype.TEXT)
    contract_delivery_period = DbField(datatype=DbDatatype.TEXT)
    
    open = DbField(datatype=DbDatatype.REAL)
    high = DbField(datatype=DbDatatype.REAL)
    low = DbField(datatype=DbDatatype.REAL)
    close = DbField(datatype=DbDatatype.REAL)
    volume = DbField(datatype=DbDatatype.INT)

    @classmethod
    def get_table_name(cls) -> str:
        return 'ice_futures_data_month_tas'
    
    @classmethod
    def get_row_data(cls, *args: Any, **kwargs: Any) -> dict[Any, Any]:
        return {}
    
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Create table
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

@dynamic_database_connection_closer
def create_table(sqlite3_connection_provider: Sqlite3ConnectionProvider):
    init_sql=   (
                    f'{ICEFuturesDataMonthTable.get_create_table_sql(ICEFuturesDataMonthTable)}'
                    '\n\n'
                    f'{ICEFuturesDataMonthTASTable.get_create_table_sql(ICEFuturesDataMonthTASTable)}'
                )
    
    print(init_sql)
    
    with sqlite3_connection_provider.connection as conn:
        conn.executescript(init_sql)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Parse csv and import to db
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
 
@dataclass
class ParseFuturesCSVRes:
    ice_futures_data_month_list: list[ICEFuturesData_Month]
    ice_futures_data_month_tas_list: list[ICEFuturesData_Month_TAS]
    ice_futures_data_month_spread_list: list[ICEFuturesData_Spread_Month]
    ice_futures_data_qsy_list: list[ICEFuturesData_QSY]
    ice_futures_data_qsy_spread_list: list[ICEFuturesData_Spread_QSY]
    ice_futures_data_undecoded_list: list[ICEFuturesData_Unencoded]
    ice_futures_data_undecoded_month_spread_tas_list: list[ICEFuturesData_Unencoded_MonthSpread_TAS]
    ice_futures_data_undecoded_record_with_id_list: list[ICEFuturesData_Unencoded_recordWithId]
    
def parse_futures_csv(csv_file_path: Path)-> ParseFuturesCSVRes:
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        fieldnames: list[str] = list(reader.fieldnames) if reader.fieldnames is not None else []
        fieldname_check= set(fieldnames).difference({'ts_event', 'rtype', 'publisher_id', 'instrument_id', 'open', 'high', 'low', 'close', 'volume', 'symbol'})
        if len(fieldnames) == 0 or len(fieldname_check) != 0:
            raise RuntimeError('Invalid fieldnames in the csv file')
        
        res = ParseFuturesCSVRes(   ice_futures_data_month_list=[],
                                    ice_futures_data_month_tas_list = [],
                                     ice_futures_data_month_spread_list=[],
                                     ice_futures_data_qsy_list=[],
                                     ice_futures_data_qsy_spread_list=[],
                                     ice_futures_data_undecoded_list=[], 
                                     ice_futures_data_undecoded_month_spread_tas_list=[], 
                                     ice_futures_data_undecoded_record_with_id_list=[])
        
        
        for row in reader:    
            row_decoded:ICEFuturesDataABC = ICEFuturesDataABC.decode_csv_row(row)
            
            match row_decoded:
                case ICEFuturesData_Month():
                    res.ice_futures_data_month_list.append(row_decoded)
                    
                case ICEFuturesData_Month_TAS():
                    res.ice_futures_data_month_tas_list.append(row_decoded)
                
                case ICEFuturesData_QSY():
                    res.ice_futures_data_qsy_list.append(row_decoded)
                
                case ICEFuturesData_Spread_Month():
                    res.ice_futures_data_month_spread_list.append(row_decoded)
                    
                case ICEFuturesData_Spread_QSY():
                    res.ice_futures_data_qsy_spread_list.append(row_decoded)
                    
                case ICEFuturesData_Unencoded():
                    res.ice_futures_data_undecoded_list.append(row_decoded)
                
                case ICEFuturesData_Unencoded_MonthSpread_TAS():
                    res.ice_futures_data_undecoded_month_spread_tas_list.append(row_decoded)
                            
                case ICEFuturesData_Unencoded_recordWithId():
                    res.ice_futures_data_undecoded_record_with_id_list.append(row_decoded)
                    
        return res
    
    

def upload_data_to_db(parse_futures_csv_res: ParseFuturesCSVRes):
        with Sqlite3ConnectionProvider(db_path=MAIN_DB_FILE_PATH).connection as conn:
            query = '''
                DELETE FROM ice_futures_data_month
            '''
            conn.execute(query)
            
            query = '''
                DELETE FROM ice_futures_data_month_tas
            '''
            conn.execute(query)
            
            query = '''
                INSERT INTO ice_futures_data_month (
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
                    contract_delivery_term,
                    contract_delivery_period
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            conn.executemany(query,
                              [(d.ts_event.strftime('%Y-%m-%d'), d.publisher_id,
                                d.instrument_id, d.symbol, d.rtype, d.open, d.high,
                                d.low, d.close, d.volume,
                                d.contract_code, d.contract_type.code, d.contract_delivery_term.code,
                                d.contract_delivery_period.__str__())
                                 for d in parse_futures_csv_res.ice_futures_data_month_list])

            query = '''
                INSERT INTO ice_futures_data_month_tas (
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
                    contract_delivery_term,
                    contract_delivery_period
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            conn.executemany(query,
                              [(d.ts_event.strftime('%Y-%m-%d'), d.publisher_id,
                                d.instrument_id, d.symbol, d.rtype, d.open, d.high,
                                d.low, d.close, d.volume,
                                d.contract_code, d.contract_type.code, d.contract_delivery_term.code,
                                d.contract_delivery_period.__str__())
                                 for d in parse_futures_csv_res.ice_futures_data_month_tas_list])




sqlite3_connection_provider = Sqlite3ConnectionProvider(db_path=MAIN_DB_FILE_PATH)
create_table(sqlite3_connection_provider=sqlite3_connection_provider)

res = parse_futures_csv(csv_file_path=FUTURES_FILE_PATH)

upload_data_to_db(parse_futures_csv_res=res)

if len(res.ice_futures_data_undecoded_list) >0:
    for d in res.ice_futures_data_undecoded_list:
        print(d.symbol)
    raise ValueError('Undecoded unknown list is not empty')
