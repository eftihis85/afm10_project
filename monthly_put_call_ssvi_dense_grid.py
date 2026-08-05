from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize

# Import paths from your local configuration module
from files import MAIN_DB_FILE_PATH

# ----------------------------------------------------------------------
# 1. SSVI Formula & Surface Interpolator Class
# ----------------------------------------------------------------------


class SSVISurface:
    """Class to calibrate SSVI on market options data and sample/extrapolate

    smooth Implied Volatility for ANY arbitrary (K, T) pair.
    """

    def __init__(self, rho: float, eta: float, gamma: float, theta_interpolator):
        self.rho = rho
        self.eta = eta
        self.gamma = gamma
        self.theta_interpolator = theta_interpolator

    @staticmethod
    def _w_func(k, theta, rho, eta, gamma):
        """Raw SSVI total variance formula."""
        phi = eta / ((theta**gamma) * ((1.0 + theta) ** (1.0 - gamma)))
        inside_sqrt = (phi * k + rho) ** 2 + (1.0 - rho**2)
        return (theta / 2.0) * (1.0 + rho * phi * k + np.sqrt(inside_sqrt))

    def predict_iv(
        self, K: np.ndarray, F: np.ndarray, T: np.ndarray
    ) -> np.ndarray:
        """Evaluates Implied Volatility for arbitrary Strikes (K), Forwards (F), and Expiries (T).

        Supports both interpolation (between data points) and extrapolation (outside min/max T).
        """
        # 1. Extrapolate/Interpolate ATM Variance theta(T) using monotone PCHIP
        theta_T = self.theta_interpolator(T)

        # 2. Compute Log-Moneyness k = ln(K / F)
        k = np.log(K / F)

        # 3. Calculate Total Variance w(k, theta_T)
        w_pred = self._w_func(k, theta_T, self.rho, self.eta, self.gamma)

        # 4. Convert Total Variance back to Implied Volatility: sigma = sqrt(w / T)
        iv_pred = np.sqrt(np.maximum(w_pred, 1e-6) / T)
        return iv_pred


# ----------------------------------------------------------------------
# 2. SSVI Surface Calibration Engine
# ----------------------------------------------------------------------


def calibrate_ssvi_surface(df_valid: pd.DataFrame) -> SSVISurface:
    """Fits global SSVI parameters (rho, eta, gamma) and interpolates ATM variance theta(T)."""
    slice_summary = []

    # Step 1: Extract ATM Variance Curve theta(T) per expiry slice
    for (ts_event, expiry), group in df_valid.groupby(
        ["ts_event", "option_expiry_date"]
    ):
        T = group["T"].iloc[0]
        # ATM option is where |log_moneyness| is smallest
        atm_row = group.iloc[(group["log_moneyness"].abs()).argmin()]
        slice_summary.append({"T": T, "theta": atm_row["total_variance"]})

    df_atm = (
        pd.DataFrame(slice_summary)
        .sort_values("T")
        .drop_duplicates(subset=["T"])
    )

    # Monotonic Cubic Spline (PCHIP) with linear extrapolation for T beyond observation limits
    T_knots = df_atm["T"].values
    theta_knots = np.maximum.accumulate(df_atm["theta"].values)

    # Use PCHIP with extrapolate=True to safely extrapolate time-structure out to long dates
    theta_interpolator = PchipInterpolator(
        T_knots, theta_knots, extrapolate=True
    )

    # Step 2: Global Optimization for Smile parameters (rho, eta, gamma)
    df_valid["theta_T"] = theta_interpolator(df_valid["T"].values)

    k_all = df_valid["log_moneyness"].values
    theta_all = df_valid["theta_T"].values
    w_mkt_all = df_valid["total_variance"].values

    def global_loss(params):
        rho, eta, gamma = params
        w_pred = SSVISurface._w_func(k_all, theta_all, rho, eta, gamma)
        return np.sum((w_pred - w_mkt_all) ** 2)

    initial_guess = [-0.3, 0.5, 0.25]
    bounds = [(-0.99, 0.99), (0.0001, 2.0), (0.0001, 0.5)]

    res = minimize(
        global_loss, initial_guess, bounds=bounds, method="L-BFGS-B"
    )
    rho_opt, eta_opt, gamma_opt = res.x

    return SSVISurface(rho_opt, eta_opt, gamma_opt, theta_interpolator)


# ----------------------------------------------------------------------
# 3. Pipeline: Interpolate Table & Construct Extrapolated Grid
# ----------------------------------------------------------------------


def process_and_extrapolate_ssvi(
    db_path: Path,
    source_table: str = "monthly_put_call_iv_results",
    target_table: str = "monthly_put_call_ssvi_results",
):
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {source_table}", conn)

    # Compute Time-To-Expiry T
    df["T"] = (
        pd.to_datetime(df["option_expiry_date"])
        - pd.to_datetime(df["ts_event"])
    ).dt.days / 365.25

    # Filter valid rows to calibrate SSVI model
    valid_mask = (
        df["implied_volatility"].notna()
        & (df["implied_volatility"] > 0)
        & (df["T"] > 0.001)
        & (df["close_of_future"] > 0)
    )
    df_valid = df[valid_mask].copy()

    df_valid["log_moneyness"] = np.log(
        df_valid["option_strike_price"] / df_valid["close_of_future"]
    )
    df_valid["total_variance"] = (
        df_valid["implied_volatility"] ** 2
    ) * df_valid["T"]

    print("Step 1: Calibrating global SSVI Model...")
    ssvi_model = calibrate_ssvi_surface(df_valid)

    # ------------------------------------------------------------------
    # PART A: Interpolate/Fill missing cells on the existing DB schema
    # ------------------------------------------------------------------
    print("Step 2: Interpolating missing/NULL values in database table...")
    full_mask = (df["T"] > 0.001) & (df["close_of_future"] > 0)

    df.loc[full_mask, "ssvi_implied_volatility"] = ssvi_model.predict_iv(
        K=df.loc[full_mask, "option_strike_price"].values,
        F=df.loc[full_mask, "close_of_future"].values,
        T=df.loc[full_mask, "T"].values,
    )

    # Drop temporary column and write back to SQLite
    df_output = df.drop(columns=["T"])
    with sqlite3.connect(db_path) as conn:
        df_output.to_sql(target_table, conn, if_exists="replace", index=False)

    print(f"-> Filled table saved to '{target_table}'.")

    # ------------------------------------------------------------------
    # PART B: Extrapolate full continuous dense grid (Any Strike & Maturity)
    # ------------------------------------------------------------------
    print(
        "Step 3: Generating dense extrapolated grid across new Strikes & Expiries..."
    )

    # Define arbitrary dense ranges for Extrapolation/Interpolation:
    # Example: Strikes from 20 to 120, Expiries from 1 month to 2 years
    dense_strikes = np.linspace(20.0, 120.0, 50)  # 50 strike steps
    dense_expiries = np.linspace(
        0.0833, 2.0, 24
    )  # 24 monthly maturities (0.083y to 2y)
    ref_forward = df_valid["close_of_future"].mean()  # Benchmark forward price

    # Meshgrid for full 3D surface expansion
    K_grid, T_grid = np.meshgrid(dense_strikes, dense_expiries)
    F_grid = np.full_like(K_grid, ref_forward)

    IV_extrapolated_grid = ssvi_model.predict_iv(
        K=K_grid.flatten(), F=F_grid.flatten(), T=T_grid.flatten()
    ).reshape(K_grid.shape)

    # Convert continuous grid to long DataFrame representation
    grid_records = []
    for i, t in enumerate(dense_expiries):
        for j, k in enumerate(dense_strikes):
            grid_records.append(
                {
                    "time_to_expiry_years": round(t, 4),
                    "strike_price": round(k, 2),
                    "forward_price": ref_forward,
                    "extrapolated_svi_iv": IV_extrapolated_grid[i, j],
                }
            )

    df_dense_grid = pd.DataFrame(grid_records)

    with sqlite3.connect(db_path) as conn:
        df_dense_grid.to_sql(
            "monthly_put_call_ssvi_dense_grid",
            conn,
            if_exists="replace",
            index=False,
        )

    print(
        "-> Continuous 3D extrapolated surface saved to table 'monthly_put_call_ssvi_dense_grid'."
    )


if __name__ == "__main__":
    process_and_extrapolate_ssvi(MAIN_DB_FILE_PATH)