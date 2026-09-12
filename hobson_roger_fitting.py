from dataclasses import dataclass
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import minimize
from files import MAIN_DB_FILE_PATH, MONTH_PUT_CALL_PARITY, FUTURES_PRICES



# ==============================================================================
# 1. HOBSON-ROGERS MATHEMATICAL & PRICING FUNCTIONS
# ==============================================================================

def compute_offset(log_prices: np.ndarray, dt: float, l: float) -> float:
    '''
    D_0 = Z_0 - l * integral_{-inf}^0 e^{l * s} Z_s ds
    '''
    
    n = len(log_prices)
    if n == 0:
        return 0.0
    
    # decay weights 
    weights: list[float] = np.exp(-l * np.arange(n - 1, -1, -1) * dt)
    weights = weights / np.sum(weights)
    
    ewma_z:float = np.sum(weights * log_prices)
    current_z = log_prices[-1]
    
    return float(current_z - ewma_z)


def hr_volatility_asymmetric(D: float | np.ndarray, eta: float, epsilon: float, gamma: float) -> float | np.ndarray:
    '''
    sigma(D) = sqrt(eta * (epsilon + (D - gamma)^2))
    '''
    a = eta * (epsilon + (D - gamma)**2)
    return np.sqrt(a)


def hobson_rogers_mc_price(
    S0: float, 
    K: float, 
    r: float, 
    T: float, 
    D0: float, 
    l: float, 
    eta: float, 
    epsilon: float, 
    gamma: float,
    option_type: str,
    n_sims: int = 3000, 
    n_steps: int = 30 
) -> float:
    """
    Prices European Option under Hobson-Rogers risk-neutral dynamics via Monte Carlo.
    """
    if T <= 0:
        return max(S0 - K, 0.0) if option_type.upper() == 'C' else max(K - S0, 0.0)

    dt = T / n_steps
    sqrt_dt = np.sqrt(dt)
    
    S = np.full(n_sims, S0)
    D = np.full(n_sims, D0)
    
    for _ in range(n_steps):
        vol = hr_volatility_asymmetric(D, eta, epsilon, gamma)
        dW = np.random.normal(0, 1, n_sims)
        
        # Stock process: dS / S = r dt + sigma(D) dW
        S = S * np.exp((r - 0.5 * vol**2) * dt + vol * sqrt_dt * dW)
        
        # Offset process: dD = (r - 0.5*sigma^2 - l * D) dt + sigma(D) dW
        D += (r - 0.5 * vol**2 - l * D) * dt + vol * sqrt_dt * dW

    payoff = np.maximum(S - K, 0) if option_type.upper() in ['C', 'CALL'] else np.maximum(K - S, 0)
    return float(np.exp(-r * T) * np.mean(payoff))




# ==============================================================================
# 3. MODEL CALIBRATION PIPELINE
# ==============================================================================

def objective_function(
    params: list, 
    df_options: pd.DataFrame, 
    log_prices_hist: np.ndarray, 
    dt_hist: float = 1/252
) -> float:
    """
    Sum of Squared Errors (SSE) across market options.
    """
    l, eta, epsilon, gamma = params
    
    # Strict boundary constraints
    if l <= 0 or eta <= 0 or epsilon <= 0:
        return 1_000_000_000.0
    

    D0 = compute_offset(log_prices_hist, dt_hist, l)
    total_sse = 0.0
    
    for _, row in df_options.iterrows():
        S0 = row['close_of_future']
        K = row['option_strike_price']
        r = row['euro_short_term_rate']
        T = row['time_to_expiry']
        
        # Target price: pick Call or Put price based on liquidity/volume
        opt_type = 'C'
        mkt_price = row.get('call_price', np.nan)
        
        if pd.isna(mkt_price) or (row.get('put_volume', 0) > row.get('call_volume', 0)):
            opt_type = 'P'
            mkt_price = row.get('put_price', np.nan)
            
        if pd.isna(mkt_price) or mkt_price <= 0:
            continue

        model_price = hobson_rogers_mc_price(
            S0=S0, K=K, r=r, T=T, D0=D0,
            l=l, eta=eta, epsilon=epsilon, gamma=gamma,
            option_type=opt_type, n_sims=1500, n_steps=20
        )
        
        total_sse += (model_price - mkt_price) ** 2
        
    return total_sse






# ==============================================================================
# 4. DATA LOADING & EXTRACTION FROM SQL QUERIES
# ==============================================================================
 



def load_data_from_db(
    db_path: Path, 
    options_sql_path: Path, 
    futures_sql_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(db_path)
    
    with open(options_sql_path, 'r', encoding='utf-8') as f:
        options_query = f.read()
        
    with open(futures_sql_path, 'r', encoding='utf-8') as f:
        futures_query = f.read()

    df_options_all = pd.read_sql_query(options_query, conn)
    df_futures_all = pd.read_sql_query(futures_query, conn)
    conn.close()
    
    return df_options_all, df_futures_all
    





# ==============================================================================
# 4. DATA LOADING & EXTRACTION FROM SQL QUERIES
# ==============================================================================

def filter_data(
    df_options_all: pd.DataFrame,
    df_futures_all: pd.DataFrame,
    futures_contract_code: str,
    option_contract_code: str,
    delivery_period: str,
    valuation_date: str,
) -> tuple[pd.DataFrame, np.ndarray]:

    # Filter options for specific valuation snapshot
    df_options = df_options_all[
        (df_options_all['contract_code'] == option_contract_code) &
        (df_options_all['contract_delivery_period'] == delivery_period) &
        (df_options_all['ts_event'] == valuation_date)
    ].copy()

    # Calculate Time-to-Expiry (T in years)
    df_options['ts_event'] = pd.to_datetime(df_options['ts_event'])
    df_options['option_expiry_date'] = pd.to_datetime(df_options['option_expiry_date'])
    df_options['time_to_expiry'] = (df_options['option_expiry_date'] - df_options['ts_event']).dt.days / 365.25

    # Determine most liquid option price and type per row
    def select_liquid_option(row):
        p_vol = row.get('put_volume', 0)
        c_vol = row.get('call_volume', 0)
        if c_vol > p_vol:
            return pd.Series({'market_price': row['call_price'], 'option_type': 'C'})
        elif p_vol > c_vol:
            return pd.Series({'market_price': row['put_price'], 'option_type': 'P'})
        elif c_vol > 0:
            return pd.Series({'market_price': row['call_price'], 'option_type': 'C'})
        else:
            return pd.Series({'market_price': np.nan, 'option_type': None})

    liquid_info = df_options.apply(select_liquid_option, axis=1)
    df_options['market_price'] = liquid_info['market_price']
    df_options['option_type'] = liquid_info['option_type']
    
    # Drop rows without valid option prices
    df_options = df_options.dropna(subset=['market_price', 'close_of_future', 'euro_short_term_rate']).copy()
    df_options = df_options[df_options['market_price'] > 0].copy()

    # Extract historical futures close path leading up to valuation date
    df_futures_hist = df_futures_all[
        (df_futures_all['contract_code'] == futures_contract_code) &
        (df_futures_all['contract_delivery_period'] == delivery_period) &
        (df_futures_all['ts_event'] < valuation_date)
    ].sort_values('ts_event').copy()

    # Convert rate percentage (e.g., 2.398%) to decimal (0.02398)
    r_avg = df_options['euro_short_term_rate'].mean() / 100.0 if df_options['euro_short_term_rate'].mean() > 0.5 else df_options['euro_short_term_rate'].mean()

    prices = df_futures_hist['close_of_future'].values
    n_days = len(prices)
    t_vec = np.linspace(0, n_days / 252.0, n_days)
    
    # Z_s = ln(e^{-r*s} * S_s)
    log_prices_hist = np.log(np.exp(-r_avg * t_vec) * prices)

    return df_options, log_prices_hist

def run_hobson_rogers_calibration(
    df_options_all: pd.DataFrame,
    df_futures_all: pd.DataFrame,
    )-> pd.DataFrame:
    """
    Executes data loading, calibration, and database export.
    """
    print("Loading data from SQLite queries...")
    df_options, log_prices_hist = filter_data(
        df_options_all=df_options_all, df_futures_all=df_futures_all, futures_contract_code='TFM',
        option_contract_code='TFO', delivery_period='2023-04', valuation_date='2023-03-20'
    )
    
    print(f"Loaded {len(df_options)} valid market option quotes across strikes.")
    print(f"Historical futures price sequence length: {len(log_prices_hist)} days.")

    # Optimization setup
    initial_guess = [2.0, 0.04, 0.01, -0.05]  # [lambda, eta, epsilon, gamma]
    bounds = [
        (0.01, 10.0),   # lambda > 0
        (0.001, 1.0),   # eta > 0
        (0.0001, 0.1),  # epsilon > 0
        (-0.5, 0.5)     # gamma (skew parameter)
    ]

    print("\nStarting Nelder-Mead Hobson-Rogers Model Calibration...")
    res = minimize(
        objective_function,
        x0=initial_guess,
        args=(df_options, log_prices_hist),
        method='Nelder-Mead',
        bounds=bounds,
        options={'maxiter': 200, 'disp': True}
    )

    opt_lambda, opt_eta, opt_epsilon, opt_gamma = res.x
    opt_D0 = compute_offset(log_prices_hist, 1/252, opt_lambda)

    print("\n==========================================")
    print("CALIBRATION SUCCESSFUL")
    print("==========================================")
    print(f"Optimal Lambda  (λ): {opt_lambda:.4f}")
    print(f"Optimal Eta     (η): {opt_eta:.4f}")
    print(f"Optimal Epsilon (ε): {opt_epsilon:.4f}")
    print(f"Optimal Gamma   (γ): {opt_gamma:.4f}")
    print(f"Initial Offset (D0): {opt_D0:.4f}")
    print("==========================================")

    # Compute fitted model prices
    print("\nComputing calibrated model prices...")
    df_options['hr_model_price'] = df_options.apply(
        lambda r: hobson_rogers_mc_price(
            S0=r['close_of_future'], K=r['option_strike_price'], 
            r=r['euro_short_term_rate'] / 100.0 if r['euro_short_term_rate'] > 0.5 else r['euro_short_term_rate'],
            T=r['time_to_expiry'], D0=opt_D0,
            l=opt_lambda, eta=opt_eta, epsilon=opt_epsilon, gamma=opt_gamma,
            option_type=r['option_type']
        ),
        axis=1
    )

    return df_options



if __name__ == "__main__":
    
    if MAIN_DB_FILE_PATH.exists() and MONTH_PUT_CALL_PARITY.exists() and FUTURES_PRICES.exists():
         
        df_options_all, df_futures_all = load_data_from_db(  db_path= MAIN_DB_FILE_PATH, 
                            options_sql_path= MONTH_PUT_CALL_PARITY, 
                            futures_sql_path= FUTURES_PRICES
                            )
        
        df_options= run_hobson_rogers_calibration(  
                                                    df_options_all=df_options_all,
                                                    df_futures_all= df_futures_all,)
    
        output_table_name: str = "hobson_rogers_calibrated_prices"
    
        # Export calibrated results back to SQLite database
        conn = sqlite3.connect(MAIN_DB_FILE_PATH)
        df_options.to_sql(output_table_name, conn, if_exists='replace', index=False)
        conn.close()
        print(f"Results successfully saved to SQLite table '{output_table_name}'.")

    else:
        raise FileNotFoundError('File path not found')
