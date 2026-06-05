from pathlib import Path
from typing import Final

DATA_FOLDER:Final = 'data'
OPTIONS_FILE_NAME:Final  = 'TFO · Dutch TTF Natural Gas Options - ohlcv-1d - 2026-04-20 00:00 2026-05-20 16:00.csv'
FUTURES_FILE_NAME:Final  = 'TFM · Dutch TTF Natural Gas Futures - ohlcv-1d - 2021-01-01 00:00 2026-05-21 00:00.csv'
MAIN_DB_FILENAME:Final = 'database.db'
OPTIONS_FILE_PATH:Final = Path(__file__).resolve().parent / DATA_FOLDER / OPTIONS_FILE_NAME 
FUTURES_FILE_PATH:Final = Path(__file__).resolve().parent / DATA_FOLDER / FUTURES_FILE_NAME 
MAIN_DB_FILE_PATH:Final = Path(__file__).resolve().parent / DATA_FOLDER / MAIN_DB_FILENAME 
