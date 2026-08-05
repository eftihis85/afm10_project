SELECT
    time_to_expiry_years,
    strike_price,
    forward_price,
    extrapolated_svi_iv
FROM
    monthly_put_call_ssvi_dense_grid;