from abc import ABC


class IceDataCommon(ABC):
    def __init__(self, row: dict[str, str])->None:
            
        def get_int_or_none_from_str_or_none(s:str | None)-> int| None:
            if s is None:
                return None
            try:
                return int(s)
            except:
                return None
        
        def get_int_or_zero(s:str | None)-> int:
            if s is None:
                return 0
            try:
                return int(s)
            except:
                return 0
            
        def get_float_or_none(s:str | None)-> float | None:
            if s is None:
                return None
            try:
                return float(s)
            except:
                return None

        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')
        self.ts_event_date_only_str = (row.get('ts_event') or '')[:10]
        self.rtype = get_int_or_none_from_str_or_none(s=row.get('rtype'))
        self.publisher_id = get_int_or_none_from_str_or_none(s=row.get('publisher_id'))
        self.instrument_id = get_int_or_none_from_str_or_none(s=row.get('instrument_id'))
        self.volume = get_int_or_zero(row.get('volume'))
        
        
        self.open:float | None = get_float_or_none(row.get('open'))
        self.high:float | None = get_float_or_none(row.get('high'))
        self.low:float | None = get_float_or_none(row.get('low'))
        self.close:float | None = get_float_or_none(row.get('close'))