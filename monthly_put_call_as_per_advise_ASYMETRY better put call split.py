from datetime import date
import sqlite3
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq, minimize
from scipy import stats
import matplotlib.pyplot as plt
from files import MAIN_DB_FILE_PATH
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch

# ==============================================================================
# 1. Black-Scholes Pricing & Implied Volatility Inversion
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

# ==============================================================================
# 2. Hobson-Rogers Monte Carlo Engine
# ==============================================================================
def hobson_rogers_mc_grid(S0: float, y0: float, strikes: np.ndarray, r: float, T: float,
                          sigma0: float, epsilon: float, lmbda: float, gamma: float = 0.0,
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
        
        # Safeguard against drift blow-up
        Y = np.clip(Y, -5.0, 5.0)
        
        # Asymmetric local volatility with upper cap C
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

def coontineus_EWMA(log_prices: np.ndarray, dt_series: np.ndarray, lmbda: float) -> float:
    if len(log_prices) < 2:
        return 0.0
    time_steps = np.cumsum(dt_series[::-1])[::-1]
    weights = np.exp(-lmbda * time_steps)
    weights /= np.sum(weights)
    ewma_trend = np.sum(weights * log_prices)
    return float(log_prices[-1] - ewma_trend)

# ==============================================================================
# 3. Market Data Pipeline & Separate Call/Put Calibration
# ==============================================================================
def run_simulation_market_data(
    selected_ts_event: str | None,
    contract_delivery_month: str):
    
    conn = sqlite3.connect(MAIN_DB_FILE_PATH)

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

    df_futures['log_ret'] = np.log(df_futures['close_of_future'] / df_futures['close_of_future'].shift(1))
    sigma_hist = df_futures['log_ret'].std() * np.sqrt(252)
    print(f'Annualized sample standard deviation of daily log-returns: {sigma_hist:.4f}')

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

    if selected_ts_event is None:
        selected_ts_event = df_options['ts_event'].max()
    else:
        date.fromisoformat(selected_ts_event)

    selected_df = df_options[df_options['ts_event'] == selected_ts_event].copy()
    if len(selected_df) == 0:
        raise Exception('No data found for selected date.')

    # Filter strictly by the requested contract_delivery_period
    available_delivery_periods = selected_df['contract_delivery_period'].unique().tolist()
    if contract_delivery_month not in available_delivery_periods:
        raise ValueError(
            f"Delivery period '{contract_delivery_month}' not found for date {selected_ts_event}. "
            f"Available periods: {available_delivery_periods}"
        )
    
    selected_df = selected_df[selected_df['contract_delivery_period'] == contract_delivery_month].copy()
    selected_df['T'] = (pd.to_datetime(selected_df['option_expiry_date']) - pd.to_datetime(selected_df['ts_event'])).dt.days / 365.25
    selected_df = selected_df[selected_df['T'] > 0.02].copy()
    
    if selected_df.empty:
        raise ValueError("Invalid date / contracts too close to expiry (T <= 0.02).")

    target_T = float(selected_df['T'].iloc[0])
    S0 = float(selected_df['close_of_future'].iloc[0])
    r = float(selected_df['euro_short_term_rate'].iloc[0]) / 100.0
    print(f"Targeting Delivery Period: {contract_delivery_month} | T = {target_T:.4f}y | S0 = {S0:.2f} | r = {r:.4f}")

    log_prices_hist = np.log(df_futures[df_futures['ts_event'] <= pd.to_datetime(selected_ts_event)]['close_of_future'].values)
    dt_series = np.full(len(log_prices_hist), 1.0 / 252.0)

    # --------------------------------------------------------------------------
    # Subsetting Calls and Puts Separately
    # --------------------------------------------------------------------------
    df_calls = selected_df[selected_df['call_price'] > 0.05].copy().sort_values('option_strike_price')
    df_calls['market_call_iv'] = [
        derive_implied_volatility_bs(p, S0, k, r, target_T, 'C')
        for p, k in zip(df_calls['call_price'], df_calls['option_strike_price'])
    ]
    df_calls.dropna(subset=['market_call_iv'], inplace=True)

    df_puts = selected_df[selected_df['put_price'] > 0.05].copy().sort_values('option_strike_price')
    df_puts['market_put_iv'] = [
        derive_implied_volatility_bs(p, S0, k, r, target_T, 'P')
        for p, k in zip(df_puts['put_price'], df_puts['option_strike_price'])
    ]
    df_puts.dropna(subset=['market_put_iv'], inplace=True)

    bounds_hr = [(0.05, 3.0), (0.001, 10.0), (0.10, 10.0), (-5.0, 5.0)]
    bounds_bs = [(0.01, 3.0)]

    # ==========================================================================
    # Calibration for CALL OPTIONS
    # ==========================================================================
    strikes_c = df_calls['option_strike_price'].values
    market_calls = df_calls['call_price'].values
    market_c_ivs = df_calls['market_call_iv'].values
    atm_call_iv = float(df_calls.loc[(df_calls['option_strike_price'] - S0).abs().idxmin(), 'market_call_iv'])

    def call_hr_loss(params):
        sigma0, eps, lmbda, gamma = params
        np.random.seed(42)
        y0 = coontineus_EWMA(log_prices_hist, dt_series, lmbda)
        c_mc, _ = hobson_rogers_mc_grid(
            S0, y0, strikes_c, r, target_T, sigma0, eps, lmbda, gamma=gamma,
            n_sims=4000, n_steps=30, C=5.0
        )
        model_ivs = np.array([derive_implied_volatility_bs(p, S0, k, r, target_T, 'C') for p, k in zip(c_mc, strikes_c)])
        valid_mask = ~np.isnan(model_ivs)
        if np.sum(valid_mask) < len(strikes_c) // 2:
            return 1e6
        return float(np.sum((model_ivs[valid_mask] - market_c_ivs[valid_mask])**2))

    print("\n--- Calibrating Models on CALLS ---")
    res_c_hr = minimize(call_hr_loss, [atm_call_iv, 0.5, 1.5, -0.2], method='Nelder-Mead', bounds=bounds_hr,
                        options={'maxiter': 250, 'xatol': 1e-3, 'fatol': 1e-3})
    c_s0, c_eps, c_lmbda, c_gamma = res_c_hr.x
    print(f"Calibrated HR (Calls): σ0={c_s0:.4f}, ε={c_eps:.4f}, λ={c_lmbda:.4f}, γ={c_gamma:.4f}")

    def call_bs_loss(sig):
        preds = np.array([bs_price(S0, k, r, target_T, sig[0], 'C') for k in strikes_c])
        return np.sum((preds - market_calls)**2)

    res_c_bs = minimize(call_bs_loss, [atm_call_iv], bounds=bounds_bs)
    fitted_bs_vol_c = float(res_c_bs.x[0])
    print(f"Fitted BS Vol (Calls): {fitted_bs_vol_c:.4f}")

    # ==========================================================================
    # Calibration for PUT OPTIONS
    # ==========================================================================
    strikes_p = df_puts['option_strike_price'].values
    market_puts = df_puts['put_price'].values
    market_p_ivs = df_puts['market_put_iv'].values
    atm_put_iv = float(df_puts.loc[(df_puts['option_strike_price'] - S0).abs().idxmin(), 'market_put_iv'])

    def put_hr_loss(params):
        sigma0, eps, lmbda, gamma = params
        np.random.seed(42)
        y0 = coontineus_EWMA(log_prices_hist, dt_series, lmbda)
        _, p_mc = hobson_rogers_mc_grid(
            S0, y0, strikes_p, r, target_T, sigma0, eps, lmbda, gamma=gamma,
            n_sims=4000, n_steps=30, C=5.0
        )
        model_ivs = np.array([derive_implied_volatility_bs(p, S0, k, r, target_T, 'P') for p, k in zip(p_mc, strikes_p)])
        valid_mask = ~np.isnan(model_ivs)
        if np.sum(valid_mask) < len(strikes_p) // 2:
            return 1e6
        return float(np.sum((model_ivs[valid_mask] - market_p_ivs[valid_mask])**2))

    print("\n--- Calibrating Models on PUTS ---")
    res_p_hr = minimize(put_hr_loss, [atm_put_iv, 0.5, 1.5, 0.2], method='Nelder-Mead', bounds=bounds_hr,
                        options={'maxiter': 250, 'xatol': 1e-3, 'fatol': 1e-3})
    p_s0, p_eps, p_lmbda, p_gamma = res_p_hr.x
    print(f"Calibrated HR (Puts) : σ0={p_s0:.4f}, ε={p_eps:.4f}, λ={p_lmbda:.4f}, γ={p_gamma:.4f}")

    def put_bs_loss(sig):
        preds = np.array([bs_price(S0, k, r, target_T, sig[0], 'P') for k in strikes_p])
        return np.sum((preds - market_puts)**2)

    res_p_bs = minimize(put_bs_loss, [atm_put_iv], bounds=bounds_bs)
    fitted_bs_vol_p = float(res_p_bs.x[0])
    print(f"Fitted BS Vol (Puts) : {fitted_bs_vol_p:.4f}")

    # ==========================================================================
    # Final Model Evaluations & Error Calculation
    # ==========================================================================
    # Call final evaluation
    y0_c = coontineus_EWMA(log_prices_hist, dt_series, c_lmbda)
    hr_c_fit, _ = hobson_rogers_mc_grid(
        S0=S0, y0=y0_c, strikes=strikes_c, r=r, T=target_T, sigma0=c_s0, epsilon=c_eps, lmbda=c_lmbda,
        gamma=c_gamma, n_sims=20000, n_steps=60, C=5.0
    )
    df_calls['hr_call_fit'] = hr_c_fit
    df_calls['hr_call_iv'] = [derive_implied_volatility_bs(p, S0, k, r, target_T, 'C') for p, k in zip(hr_c_fit, strikes_c)]
    df_calls['bs_call_fit'] = [bs_price(S0, k, r, target_T, fitted_bs_vol_c, 'C') for k in strikes_c]

    # Put final evaluation
    y0_p = coontineus_EWMA(log_prices_hist, dt_series, p_lmbda)
    _, hr_p_fit = hobson_rogers_mc_grid(
        S0=S0, y0=y0_p, strikes=strikes_p, r=r, T=target_T, sigma0=p_s0, epsilon=p_eps, lmbda=p_lmbda,
        gamma=p_gamma, n_sims=20000, n_steps=60, C=5.0
    )
    df_puts['hr_put_fit'] = hr_p_fit
    df_puts['hr_put_iv'] = [derive_implied_volatility_bs(p, S0, k, r, target_T, 'P') for p, k in zip(hr_p_fit, strikes_p)]
    df_puts['bs_put_fit'] = [bs_price(S0, k, r, target_T, fitted_bs_vol_p, 'P') for k in strikes_p]

    # MSE Statistics
    mse_bs_c = np.mean((df_calls['bs_call_fit'] - df_calls['call_price'])**2)
    mse_hr_c = np.mean((df_calls['hr_call_fit'] - df_calls['call_price'])**2)
    mse_bs_p = np.mean((df_puts['bs_put_fit'] - df_puts['put_price'])**2)
    mse_hr_p = np.mean((df_puts['hr_put_fit'] - df_puts['put_price'])**2)

    print("\n# # # # # # # # # # # # FIT COMPARISON # # # # # # # # # # #")
    print(f"CALLS -> BS MSE: {mse_bs_c:.6f} | HR MSE: {mse_hr_c:.6f}")
    print(f"PUTS  -> BS MSE: {mse_bs_p:.6f} | HR MSE: {mse_hr_p:.6f}")
    print("# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #\n")

    # ==========================================================================
    # Unified 2x2 Subplots: Puts (Row 1), Calls (Row 2)
    # ==========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # --- ROW 1: PUT OPTIONS ---
    axes[0, 0].plot(df_puts['option_strike_price'], df_puts['put_price'], 'ko', label='Market Put Price')
    axes[0, 0].plot(df_puts['option_strike_price'], df_puts['hr_put_fit'], 'b-', label='Calibrated HR (Puts)')
    axes[0, 0].plot(df_puts['option_strike_price'], df_puts['bs_put_fit'], 'r--', label='Fitted BS (Puts)')
    axes[0, 0].axvline(S0, color='grey', linestyle=':', label=f'ATM Strike ({S0:.1f})')
    axes[0, 0].set_title(f'Put Option Prices (MSE HR: {mse_hr_p:.4f} | BS: {mse_bs_p:.4f})')
    axes[0, 0].set_xlabel('Strike Price (K)')
    axes[0, 0].set_ylabel('Price (€)')
    axes[0, 0].grid(True, linestyle=':')
    axes[0, 0].legend()

    axes[0, 1].plot(df_puts['option_strike_price'], df_puts['market_put_iv'], 'ko', label='Market Put IV')
    axes[0, 1].plot(df_puts['option_strike_price'], df_puts['hr_put_iv'], 'b-', label='Calibrated HR IV (Puts)')
    axes[0, 1].axhline(fitted_bs_vol_p, color='r', linestyle='--', label=f'Fitted BS Vol ({fitted_bs_vol_p:.2%})')
    axes[0, 1].axvline(S0, color='grey', linestyle=':', label=f'ATM Strike ({S0:.1f})')
    axes[0, 1].set_title('Put Implied Volatilities')
    axes[0, 1].set_xlabel('Strike Price (K)')
    axes[0, 1].set_ylabel('Implied Volatility')
    axes[0, 1].grid(True, linestyle=':')
    axes[0, 1].legend()

    # --- ROW 2: CALL OPTIONS ---
    axes[1, 0].plot(df_calls['option_strike_price'], df_calls['call_price'], 'ko', label='Market Call Price')
    axes[1, 0].plot(df_calls['option_strike_price'], df_calls['hr_call_fit'], 'b-', label='Calibrated HR (Calls)')
    axes[1, 0].plot(df_calls['option_strike_price'], df_calls['bs_call_fit'], 'r--', label='Fitted BS (Calls)')
    axes[1, 0].axvline(S0, color='grey', linestyle=':', label=f'ATM Strike ({S0:.1f})')
    axes[1, 0].set_title(f'Call Option Prices (MSE HR: {mse_hr_c:.4f} | BS: {mse_bs_c:.4f})')
    axes[1, 0].set_xlabel('Strike Price (K)')
    axes[1, 0].set_ylabel('Price (€)')
    axes[1, 0].grid(True, linestyle=':')
    axes[1, 0].legend()

    axes[1, 1].plot(df_calls['option_strike_price'], df_calls['market_call_iv'], 'ko', label='Market Call IV')
    axes[1, 1].plot(df_calls['option_strike_price'], df_calls['hr_call_iv'], 'b-', label='Calibrated HR IV (Calls)')
    axes[1, 1].axhline(fitted_bs_vol_c, color='r', linestyle='--', label=f'Fitted BS Vol ({fitted_bs_vol_c:.2%})')
    axes[1, 1].axvline(S0, color='grey', linestyle=':', label=f'ATM Strike ({S0:.1f})')
    axes[1, 1].set_title('Call Implied Volatilities')
    axes[1, 1].set_xlabel('Strike Price (K)')
    axes[1, 1].set_ylabel('Implied Volatility')
    axes[1, 1].grid(True, linestyle=':')
    axes[1, 1].legend()

    plt.suptitle(f'Market vs HR vs BS (Independent Fits) | Date: {selected_ts_event} | Del. Period: {contract_delivery_month}', fontsize=14, y=0.995)
    plt.tight_layout()
    plt.show()

    return df_calls, df_puts

def verify_black_scholes_adequacy(log_returns: pd.Series):
    """
    Evaluates whether empirical gas forward returns conform to Black-76/Black-Scholes assumptions:
    - Log-normal returns (normality of log-returns)
    - Independent increments (no serial autocorrelation / random walk)
    - Constant volatility (no ARCH effects / volatility clustering)
    """
    r = log_returns.dropna().values
    
    # 1. Summary & Higher Moments
    mean_ann = np.mean(r) * 252.0
    vol_ann = np.std(r) * np.sqrt(252.0)
    skew = stats.skew(r)
    kurt = stats.kurtosis(r)  # Excess kurtosis (Normal = 0.0)
    
    # 2. Hypothesis Tests
    jb_stat, jb_pval = stats.jarque_bera(r)
    lb_df = acorr_ljungbox(r, lags=[5, 10], return_df=True)
    arch_stat, arch_pval, _, _ = het_arch(r)
    
    print("\n=======================================================")
    print("      BLACK-SCHOLES / BLACK-76 ADEQUACY DIAGNOSTIC     ")
    print("=======================================================")
    print(f"Sample Size (N)             : {len(r)}")
    print(f"Annualized Mean Return      : {mean_ann:.4f}")
    print(f"Annualized Sample Volatility: {vol_ann:.4f}")
    print(f"Sample Skewness             : {skew:.4f}  (Gaussian = 0.0)")
    print(f"Excess Kurtosis             : {kurt:.4f}  (Gaussian = 0.0)")
    print("-------------------------------------------------------")
    print(f"Jarque-Bera Test (Normality): p-value = {jb_pval:.4e}")
    if jb_pval < 0.05:
        print("  -> REJECT Normality (Fat tails / skew present in returns).")
    else:
        print("  -> Cannot reject Normality.")

    print(f"Ljung-Box Test (Lag 10)     : p-value = {lb_df.loc[10, 'lb_pvalue']:.4e}")
    if lb_df.loc[10, 'lb_pvalue'] < 0.05:
        print("  -> REJECT Independence (Significant autocorrelation detected).")
    else:
        print("  -> Cannot reject Random Walk assumption.")

    print(f"ARCH-LM Test (Heteroskedast): p-value = {arch_pval:.4e}")
    if arch_pval < 0.05:
        print("  -> REJECT Constant Volatility (Volatility clustering present).")
    else:
        print("  -> Cannot reject Constant Volatility.")
    print("=======================================================\n")

def run_diagnostic_on_db():
    conn = sqlite3.connect(MAIN_DB_FILE_PATH)

    # Use the same weighted-average futures query from your pipeline
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
    conn.close()

    df_futures['ts_event'] = pd.to_datetime(df_futures['ts_event'])
    df_futures.dropna(subset=['close_of_future'], inplace=True)

    # Calculate daily log-returns: r_t = ln(F_t / F_{t-1})
    df_futures['log_ret'] = np.log(df_futures['close_of_future'] / df_futures['close_of_future'].shift(1))

    # Run the test suite
    verify_black_scholes_adequacy(df_futures['log_ret'])

if __name__ == '__main__':
    np.random.seed(0)
    # run_diagnostic_on_db()
    df_c, df_p = run_simulation_market_data(selected_ts_event='2026-04-15', contract_delivery_month='2026-06')