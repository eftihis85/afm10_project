
-- SELECT * FROM ice_options_data_month;

-- delete from ice_options_data_month;

-- DROP TABLE ice_options_data_month;



SELECT * FROM ice_options_data_month
where (ts_event, instrument_id) IN (
									select ts_event, instrument_id 
									from  (
													SELECT ts_event, instrument_id, count(DISTINCT publisher_id)
													FROM ice_options_data_month
													HAVING count(DISTINCT publisher_id) > 1
												)
);

select * from ice_options_data_month where instrument_id = 108147169



-- SELECT COUNT(*)
-- FROM ice_options_data_month;
