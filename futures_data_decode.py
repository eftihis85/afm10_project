from abc import ABC, abstractmethod
import re
from datetime import date
from typing import Union

from ice_helper.datetime_misc import ICE_ts_event_to_dt
from ice_helper.delivery_period_specific_types import ICEDeliveryPeriod, ICEDeliveryPeriod_Daily, ICEDeliveryPeriod_Month, ICEDeliveryPeriod_NotSet, ICEDeliveryPeriod_Quarter, ICEDeliveryPeriod_Season, ICEDeliveryPeriod_Year
from ice_helper.types import ICEContractDeliveryTerm, ICEContractType, ICEMonth, ICESeason



class ICEFuturesData(ABC):
    @classmethod
    def decode_csv_row(cls, row: dict[str, str])-> ICEFuturesDataUnion:
        try:
            symbol = row.get('symbol')
            
            if not symbol:
                raise ValueError('symbol is None')
            
            symbol_len = len(symbol)

            match symbol_len:
                case 12:
                    # Month
                    return ICEFuturesData_Month(row)
                case 17:
                    # QSY
                    return ICEFuturesData_Unencoded(row)
                case 23:
                    # Month spread (maybe product too)
                    return ICEFuturesData_Unencoded(row)
                case 35:
                    # QSY spread (maybe product too)
                    return ICEFuturesData_Unencoded(row)
                case _:
                    return ICEFuturesData_Unencoded(row)
        except:
            return ICEFuturesData_Unencoded(row)
            
        
    
    def __init__(self, row: dict[str, str]):
        self.ts_event = ICE_ts_event_to_dt(row.get('ts_event') or '')
        self.rtype = row.get('rtype')
        self.publisher_id = row.get('publisher_id')
        self.instrument_id = row.get('instrument_id')
        self.open_price = row.get('open')
        self.high_price = row.get('high')
        self.low_price = row.get('low')
        self.close_price = row.get('close')
        self.volume = row.get('volume')
        
        
    @abstractmethod
    def __str__(self) -> str:
        return (    
                    f'ts_event: {self.ts_event}\n'
                    f'rtype: {self.rtype}\n'
                    f'publisher_id: {self.publisher_id}\n'
                    f'instrument_id: {self.instrument_id}\n'
                    f'open_price: {self.open_price}\n'
                    f'high_price: {self.high_price}\n'
                    f'low_price: {self.low_price}\n'
                    f'close_price: {self.close_price}\n'
                    f'volume: {self.volume}\n'
                )

class ICEFuturesData_Month(ICEFuturesData):
    def __init__(self, row: dict[str, str]):
        # up to here is ensured that 'symbol' is not null
        symbol:str =  row.get('symbol') or ''
        
        pattern =  (
                r'^'
                r'([A-Z\s]{4})'  # contract_code
                r'([A-Z]{1})'    # contract_type 
                r'([M])'         # contract_delivery_term 
                r'([A-Z])'       # contract_delivery_month_code
                r'(\d{2})'       # contract_delivery_day_of_the_month
                r'(\d{2})'       # contract_delivery_year
                r'([!])'         # exclamation_mark
                r'$'        
            )
        
        match = re.match(pattern, symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
        
        self.contract_code = str(match.group(1)).strip()
        self.contract_type = ICEContractType.from_code(str(match.group(2)))
        self.contract_delivery_term = ICEContractDeliveryTerm.from_code(str(match.group(3)))
        
        contract_delivery_month_code = str(match.group(4))
        contract_delivery_day_of_the_month = int(match.group(5))
        contract_delivery_year = int(match.group(6))
        
        self.contract_delivery_period:ICEDeliveryPeriod = self.contract_delivery_term.get_ice_delivery_period(contract_delivery_month_code, 
                                                                                                contract_delivery_day_of_the_month, 
                                                                                                contract_delivery_year) 
            
        
        
        super().__init__(row)
        
    
        
    def __str__(self) -> str:
        return super().__str__()
    



class ICEFuturesData_Unencoded(ICEFuturesData):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol')
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'symbol: {self.symbol}\n' 
                + super().__str__())





ICEFuturesDataUnion = Union[ICEFuturesData_Month, ICEFuturesData_Unencoded]




        # Month pattern
        pattern = r'^.{11}\!$'
        
        match = re.match(pattern, symbol)
        
        if match:

                    pattern =  (
                r'^'
                r'([A-Z\s]{4})'  # contract_code
                r'([A-Z]{1})'    # contract_type 
                r'([QSY])'       # contract_delivery_term 
                r'([A-Z])'       # contract_delivery_month_code_from
                r'(\d{2})'       # contract_delivery_day_of_the_month_from
                r'(\d{2})'       # contract_delivery_year_from
                r'[.]'
                r'([A-Z])'       # contract_delivery_month_code_to
                r'(\d{2})'       # contract_delivery_day_of_the_month_to
                r'(\d{2})'       # contract_delivery_year_to
                r'$'                  
            )
            
        
        # QSY pattern
        if symbol[11] == '.':
            pattern =  (
                            r'^'
                            r'([A-Z\s]{4})'  # contract_code
                            r'([A-Z]{1})'    # contract_type 
                            r'([QSY])'       # contract_delivery_term 
                            r'([A-Z])'       # contract_delivery_month_code_from
                            r'(\d{2})'       # contract_delivery_day_of_the_month_from
                            r'(\d{2})'       # contract_delivery_year_from
                            r'[.]'
                            r'([A-Z])'       # contract_delivery_month_code_to
                            r'(\d{2})'       # contract_delivery_day_of_the_month_to
                            r'(\d{2})'       # contract_delivery_year_to
                            r'$'                  
                        )
        
        
        # Spread pattern on month and maybe on product
        if symbol[16] == '-':
            pattern =  ( #! PRODUCT OR TIMESPREAD
                    r'^'
                    r'([A-Z\s]{4})'  # contract_code
                    r'([A-Z]{1})'    # contract_type 
                    r'([M])'         # contract_delivery_term 
                    r'([A-Z])'       # contract_delivery_month_code
                    r'(\d{2})'       # contract_delivery_day_of_the_month
                    r'(\d{2})'       # contract_delivery_year
                    r'([A-Z])'       # contract_delivery_month_code
                    r'(\d{2})'       # contract_delivery_day_of_the_month
                    r'(\d{2})'       # contract_delivery_year
                    r'[-]'           # dash
                    r'([A-Z\s]{4})'  # contract_code
                    r'([A-Z]{1})'    # contract_type 
                    r'([M])'         # contract_delivery_term 
                    r'([A-Z])'       # contract_delivery_month_code
                    r'(\d{2})'       # contract_delivery_day_of_the_month
                    r'(\d{2})'       # contract_delivery_year
                    r'([A-Z])'       # contract_delivery_month_code
                    r'(\d{2})'       # contract_delivery_day_of_the_month
                    r'(\d{2})'       # contract_delivery_year
                    r'$'        # exclamation_mark
        )
        
        # Spread pattern on QSY and maybe on product
        if (symbol[11] == '.' and 
            symbol[17] == '-' and
            symbol[29] == '.'):

            qsy_spread_pattern =  (
                        r'^'
                        r'([A-Z\s]{4})'  # contract_code
                        r'([A-Z]{1})'    # contract_type 
                        r'([QSY])'       # contract_delivery_term 
                        r'([A-Z])'       # contract_delivery_month_code_from
                        r'(\d{2})'       # contract_delivery_day_of_the_month_from
                        r'(\d{2})'       # contract_delivery_year_from
                        r'[.]$'
                        r'([A-Z])'       # contract_delivery_month_code_to
                        r'(\d{2})'       # contract_delivery_day_of_the_month_to
                        r'(\d{2})'       # contract_delivery_year_to
                        r'([-])'         # dash
                        r'([A-Z\s]{4})'
                        r'([A-Z]{1})'    # contract_type 
                        r'([QSY])'       # contract_delivery_term 
                        r'([A-Z])'       # contract_delivery_month_code_from
                        r'(\d{2})'       # contract_delivery_day_of_the_month_from
                        r'(\d{2})'       # contract_delivery_year_from
                        r'[.]$'
                        r'([A-Z])'       # contract_delivery_month_code_to
                        r'(\d{2})'       # contract_delivery_day_of_the_month_to
                        r'(\d{2})'       # contract_delivery_year_to
                        r'$'                  
            )
        
        

            
        # Extract raw string groups from the regex match
        
        contract_code = str(match.group(1)).strip()
        contract_type = str(match.group(2))
        contract_delivery_term = str(match.group(3))
        contract_delivery_month_code = str(match.group(4))
        contract_delivery_day_of_the_month = int(match.group(5))
        contract_delivery_year = int(match.group(6))
        # underscore_char = str(match.group(7))
        # option_contract_block = str(match.group(8))
        option_term = str(match.group(9))
        option_payoff_style = str(match.group(10))
        option_exercise_style = str(match.group(11))    
        option_raw_strike = str(match.group(12))
        option_strike_decimals = int(match.group(13))
        option_expiry_month = int(match.group(14))
        option_expiry_day = int(match.group(15))
        option_expiry_short_year = int(match.group(16))
        option_expiry_year = option_expiry_short_year+2000
        
        self.contract_code = contract_code
        self.contract_type = ICEContractType.from_code(contract_type)
        self.contract_term = ICEContractDeliveryTerm.from_code(contract_delivery_term)
        self.contract_delivery:ICEDeliveryPeriod = ICEDeliveryPeriod_NotSet()
        
        match self.contract_term:
            case ICEContractDeliveryTerm.DAILY:
                contract_delivery_month_calendar_order = ICEMonth.from_code(contract_delivery_month_code).calendar_order
                self.contract_delivery = ICEDeliveryPeriod_Daily(
                                                                    date=date(day=contract_delivery_day_of_the_month, 
                                                                              month=contract_delivery_month_calendar_order, 
                                                                              year=contract_delivery_year
                                                                              )
                )
            case ICEContractDeliveryTerm.MONTH:
                contract_delivery_month_calendar_order = ICEMonth.from_code(contract_delivery_month_code).calendar_order
                self.contract_delivery = ICEDeliveryPeriod_Month(year = contract_delivery_year,
                                                                month = contract_delivery_month_calendar_order)
                
            case ICEContractDeliveryTerm.QUARTER:
                calendar_order = ICEMonth.from_code(contract_delivery_month_code).calendar_order
                x = calendar_order +2
                contract_delivery_month_calendar_order:float = x /3 
                
                if contract_delivery_month_calendar_order not in [1, 2, 3, 4]:
                    raise OptionSymbolDecodeException_NoMatch(symbol=symbol)
                
                self.contract_delivery = ICEDeliveryPeriod_Quarter(year = contract_delivery_year,
                                                                quarter=int(contract_delivery_month_calendar_order) )
            case ICEContractDeliveryTerm.SEASON:
                season = ICESeason.from_code(contract_delivery_month_code)
                self.contract_delivery = ICEDeliveryPeriod_Season(year = contract_delivery_year,
                                                                season = season)
            case ICEContractDeliveryTerm.CALENDAR_YEAR:
                self.contract_delivery = ICEDeliveryPeriod_Year(year = contract_delivery_year)
            case _:
                raise OptionSymbolDecodeException_NoMatch(symbol=symbol)
            
            
            
        self.option_term = ICEOptionTerm.from_code(option_term)
        self.option_payoff_style = ICEPayoffStyle.from_code(option_payoff_style)
        self.option_exercise_style = ICEOptionExerciseStyle.from_code(option_exercise_style)
        self.strike_decimals = option_strike_decimals
        self.strike_price = float(option_raw_strike) / 10 ** int(option_strike_decimals)
        self.exact_expiry_date = date(day=option_expiry_day, month=option_expiry_month, year=option_expiry_year)
        
    # With correct decimals
    def _strike_price_str(self)->str:
        return f'{self.strike_price:.{self.strike_decimals}f}'
        
    def __str__(self) -> str:
        return (    
                    f'symbol: {self.symbol}\n'
                    f'contract_code: {self.contract_code}\n'
                    f'contract_type: {self.contract_type}\n'
                    f'contract_delivery_term: {self.contract_term}\n'
                    f'contract_delivery: {self.contract_delivery}\n'
                    f'option_term: {self.option_term}\n'
                    f'option_payoff_style: {self.option_payoff_style}\n'
                    f'option_exercise_style: {self.option_exercise_style}\n'
                    f'strike_price: {self._strike_price_str()}\n'
                    f'exact_expiry_date: {self.exact_expiry_date}\n'
                    f'ts_event: {self.ts_event}\n'
                    f'rtype: {self.rtype}\n'
                    f'publisher_id: {self.publisher_id}\n'
                    f'instrument_id: {self.instrument_id}\n'
                    f'open_price: {self.open_price}\n'
                    f'high_price: {self.high_price}\n'
                    f'low_price: {self.low_price}\n'
                    f'close_price: {self.close_price}\n'
                    f'volume: {self.volume}\n'
                )