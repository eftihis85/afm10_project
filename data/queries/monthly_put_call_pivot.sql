-- DROP TABLE IF EXISTS monthly_put_call_pivot;
-- CREATE TABLE IF NOT EXISTS monthly_put_call_pivot AS
SELECT      o_pvt.*, f.close_of_future, r.euro_short_term_rate
FROM        (
                SELECT      count(*) 'check',
                            contract_code,
                            ts_event, 
                            contract_delivery_period, 
                            option_strike_price, 
                            option_exercise_style ex_style,
                            option_term opt_term,
                            option_expiry_date, 
                            sum(CASE option_payoff_style WHEN 'P' THEN wavg_price ELSE 0 END) put_price,
                            sum(CASE option_payoff_style WHEN 'C' THEN wavg_price ELSE 0 END) call_price,
                            sum(CASE option_payoff_style WHEN 'P' THEN volume ELSE 0 END) put_volume,
                            sum(CASE option_payoff_style WHEN 'C' THEN volume ELSE 0 END) call_volume
                FROM        (
                                SELECT      ohlc.contract_code,
                                            ohlc.ts_event, 
                                            ohlc.contract_delivery_period, 
                                            ohlc.option_strike_price, 
                                            ohlc.option_exercise_style,
                                            ohlc.option_term,
                                            ohlc.option_expiry_date, 
                                            ohlc.option_payoff_style,
                                            ohlc.volume,
                                           -- ohlc.*, 
                                           -- CAST(ohlc.volume AS REAL) / CAST( day_total.volume AS REAL) as weight, 
                                            ohlc.close * CAST(ohlc.volume AS REAL) / CAST( day_total.volume AS REAL)  as wavg_price
                                FROM        (
                                                SELECT  *
                                                FROM    ice_options_data_month 
                                                WHERE   close is not NULL
                                            ) ohlc
                                            INNER JOIN
                                            (
                                                SELECT      ts_event, symbol, sum(volume) volume
                                                FROM        ice_options_data_month 
                                                WHERE       close is not NULL
                                                GROUP BY    ts_event, symbol
                                            ) day_total
                                            ON ohlc.symbol = day_total.symbol
                                            AND ohlc.ts_event = day_total.ts_event
                            ) 
                GROUP BY    contract_code,
                            ts_event, 
                            contract_delivery_period, 
                            option_strike_price, 
                            option_exercise_style,
                            option_term,
                            option_expiry_date
                ORDER BY    contract_code,
                            ts_event, 
                            contract_delivery_period, 
                            option_strike_price, 
                            option_exercise_style,
                            option_term,
                            option_expiry_date 
            ) o_pvt
            LEFT JOIN
            (
                SELECT      count(*) 'check',
                            contract_code,
                            ts_event, 
                            contract_delivery_period, 
                            sum(wavg_price) close_of_future
                FROM        (
                                SELECT      ohlc.contract_code,
                                            ohlc.ts_event, 
                                            ohlc.contract_delivery_period, 
                                           -- ohlc.*, 
                                           -- CAST(ohlc.volume AS REAL) / CAST( day_total.volume AS REAL) as weight, 
                                            ohlc.close * CAST(ohlc.volume AS REAL) / CAST( day_total.volume AS REAL)  as wavg_price
                                FROM        (
                                                SELECT  *
                                                FROM    ice_futures_data_month 
                                                WHERE   close is not NULL
                                            ) ohlc
                                            INNER JOIN
                                            (
                                                SELECT      ts_event, symbol, sum(volume) volume
                                                FROM        ice_futures_data_month 
                                                WHERE       close is not null
                                                GROUP BY    ts_event, symbol
                                            ) day_total
                                            ON ohlc.symbol = day_total.symbol
                                            AND ohlc.ts_event = day_total.ts_event
                            ) 
                GROUP BY    contract_code,
                            ts_event, 
                            contract_delivery_period
                ORDER BY    contract_code,
                            ts_event, 
                            contract_delivery_period
            ) f
            ON      o_pvt.ts_event = f.ts_event
            AND     o_pvt.contract_delivery_period = f.contract_delivery_period
            LEFT JOIN
            euro_short_term_rates r
            ON      o_pvt.ts_event = r."date"
            