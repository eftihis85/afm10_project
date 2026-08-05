# ----------------------------------------------------------------------
# 4. SVI Model Fitting Functions
# ----------------------------------------------------------------------
def svi_total_variance(k, a, b, rho, m, sigma):
    """Raw SVI formula for Total Implied Variance w(k) = sigma^2 * T."""
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma**2))


def fit_svi_slice(k_market, w_market):
    """Fits SVI parameters (a, b, rho, m, sigma) for a single expiry slice via least squares optimization."""

    def objective(params):
        a, b, rho, m, sigma = params
        w_pred = svi_total_variance(k_market, a, b, rho, m, sigma)
        return np.sum((w_pred - w_market) ** 2)

    # Initial parameter guess: [a, b, rho, m, sigma]
    initial_guess = [0.04, 0.1, -0.3, 0.0, 0.1]

    # Theoretical SVI bounds to preserve smile shape
    bounds = [
        (1e-5, None),  # a >= 0 (minimum total variance level)
        (1e-5, None),  # b >= 0 (slope angle of asymptotes)
        (-0.999, 0.999),  # -1 < rho < 1 (skew rotation angle)
        (-2.0, 2.0),  # m (horizontal shift/ATM location)
        (1e-4, 2.0),  # sigma > 0 (vertex curvature)
    ]

    res = minimize(
        objective, initial_guess, bounds=bounds, method="L-BFGS-B"
    )
    return res.x if res.success else initial_guess


def apply_svi_smoothing(
    db_path: Path,
    source_table: str = "monthly_put_call_iv_results",
    target_table: str = "monthly_put_call_svi_results",
) -> pd.DataFrame:
    """Reads the raw IV table, fits SVI per (ts_event, option_expiry_date) slice,

    and exports the smoothed surface to SQLite.
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {source_table}", conn)

    # Calculate Time-To-Expiry (T) in year fraction
    df["T"] = (
        pd.to_datetime(df["option_expiry_date"])
        - pd.to_datetime(df["ts_event"])
    ).dt.days / 365.25

    # Filter valid rows to fit the SVI model curves
    valid_mask = (
        df["implied_volatility"].notna()
        & (df["implied_volatility"] > 0)
        & (df["T"] > 0.001)
        & (df["close_of_future"] > 0)
    )

    df_valid = df[valid_mask].copy()

    # Log-Moneyness k = ln(K / F) and Total Variance w = IV^2 * T
    df_valid["log_moneyness"] = np.log(
        df_valid["option_strike_price"] / df_valid["close_of_future"]
    )
    df_valid["total_variance"] = (
        df_valid["implied_volatility"] ** 2
    ) * df_valid["T"]

    df["svi_implied_volatility"] = np.nan

    # Group by trading date (ts_event) and expiry date
    grouped = df_valid.groupby(["ts_event", "option_expiry_date"])

    print(
        f"Fitting SVI model across {len(grouped)} distinct expiry slices..."
    )

    for (ts_event, expiry), group in grouped:
        if len(group) < 3:
            # Skip slices with fewer than 3 valid market IV points
            continue

        k_mkt = group["log_moneyness"].values
        w_mkt = group["total_variance"].values

        # 1. Fit SVI parameters for current slice
        params = fit_svi_slice(k_mkt, w_mkt)

        # 2. Get mask for all records in the full dataset for this slice
        slice_mask = (df["ts_event"] == ts_event) & (
            df["option_expiry_date"] == expiry
        )

        full_strikes = df.loc[slice_mask, "option_strike_price"].values
        futures_prices = df.loc[slice_mask, "close_of_future"].values
        T_slice = df.loc[slice_mask, "T"].values

        # 3. Evaluate SVI model across all rows (filling missing/NULL values automatically)
        k_full = np.log(full_strikes / futures_prices)
        w_pred = svi_total_variance(k_full, *params)

        # 4. Convert Total Variance back to Implied Volatility: sigma = sqrt(w / T)
        iv_svi = np.sqrt(np.maximum(w_pred, 1e-6) / T_slice)

        df.loc[slice_mask, "svi_implied_volatility"] = iv_svi

    # Drop temporary calculation column
    df.drop(columns=["T"], inplace=True)

    # Save augmented DataFrame into target table
    with sqlite3.connect(db_path) as conn:
        df.to_sql(target_table, conn, if_exists="replace", index=False)

    print(f"SVI surface fitting completed. Saved to table '{target_table}'.")
    return df


# ----------------------------------------------------------------------
# Updated Execution Script
# ----------------------------------------------------------------------
if __name__ == "__main__":

    # Step 1: Run your existing pipeline to generate market IVs
    result_df = process_options_data(MAIN_DB_FILE_PATH, MONTH_PUT_CALL_PARITY)

    with sqlite3.connect(MAIN_DB_FILE_PATH) as conn:
        result_df.to_sql(
            "monthly_put_call_iv_results",
            conn,
            if_exists="replace",
            index=False,
        )

    print("Step 1 Complete: Market IVs calculated and saved.")

    # Step 2: Fit SVI model to smooth the surface and fill missing values
    svi_df = apply_svi_smoothing(
        MAIN_DB_FILE_PATH,
        source_table="monthly_put_call_iv_results",
        target_table="monthly_put_call_svi_results",
    )

    print("Step 2 Complete: SVI smoothing pipeline finished successfully!")