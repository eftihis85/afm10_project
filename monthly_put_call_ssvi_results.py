from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize

# Import paths from your local configuration module
from files import MAIN_DB_FILE_PATH

# ----------------------------------------------------------------------
# 1. SSVI Surface Functions & Optimization
# ----------------------------------------------------------------------


def ssvi_total_variance(k, theta, rho, eta, gamma):
    """Computes SSVI Total Implied Variance w(k, theta_T)."""
    # Smooth decay function phi(theta)
    phi = eta / ((theta**gamma) * ((1.0 + theta) ** (1.0 - gamma)))

    # SSVI variance formula
    inside_sqrt = (phi * k + rho) ** 2 + (1.0 - rho**2)
    w = (theta / 2.0) * (1.0 + rho * phi * k + np.sqrt(inside_sqrt))
    return w


def fit_ssvi_surface(df_valid: pd.DataFrame):
    """Fits global SSVI parameters across all slices to eliminate calendar arbitrage.

    Step 1: Fit smooth ATM variance curve theta(T) using monotone PCHIP.
    Step 2: Fit global parameters (rho, eta, gamma) across all market data points.
    """
    # ------------------------------------------------------------------
    # Step 1: Extract ATM Variance Curve theta(T) per expiry
    # ------------------------------------------------------------------
    slice_summary = []
    for (ts_event, expiry), group in df_valid.groupby(
        ["ts_event", "option_expiry_date"]
    ):
        T = group["T"].iloc[0]
        # Identify the option closest to at-the-money (log_moneyness close to 0)
        atm_row = group.iloc[(group["log_moneyness"].abs()).argmin()]
        theta_atm = atm_row["total_variance"]
        slice_summary.append({"T": T, "theta": theta_atm})

    df_atm = (
        pd.DataFrame(slice_summary)
        .sort_values("T")
        .drop_duplicates(subset=["T"])
    )

    # Monotonic Cubic Spline ensuring theta(T) is non-decreasing over time (No Calendar Arbitrage)
    theta_interpolator = PchipInterpolator(
        df_atm["T"].values, np.maximum.accumulate(df_atm["theta"].values)
    )

    # Apply theta(T) to all valid records
    df_valid["theta_T"] = theta_interpolator(df_valid["T"].values)

    # ------------------------------------------------------------------
    # Step 2: Global Optimization for (rho, eta, gamma)
    # ------------------------------------------------------------------
    k_all = df_valid["log_moneyness"].values
    theta_all = df_valid["theta_T"].values
    w_mkt_all = df_valid["total_variance"].values

    def global_loss(params):
        rho, eta, gamma = params
        w_pred = ssvi_total_variance(k_all, theta_all, rho, eta, gamma)
        return np.sum((w_pred - w_mkt_all) ** 2)

    # Bounds: rho in (-1, 1), eta > 0, gamma in (0, 0.5] for Heston-like smooth decay
    initial_guess = [-0.3, 0.5, 0.25]
    bounds = [(-0.99, 0.99), (0.0001, 2.0), (0.0001, 0.5)]

    res = minimize(
        global_loss, initial_guess, bounds=bounds, method="L-BFGS-B"
    )
    rho_opt, eta_opt, gamma_opt = res.x

    return theta_interpolator, (rho_opt, eta_opt, gamma_opt)


# ----------------------------------------------------------------------
# 2. Database Processing Pipeline
# ----------------------------------------------------------------------


def apply_ssvi_to_db(
    db_path: Path,
    source_table: str = "monthly_put_call_iv_results",
    target_table: str = "monthly_put_call_ssvi_results",
):
    """Pipeline to read market IVs, calibrate SSVI, and output arbitrage-free surface."""
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {source_table}", conn)

    # Calculate Time-to-Expiry (T)
    df["T"] = (
        pd.to_datetime(df["option_expiry_date"])
        - pd.to_datetime(df["ts_event"])
    ).dt.days / 365.25

    # Filter out invalid records
    valid_mask = (
        df["implied_volatility"].notna()
        & (df["implied_volatility"] > 0)
        & (df["T"] > 0.001)
        & (df["close_of_future"] > 0)
    )

    df_valid = df[valid_mask].copy()

    # Calculate log-moneyness k and market total variance w
    df_valid["log_moneyness"] = np.log(
        df_valid["option_strike_price"] / df_valid["close_of_future"]
    )
    df_valid["total_variance"] = (
        df_valid["implied_volatility"] ** 2
    ) * df_valid["T"]

    print("Calibrating 3D SSVI Surface across all expiries...")
    theta_interpolator, (rho_opt, eta_opt, gamma_opt) = fit_ssvi_surface(
        df_valid
    )

    print(
        f"Optimal SSVI Parameters: rho={rho_opt:.4f}, eta={eta_opt:.4f}, gamma={gamma_opt:.4f}"
    )

    # Evaluate SSVI for ALL rows in dataset (filling gaps & extrapolating smoothly)
    full_mask = (df["T"] > 0.001) & (df["close_of_future"] > 0)

    full_strikes = df.loc[full_mask, "option_strike_price"].values
    futures_prices = df.loc[full_mask, "close_of_future"].values
    T_full = df.loc[full_mask, "T"].values

    k_full = np.log(full_strikes / futures_prices)
    theta_full = theta_interpolator(T_full)

    # Predict Total Variance
    w_pred = ssvi_total_variance(
        k_full, theta_full, rho_opt, eta_opt, gamma_opt
    )

    # Derive Implied Volatility: sigma = sqrt(w / T)
    df.loc[full_mask, "ssvi_implied_volatility"] = np.sqrt(
        np.maximum(w_pred, 1e-6) / T_full
    )

    # Clean up temporary calculation columns
    df.drop(columns=["T"], inplace=True)

    # Save to SQLite target table
    with sqlite3.connect(db_path) as conn:
        df.to_sql(target_table, conn, if_exists="replace", index=False)

    print(f"Successfully saved 3D SSVI Surface to table '{target_table}'.")


if __name__ == "__main__":
    apply_ssvi_to_db(MAIN_DB_FILE_PATH)