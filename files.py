from pathlib import Path
from typing import Final

EUR_SHORT_TERM_RATE_FILE_PATH:Final = Path(__file__).resolve().parent / 'data' / 'ECB Data Portal_20260607232031.csv' 
OPTIONS_FILE_PATH:Final = Path(__file__).resolve().parent / 'data' / 'TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv' 
FUTURES_FILE_PATH:Final = Path(__file__).resolve().parent / 'data' / 'TFM · Dutch TTF Natural Gas Futures - ohlcv-1d - 2021-01-01 00:00 2026-05-21 00:00.csv' 
MAIN_DB_FILE_PATH:Final = Path(__file__).resolve().parent / 'data' / 'database.db' 

MONTH_PUT_CALL_PARITY:Final =  Path(__file__).resolve().parent / 'data' / 'queries' / 'monthly_put_call_pivot.sql'
MONTH_PUT_CALL_IV_RESULTS:Final =  Path(__file__).resolve().parent / 'data' / 'queries' / 'monthly_put_call_iv_results.sql'
MONTH_PUT_CALL_SVI_RESULTS:Final =  Path(__file__).resolve().parent / 'data' / 'queries' / 'monthly_put_call_svi_results.sql'
MONTH_PUT_CALL_SSVI_RESULTS:Final =  Path(__file__).resolve().parent / 'data' / 'queries' / 'monthly_put_call_ssvi_results.sql'
MONTH_PUT_CALL_SSVI_DENSE_GRID:Final =  Path(__file__).resolve().parent / 'data' / 'queries' / 'monthly_put_call_ssvi_dense_grid.sql'

EXPORTS_PATH:Final =  Path(__file__).resolve().parent / 'exports'