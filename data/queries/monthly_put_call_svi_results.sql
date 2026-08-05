
SELECT
    'check',
    contract_code,
    ts_event,
    contract_delivery_period,
    option_strike_price,
    ex_style,
    opt_term,
    option_expiry_date,
    put_price,
    call_price,
    put_volume,
    call_volume,
    close_of_future,
    euro_short_term_rate,
    selected_option,
    implied_volatility,
    svi_implied_volatility
FROM monthly_put_call_svi_results;