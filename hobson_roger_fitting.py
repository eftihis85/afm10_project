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
        raise ImportError('Non zero')
    
    # Exponential decay weights over past time steps
    weights = np.exp(-l * np.arange(n - 1, -1, -1) * dt)
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
    n_sims: int, 
    n_steps: int 
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
# 2. AFM10 DATA EXTRACTION & PREPARATION
# ==============================================================================

def load_afm10_data(db_path: Path, sql_query: str) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Extracts options dataset and constructs historical discounted log-prices Z_s.
    """
    conn = sqlite3.connect(db_path)
    
    # 1. Load options data from SQLite
    df_options = pd.read_sql_query(sql_query, conn)
    
    # Clean and filter valid rows
    df_options = df_options.dropna(subset=['close_of_future', 'option_strike_price', 'euro_short_term_rate']).copy()
    
    # Calculate time to expiry T (years) if expiry date is available
    if 'option_expiry_date' in df_options.columns and 'ts_event' in df_options.columns:
        df_options['ts_event'] = pd.to_datetime(df_options['ts_event'])
        df_options['option_expiry_date'] = pd.to_datetime(df_options['option_expiry_date'])
        df_options['time_to_expiry'] = (df_options['option_expiry_date'] - df_options['ts_event']).dt.days / 365.25
    
    df_options = df_options[df_options['time_to_expiry'] > 0.01].copy()

    # 2. Construct historical discounted log-prices vector Z_s for underlying futures
    # Extract historical close series ordered by event timestamp
    hist_futures = df_options[['ts_event', 'close_of_future', 'euro_short_term_rate']].drop_duplicates()
    hist_futures = hist_futures.sort_values('ts_event')
    
    r_avg = hist_futures['euro_short_term_rate'].mean()
    if pd.isna(r_avg):
        r_avg = 0.03
        
    prices = hist_futures['close_of_future'].values
    t_steps = np.linspace(0, len(prices) / 252.0, len(prices))
    
    # Z_s = ln(e^{-r*s} * S_s)
    log_prices_hist = np.log(np.exp(-r_avg * t_steps) * prices)
    
    conn.close()
    return df_options, log_prices_hist


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



def run_hobson_rogers_pipeline(
    db_path: Path, 
    options_sql_path: Path, 
    futures_sql_path: Path,
    output_table_name: str = "hobson_rogers_calibrated_prices"
):
    """
    Executes data loading, calibration, and database export.
    """
    print("Loading data from SQLite queries...")
    df_options, log_prices_hist = load_data_from_db(
        db_path, options_sql_path, futures_sql_path,
        contract_code='TFO', delivery_period='2023-04', valuation_date='2023-03-20'
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
            lmbda=opt_lambda, eta=opt_eta, epsilon=opt_epsilon, gamma=opt_gamma,
            option_type=r['option_type']
        ),
        axis=1
    )

    # Export calibrated results back to SQLite database
    conn = sqlite3.connect(db_path)
    df_options.to_sql(output_table_name, conn, if_exists='replace', index=False)
    conn.close()
    print(f"Results successfully saved to SQLite table '{output_table_name}'.")


if __name__ == "__main__":
    
    if MAIN_DB_FILE_PATH.exists() and MONTH_PUT_CALL_PARITY.exists() and FUTURES_PRICES.exists():
        run_hobson_rogers_pipeline(MAIN_DB_FILE_PATH, MONTH_PUT_CALL_PARITY, FUTURES_PRICES)
    else:
        raise FileNotFoundError('File path not found')
