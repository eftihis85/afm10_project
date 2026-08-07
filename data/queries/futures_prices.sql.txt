
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
