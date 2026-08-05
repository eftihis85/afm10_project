from datetime import datetime
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
from files import MAIN_DB_FILE_PATH, MONTH_PUT_CALL_PARITY




# ----------------------------------------------------------------------
# 1. Black-Scholes & Implied Volatility Functions
# ----------------------------------------------------------------------
def black_scholes_price(S:float, K:float, r:float, T:float, sigma, option_type='C'):
    """
    Calculates Black-Scholes European option price.
    For futures options, standard Black-76 or Black-Scholes is used.
    Here using Black-Scholes formula.
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == 'C':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == 'P':
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    else:
        raise ValueError("option_type must be 'C' or 'P'")

    return price


def calculate_iv(market_price, S, K, r, T, option_type):
    """
    Computes Implied Volatility via Brent's root-finding method.
    Returns None if calculation fails or market price violates arbitrage bounds.
    """
    if (
        pd.isna(market_price)
        or pd.isna(S)
        or pd.isna(K)
        or pd.isna(r)
        or pd.isna(T)
    ):
        return None

    if market_price <= 0 or T <= 0 or S <= 0 or K <= 0:
        return None

    # Objective function f(sigma) = BS_Price(sigma) - Market_Price
    def objective(sigma):
        return (
            black_scholes_price(S, K, r, T, sigma, option_type) - market_price
        )

    try:
        # Solve for sigma within reasonable bounds [0.0001, 5.0] (0.01% to 500% IV)
        iv = brentq(objective, a=0.0001, b=5.0, xtol=1e-5)
        return float(iv)
    except (ValueError, RuntimeError):
        return None


def calculate_time_to_expiry(ts_event, expiry_date_str):
    """Calculates time to expiry (T) in year fraction."""
    try:
        start_dt = pd.to_datetime(ts_event)
        end_dt = pd.to_datetime(expiry_date_str)
        days = (end_dt - start_dt).days
        return max(days / 365.25, 0.00001)  # Ensure non-zero positive fraction
    except Exception:
        return None


# ----------------------------------------------------------------------
# 2. Row Selection Logic & Main Execution Pipeline
# ----------------------------------------------------------------------
def process_options_data(db_path: Path, sql_file_path: Path) -> pd.DataFrame:
    # Read SQL query from file
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        query = f.read()

    # Execute query and load into DataFrame
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn)

    selected_options = []
    implied_vols = []

    # Process each row
    for _, row in df.iterrows():
        put_vol = row.get('put_volume', 0) or 0
        call_vol = row.get('call_volume', 0) or 0

        # Step 1: Liquidity Selection Rule
        if put_vol == 0 and call_vol == 0:
            selected = None
        elif put_vol > 0 and call_vol > 0 and put_vol == call_vol:
            selected = 'PC'
        elif put_vol > call_vol:
            selected = 'P'
        elif call_vol > put_vol:
            selected = 'C'
        else:
            selected = None

        # Step 2: Compute Implied Volatility based on selected option
        if selected in ['P', 'C']:
            # Extract required Black-Scholes variables
            S = row.get('close_of_future')
            K = row.get('option_strike_price')
            r_raw = row.get('euro_short_term_rate', 0.0) or 0.0
            r = r_raw / 100.0 if r_raw > 1.0 else r_raw  # Normalize rate

            T = calculate_time_to_expiry(
                row.get('ts_event'), row.get('option_expiry_date')
            )
            market_price = (
                row.get('put_price') if selected == 'P' else row.get('call_price')
            )

            iv = calculate_iv(
                market_price=market_price,
                S=S,
                K=K,
                r=r,
                T=T,
                option_type=selected,
            )
        else:
            iv = None  # None maps directly to SQL NULL / Pandas NaN

        selected_options.append(selected)
        implied_vols.append(iv)

    # Attach results to the DataFrame
    df['selected_option'] = selected_options
    df['implied_volatility'] = implied_vols

    return df


# ----------------------------------------------------------------------
# 3. Execution Script
# ----------------------------------------------------------------------
if __name__ == '__main__':

    # Run pipeline
    result_df = process_options_data(MAIN_DB_FILE_PATH, MONTH_PUT_CALL_PARITY)

    # Export result to SQLite database or CSV
    with sqlite3.connect(MAIN_DB_FILE_PATH) as conn:
        result_df.to_sql(
            'monthly_put_call_iv_results',
            conn,
            if_exists='replace',
            index=False,
        )

    print("Pipeline completed successfully! Augmented dataset saved.")