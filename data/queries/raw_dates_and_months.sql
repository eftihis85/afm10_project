SELECT      *
FROM        (
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
-- RAW DATES PRODUCTION
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
                WITH RECURSIVE generate_dates(date_value) AS (
                    -- 1. Establish the starting date
                    SELECT '2026-04-22'
                    UNION ALL
                    -- 3. Increment the date by 1 day at a time
                    SELECT date(date_value, '+1 day')
                    FROM generate_dates
                    -- 3. Set the end condition (e.g., generate 10 days total)
                    WHERE date_value < date('2026-04-22', '4 days')
                )
                SELECT      dates.date_value, 
                            expiry.option_expiry_date, 
                            CASE    WHEN dates.date_value >= expiry.option_expiry_date 
                                        THEN DATE(dates.date_value, 'start of month', '+2 month') 
                                    ELSE  DATE(dates.date_value, 'start of month', '+1 month') 
                            END font_month 
                FROM        generate_dates dates
                            LEFT JOIN 
                            (        
                                SELECT      DATE(contract_delivery_period || '-01', '-1 month') contract_delivery_month, max( option_expiry_date) option_expiry_date, count(*) 
                                FROM        ( SELECT     DISTINCT contract_delivery_period, option_expiry_date 
                                FROM        ice_options_data_month)
                                GROUP BY    contract_delivery_period
                            ) expiry
                            ON expiry.contract_delivery_month = DATE(dates.date_value, 'start of month')
            ) dates
            LEFT JOIN
            (
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
-- RAW MONTHS PRODUCTION
-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
                WITH RECURSIVE month_series(month_date, month_counter) AS (
                    -- 1. Anchor member: Convert 'YYYY-MM' string to a valid date and set counter to 1
                    SELECT 
                        date('2018-01-01') AS month_date,
                        1 AS month_counter
                    UNION ALL
                    -- 2. Recursive member: Increment the month by 1 and increment the counter
                    SELECT 
                        date(month_date, '+1 month'),
                        month_counter + 1
                    FROM 
                        month_series
                    WHERE 
                        month_counter < 180 -- 3. Termination condition: Stop after 24 rows
                )
                -- 4. Final selection: Convert the date back to the 'YYYY-MM' display format
                SELECT 
                    month_date 
                FROM 
                    month_series
            ) months
            ON ( (strftime('%Y', months.month_date) - strftime('%Y', dates.font_month )) * 12 + 
                (strftime('%m', months.month_date) - strftime('%m', dates.font_month ))) >= 0
                AND  
                ( (strftime('%Y', months.month_date) - strftime('%Y', dates.font_month )) * 12 + 
                (strftime('%m', months.month_date) - strftime('%m', dates.font_month ))) < 24
