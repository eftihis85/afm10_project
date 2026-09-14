from datetime import date
import math
import sqlite3
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq, minimize
import matplotlib.pyplot as plt
from files import MAIN_DB_FILE_PATH

# ==============================================================================
# 1. Black-Scholes Pricing, Vega & Implied Volatility Inversion
# ==============================================================================
def bs_price(S: float, K: float, r: float, T: float, sigma: float, option_type: str) -> float:
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0) if option_type == 'C' else max(K - S, 0.0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'C':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def derive_implied_volatility_bs(price: float, S: float, K: float, r: float, T: float, option_type: str = 'C') -> float:
    if T <= 0 or price <= 0:
        return np.nan
    df = np.exp(-r * T)
    intrinsic = max(S - K * df, 0.0) if option_type == 'C' else max(K * df - S, 0.0)
    if price <= intrinsic:
        return np.nan
    try:
        return brentq(
            lambda sig: bs_price(S, K, r, T, sig, option_type) - price,
            1e-4, 5.0, xtol=1e-6
        )
    except (ValueError, RuntimeError):
        return np.nan

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

# ==============================================================================
# 2. Hobson-Rogers Monte Carlo Engine
# ==============================================================================
# def hobson_rogers_mc_grid(S0: float, y0: float, strikes: np.ndarray, r: float, T: float,
#                           sigma0: float, epsilon: float, lmbda: float,
#                           n_sims: int = 10_000, n_steps: int = 1_00, C: int = 2):
    
#     dt = T / n_steps
#     sqrt_dt = np.sqrt(dt)

#     # Antithetic variates for variance reduction
#     half_sims = math.floor (n_sims / 2)
#     dW_half = np.random.normal(0.0, sqrt_dt, size=(n_steps, half_sims))
#     dW = np.hstack([dW_half, -dW_half])

#     S = np.full(n_sims, S0, dtype=np.float64)
#     Y = np.full(n_sims, y0, dtype=np.float64)

#     for step in range(n_steps):
#         dw = dW[step]
        
#         # $\sigma(y) = \sigma_0 \sqrt{1 + \varepsilon y^2} \wedge C$
        
        
#         vol_Y = sigma0 * np.sqrt(1.0 + epsilon * (Y**2))
#         vol_Y = np.minimum(vol_Y, C)

        
#         # Coupled update with single Brownian driver
#         S += r * S * dt + vol_Y * S * dw
#         Y += -(0.5 * (vol_Y**2) + lmbda * Y) * dt + vol_Y * dw

#     call_prices = np.array([np.exp(-r * T) * np.mean(np.maximum(S - k, 0.0)) for k in strikes])
#     put_prices = np.array([np.exp(-r * T) * np.mean(np.maximum(k - S, 0.0)) for k in strikes])
#     return call_prices, put_prices

def hobson_rogers_mc_grid(S0: float, y0: float, strikes: np.ndarray, r: float, T: float,
                          sigma0: float, epsilon: float, lmbda: float, gamma: float,
                          n_sims: int = 10_000, n_steps: int = 60, C: float = 5.0):
    dt = T / n_steps
    sqrt_dt = np.sqrt(dt)

    half_sims = n_sims // 2
    dW_half = np.random.normal(0.0, sqrt_dt, size=(n_steps, half_sims))
    dW = np.hstack([dW_half, -dW_half])

    S = np.full(n_sims, S0, dtype=np.float64)
    Y = np.full(n_sims, y0, dtype=np.float64)

    for step in range(n_steps):
        dw = dW[step]
        
        # Numerical safeguard against extreme drift
        Y = np.clip(Y, -5.0, 5.0)
        
        # Asymmetric volatility specification: sigma0 * sqrt(1 + eps * (Y - gamma)^2) ^ C
        vol_Y = sigma0 * np.sqrt(1.0 + epsilon * ((Y - gamma)**2))
        vol_Y = np.minimum(vol_Y, C)
        
        # Coupled update with single Brownian motion
        S += r * S * dt + vol_Y * S * dw
        Y += -(0.5 * (vol_Y**2) + lmbda * Y) * dt + vol_Y * dw

        S = np.maximum(S, 1e-6)

    df = np.exp(-r * T)
    call_prices = np.array([df * np.mean(np.maximum(S - k, 0.0)) for k in strikes])
    put_prices = np.array([df * np.mean(np.maximum(k - S, 0.0)) for k in strikes])
    return call_prices, put_prices

# ==============================================================================
# Task (1): Pure Simulation Study
# ==============================================================================
def run_theoretical_simulation():
    S0 = 100.0
    y0 = 0.05
    r = 0.02
    T = 0.5  # 6 months
    sigma0 = 0.20
    eps = 0.8
    lmbda = 2.0
    strikes = np.linspace(start=75.0,stop= 125.0,num= 21)

    # (ii) HR Monte Carlo Prices
    hr_calls, hr_puts = hobson_rogers_mc_grid(S0, y0, strikes, r, T, sigma0, eps, lmbda)

    # (iii) Implied Volatilities for HR Call prices
    hr_ivs = [derive_implied_volatility_bs(p, S0, k, r, T, 'C') for p, k in zip(hr_calls, strikes)]

    # (iv) Black-Scholes Comparison (Flat sigma0 benchmark)
    bs_calls = [bs_price(S0, k, r, T, sigma0, 'C') for k in strikes]
    bs_ivs = [derive_implied_volatility_bs(p, S0, k, r, T, 'C') for p, k in zip(bs_calls, strikes)]

    # Plot Comparison
    plt.figure(figsize=(9, 5))
    plt.plot(strikes, hr_ivs, 'b-o', label=r'Hobson-Rogers Smile ($\sigma(y)$)')
    plt.plot(strikes, bs_ivs, 'r--', label=r'Black-Scholes Flat IV ($\sigma_0$)')
    plt.axvline(S0, color='gray', linestyle=':', label='ATM Strike')
    plt.title(f'Simulation Study: Implied Volatility Comparison (T = {T}y)')
    plt.xlabel('Strike (K)')
    plt.ylabel('Implied Volatility')
    plt.grid(True, linestyle=':')
    plt.legend()
    plt.tight_layout()
    plt.show()

# ==============================================================================
# Task (2): Market Data Pipeline & Model Calibration
# ==============================================================================
def coontineus_EWMA(log_prices: np.ndarray, dt_series: np.ndarray, lmbda: float) -> float:
    # EWMA trend offset Y_0 
    # $Y_0 = Z_0 - \lambda \int_{-\infty}^{0} e^{\lambda s} Z_s \, ds$
    
    if len(log_prices) < 2:
        return 0.0
    time_steps = np.cumsum(dt_series[::-1])[::-1]
    weights = np.exp(-lmbda * time_steps)
    weights /= np.sum(weights)  # Normalized discrete weighting
    ewma_trend = np.sum(weights * log_prices)
    return float(log_prices[-1] - ewma_trend)

def run_simulation_market_data(
    selected_ts_event: str | None = None,
    nsmallest_delivery: int = 1):
    
    if nsmallest_delivery < 1:
        raise Exception('incorrect nsmallest_delivery')
    
    
    conn = sqlite3.connect(MAIN_DB_FILE_PATH)

    # Deriving data 
    futures_sql = '''
    SELECT ts_event, sum(wavg_price) as close_of_future
    FROM (
        SELECT ohlc.ts_event,
               ohlc.close * CAST(ohlc.volume AS REAL) / CAST(day_total.volume AS REAL) as wavg_price
        FROM (SELECT * FROM ice_futures_data_month WHERE close IS NOT NULL) ohlc
        INNER JOIN (
            SELECT ts_event, symbol, sum(volume) as volume
            FROM ice_futures_data_month WHERE close IS NOT NULL GROUP BY ts_event, symbol
        ) day_total ON ohlc.symbol = day_total.symbol AND ohlc.ts_event = day_total.ts_event
    ) GROUP BY ts_event ORDER BY ts_event;
    '''
    
    df_futures = pd.read_sql_query(futures_sql, conn)
    df_futures['ts_event'] = pd.to_datetime(df_futures['ts_event'])
    df_futures.dropna(subset=['close_of_future'], inplace=True)

    ####################################################
    # Estimate sigma from historical log-returns
    # $$r_t = \ln\left(\frac{S_t}{S_{t-1}}\right)$$

    df_futures['log_ret'] = np.log(df_futures['close_of_future'] / df_futures['close_of_future'].shift(1))

    # Calculates the annualized sample standard deviation of daily log-returns
    sigma_hist = df_futures['log_ret'].std() * np.sqrt(252)
    
    print(f'\nAnnualized sample standard deviation of daily log-returns: {sigma_hist:.4f}')

    # Select data ts_event)
    options_sql = '''
    SELECT o_pvt.*, f.close_of_future, r.euro_short_term_rate
    FROM (
        SELECT contract_code, ts_event, contract_delivery_period, option_strike_price,
               option_expiry_date,
               sum(CASE option_payoff_style WHEN 'P' THEN wavg_price ELSE 0 END) put_price,
               sum(CASE option_payoff_style WHEN 'C' THEN wavg_price ELSE 0 END) call_price,
               sum(CASE option_payoff_style WHEN 'P' THEN volume ELSE 0 END) put_volume,
               sum(CASE option_payoff_style WHEN 'C' THEN volume ELSE 0 END) call_volume
        FROM (
            SELECT ohlc.contract_code, ohlc.ts_event, ohlc.contract_delivery_period,
                   ohlc.option_strike_price, ohlc.option_expiry_date, ohlc.option_payoff_style,
                   ohlc.close * CAST(ohlc.volume AS REAL) / CAST(day_total.volume AS REAL) as wavg_price,
                   ohlc.volume
            FROM (SELECT * FROM ice_options_data_month WHERE close IS NOT NULL) ohlc
            INNER JOIN (
                SELECT ts_event, symbol, sum(volume) volume
                FROM ice_options_data_month WHERE close IS NOT NULL GROUP BY ts_event, symbol
            ) day_total ON ohlc.symbol = day_total.symbol AND ohlc.ts_event = day_total.ts_event
        ) GROUP BY contract_code, ts_event, contract_delivery_period, option_strike_price, option_expiry_date
    ) o_pvt
    LEFT JOIN (
        SELECT ts_event, contract_delivery_period, sum(wavg_price) as close_of_future
        FROM (
            SELECT ohlc.ts_event, ohlc.contract_delivery_period,
                   ohlc.close * CAST(ohlc.volume AS REAL) / CAST(day_total.volume AS REAL) as wavg_price
            FROM (SELECT * FROM ice_futures_data_month WHERE close IS NOT NULL) ohlc
            INNER JOIN (
                SELECT ts_event, symbol, sum(volume) volume
                FROM ice_futures_data_month WHERE close IS NOT NULL GROUP BY ts_event, symbol
            ) day_total ON ohlc.symbol = day_total.symbol AND ohlc.ts_event = day_total.ts_event
        ) GROUP BY ts_event, contract_delivery_period
    ) f ON o_pvt.ts_event = f.ts_event AND o_pvt.contract_delivery_period = f.contract_delivery_period
    LEFT JOIN euro_short_term_rates r ON o_pvt.ts_event = r."date"
    WHERE close_of_future IS NOT NULL AND euro_short_term_rate IS NOT NULL;
    '''
    
    df_options = pd.read_sql_query(options_sql, conn)
    conn.close()

    if df_options.empty:
        print('No matching options data found.')
        return

    # max date selection with the closest expiry
    if selected_ts_event == None:
        selected_ts_event = df_options['ts_event'].max()
    else:
        if len(selected_ts_event) != 10:
            raise Exception(f'invalid selected_ts_event: {selected_ts_event}')
        try:
            date.fromisoformat(selected_ts_event)
        except (ValueError, TypeError):
            raise Exception(f'invalid selected_ts_event: {selected_ts_event}')


    selected_df = df_options[df_options['ts_event'] == selected_ts_event].copy()
    
    if len(selected_df) == 0:
        raise Exception('no data')
    
    selected_df['T'] = (pd.to_datetime(selected_df['option_expiry_date']) - pd.to_datetime(selected_df['ts_event'])).dt.days / 365
    selected_df = selected_df[selected_df['T'] > 0.02]  # Filter out expiring options
    
    # Filter the first delivery period in calendar order 
    # target_T = selected_df['T'].iloc[0]
    # target_T = min(selected_df['T'])
    target_T = selected_df['T'].drop_duplicates().nsmallest(nsmallest_delivery).iloc[-1]
    selected_df = selected_df[np.isclose(selected_df['T'], target_T, atol=0.01)].copy()

    #  Liquidity selection, the one with the highest volume 
    selected_df['target_price'] = np.where( selected_df['call_volume'] >= selected_df['put_volume'],
                                            selected_df['call_price'], 
                                            selected_df['put_price'])
    
    selected_df['option_type'] = np.where(selected_df['call_volume'] >= selected_df['put_volume'], 'C', 'P')
    selected_df = selected_df[selected_df['target_price'] > 0.05].copy()

    # Compute Market Implied Volatilities
    S0 = selected_df['close_of_future'].iloc[0]
    r = selected_df['euro_short_term_rate'].iloc[0] / 100.0
    
    selected_df['market_iv'] = [
        derive_implied_volatility_bs(row['target_price'], S0, row['option_strike_price'], r, row['T'], row['option_type'])
        for _, row in selected_df.iterrows()
    ]
    
    selected_df.dropna(subset=['market_iv'], inplace=True)
    selected_df.sort_values('option_strike_price', inplace=True)

    # Compute BS benchmark prices with constant historical sigma
    selected_df['bs_price_const'] = [
        bs_price(S0, row['option_strike_price'], r, row['T'], sigma_hist, row['option_type'])
        for _, row in selected_df.iterrows()
    ]

    # Calibrate HR Pparameters
    log_prices_hist = np.log(df_futures[df_futures['ts_event'] <= pd.to_datetime(selected_ts_event)]['close_of_future'].values)
    dt_series = np.full(len(log_prices_hist), 1.0 / 252.0)
    strikes = selected_df['option_strike_price'].values
    market_prices = selected_df['target_price'].values
    types = selected_df['option_type'].values

    # def calibration_loss(params):
    #     sigma0, eps, lmbda = params
    #     y0 = coontineus_EWMA(log_prices_hist, dt_series, lmbda)
    #     c_mc, p_mc = hobson_rogers_mc_grid(S0, y0, strikes, r, target_T, sigma0, eps, lmbda, n_sims=5000, n_steps=40)
    #     model_prices = np.where(types == 'C', c_mc, p_mc)
    #     return np.sum((model_prices - market_prices)**2)



    def calibration_loss(params):
        sigma0, eps, lmbda, gamma = params
        np.random.seed(42)  # Deterministic seed across solver iterations
        
        y0 = coontineus_EWMA(log_prices_hist, dt_series, lmbda)
        c_mc, p_mc = hobson_rogers_mc_grid(
            S0, y0, strikes, r, target_T, sigma0, eps, lmbda, gamma,
            n_sims=4000, n_steps=30, C=5.0
        )
        model_prices = np.where(types == 'C', c_mc, p_mc)
        
        # Invert to IV space to avoid dollar-magnitude distortion
        model_ivs = np.array([
            derive_implied_volatility_bs(p, S0, k, r, target_T, opt_type)
            for p, k, opt_type in zip(model_prices, strikes, types)
        ])
        
        valid_mask = ~np.isnan(model_ivs) & ~np.isnan(selected_df['market_iv'].values)
        if np.sum(valid_mask) < len(strikes) // 2:
            return 1e6
            
        return float(np.sum((model_ivs[valid_mask] - selected_df['market_iv'].values[valid_mask])**2))
    
    # Optimizing HR param
    init_guess = [sigma_hist, 0.5, 1.5]
    # bounds = [(0.05, 1.0), (0.01, 5.0), (0.1, 10.0)]
#     bounds = [
#     (0.01, 4.0),   # sigma0: allows baseline vol up to 400%
#     (0.001, 10.0), # epsilon: offset sensitivity
#     (0.05, 15.0)   # lambda: memory decay rate
# ]
    # # res = minimize(calibration_loss, init_guess, method='L-BFGS-B', bounds=bounds)
    # res = minimize(calibration_loss, init_guess, method='Nelder-Mead', bounds=bounds, options={'maxiter': 200, 'xatol': 1e-3, 'fatol': 1e-3})

    # opt_sigma0, opt_eps, opt_lmbda = res.x
    # print(f'Calibrated Parameters: sigma0 = {opt_sigma0:.4f}, epsilon = {opt_eps:.4f}, lamda = {opt_lmbda:.4f}')
    atm_iv = float(selected_df.loc[(selected_df['option_strike_price'] - S0).abs().idxmin(), 'market_iv'])
    init_guess = [atm_iv, 0.5, 1.5, -0.2]  # Seed gamma negative for upward commodity call skew
    
    bounds = [
        (0.10, 2.5),    # sigma0
        (0.001, 10.0),  # epsilon
        (0.10, 10.0),   # lambda
        (-2.0, 2.0)     # gamma (allows positive or negative skew)
    ] 
    
    print("Calibrating Asymmetric Hobson-Rogers parameters...")
    res = minimize(calibration_loss, init_guess, method='Nelder-Mead', bounds=bounds,
                   options={'maxiter': 300, 'xatol': 1e-3, 'fatol': 1e-3})

    opt_sigma0, opt_eps, opt_lmbda, opt_gamma = res.x
    print(f"Calibrated: σ0={opt_sigma0:.4f}, ε={opt_eps:.4f}, λ={opt_lmbda:.4f}, γ={opt_gamma:.4f}")

    # Evaluate Final Calibrated HR Prices
    opt_y0 = coontineus_EWMA(log_prices_hist, dt_series, opt_lmbda)
    hr_c_fit, hr_p_fit = hobson_rogers_mc_grid(S0, opt_y0, strikes, r, target_T, opt_sigma0, opt_eps, opt_lmbda, gamma=opt_gamma, n_sims=20000)
    selected_df['hr_price_fit'] = np.where(types == 'C', hr_c_fit, hr_p_fit)

    # Fit comparson (target price mse )
    mse_bs = np.mean((selected_df['bs_price_const'] - selected_df['target_price'])**2)
    mse_hr = np.mean((selected_df['hr_price_fit'] - selected_df['target_price'])**2)

    print(f'')
    print(f'# # # # Fit Comparison # # # # # # # # ')
    print(f'')
    print(f'BS MSE            : {mse_bs:.6f}')
    print(f'')
    print(f'HR Calibrated MSE : {mse_hr:.6f}')
    print(f'')
    print(f'# # # # # # # # # # # # # # # # # # # # ')
    print(f'')

    # Calibration Smile Plot
    selected_df['hr_iv_fit'] = [
        
        derive_implied_volatility_bs(row['hr_price_fit'], 
                                     S0, 
                                     row['option_strike_price'], 
                                     r, 
                                     row['T'], 
                                     row['option_type'])
        
        for _, row in selected_df.iterrows()
    ]
    
    plt.figure(figsize=(9, 5))
    plt.plot(selected_df['option_strike_price'], selected_df['market_iv'], 'ko', label='Market Implied Vol')
    plt.plot(selected_df['option_strike_price'], selected_df['hr_iv_fit'], 'b-', label='Calibrated HR Model')
    # plt.axhline(sigma_hist, color='r', linestyle='--', label=f'Annualized sample standard deviation of daily log-returns Vol ({sigma_hist:.2%})')
    plt.axvline(x=S0, color='grey', linestyle='--', linewidth=1.5, label=f'ATM Strike ({S0:.1f})')
    plt.title(f'Market vs Hobson-Rogers vs Black-Scholes (T = {target_T:.2f}y)')
    plt.xlabel('Strike Price (K)')
    plt.ylabel('Implied Volatility')
    plt.grid(True, linestyle=':')
    plt.legend()
    plt.tight_layout()
    plt.show()

    return selected_df

if __name__ == '__main__':
    np.random.seed(0)
    # run_simulation_study()
        
    run_simulation_market_data(nsmallest_delivery=1, selected_ts_event='2026-04-20')