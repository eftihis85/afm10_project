
from abc import ABC, abstractmethod
import re
from datetime import date, datetime
from typing import Union

from ice_data_common_decode import IceDataCommon
from ice_helper.datetime_misc import ICE_ts_event_to_dt

from ice_helper.types import (
    ICEContractType,
    ICEContractDeliveryTerm,
    ICEMonth,
    ICEOptionTerm,
    ICEPayoffStyle,
    ICEOptionExerciseStyle,
)

from ice_helper.types_period import (                               
                                        ICEDeliveryPeriod_Month, 
                                        # ICEDeliveryPeriod, 
                                        # ICEDeliveryPeriod_Daily, 
                                        # ICEDeliveryPeriod_Quarter, 
                                        # ICEDeliveryPeriod_Season, 
                                        # ICEDeliveryPeriod_Year
                                        )



class ICEOptionsDataABC(IceDataCommon, ABC):
    @classmethod
    def decode_csv_row(cls, row: dict[str, str])-> ICEOptionsDataUnion:
        try:
            symbol = row.get('symbol')
            
            if not symbol:
                raise ValueError('symbol is None')
            
            symbol_len = len(symbol)

            match symbol_len:
                case 32:
                    # Month
                    try:
                        return ICEOptionsData_Month(row)
                    except:
                        return ICEOptionsData_Undencoded_Month(row)
                case 17:
                    return ICEOptionsData_Unencoded_RecordsWithId(row)
                case 35:
                    return ICEOptionsData_Unencoded_QSY_TruncationIssue(row)
                case 38:
                    return ICEOptionsData_QSY(row)
                case _:
                    return ICEOptionsData_Unencoded_Unknown(row)
        except:
            return ICEOptionsData_Unencoded_Unknown(row)
                
    def __init__(self, row: dict[str, str]):
        super().__init__(row)

        
        
           
    @abstractmethod
    def __str__(self) -> str:
        return (    
                    f'ts_event: {self.ts_event_date_only_str}\n'
                    f'rtype: {self.rtype}\n'
                    f'publisher_id: {self.publisher_id}\n'
                    f'instrument_id: {self.instrument_id}\n'
                    f'open_price: {self.open}\n'
                    f'high_price: {self.high}\n'
                    f'low_price: {self.low}\n'
                    f'close_price: {self.close}\n'
                    f'volume: {self.volume}\n'
                )

class ICEOptionsData_Month(ICEOptionsDataABC):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')
                
    
        # TFO FMK0026_OMPE0000038002042426
        pattern = (r'^'
                    r'([A-Z\s]{4})'  # contract_code
                    r'([A-Z]{1})'    # contract_type 
                    r'([A-Z]{1})'    # contract_delivery_term 
                    r'([A-Z])'       # contract_delivery_month_code
                    r'(\d{2})'       # contract_delivery_day_of_the_month
                    r'(\d{2})'       # contract_delivery_year
                    # The presence of an underscore represents additional information related to the base
                    # contract that fundamentally changes the meaning of the base contract; for example
                    # options. 
                    r'([_])'         #underscore_char
                    r'([O])'         # option_contract_block
                    r'([M])'         # option_term
                    r'([PC])'        # option_payoff_style
                    r'([E])'         # option_exercise_style
                    r'(\d{9})'       # option_raw_strike
                    r'(\d{1})'       # option_strike_decimals
                    r'(\d{2})'       # option_expiry_month
                    r'(\d{2})'       # option_expiry_day
                    r'(\d{2})'       # option_expiry_short_year
                    r'$'      
                    )
        
        match = re.match(pattern, self.symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
            
        # Extract raw string groups from the regex match
        
        contract_code = str(match.group(1)).strip()
        contract_type = str(match.group(2))
        contract_delivery_term = str(match.group(3))
        contract_delivery_month_code = str(match.group(4))
        # contract_delivery_day_of_the_month = int(match.group(5))
        contract_delivery_year = int(match.group(6)) +2000
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
        self.contract_delivery_period = ICEDeliveryPeriod_Month(year = contract_delivery_year,
                                                                month = ICEMonth.from_code(contract_delivery_month_code).calendar_order)
                                            
            
        self.option_term = ICEOptionTerm.from_code(option_term)
        self.option_payoff_style = ICEPayoffStyle.from_code(option_payoff_style)
        self.option_exercise_style = ICEOptionExerciseStyle.from_code(option_exercise_style)
        self.option_strike_decimals = option_strike_decimals
        self.option_strike_price = float(option_raw_strike) / 10 ** int(option_strike_decimals)
        self.option_expiry_date = datetime(day=option_expiry_day, month=option_expiry_month, year=option_expiry_year)
        
        super().__init__(row)
        
    # With correct decimals
    def _strike_price_str(self)->str:
        return f'{self.option_strike_price:.{self.option_strike_decimals}f}'
        
    def __str__(self) -> str:
        return (    
                    f'symbol: {self.symbol}\n'
                    f'contract_code: {self.contract_code}\n'
                    f'contract_type: {self.contract_type}\n'
                    f'contract_delivery_term: {self.contract_term}\n'
                    f'contract_delivery: {self.contract_delivery_period}\n'
                    f'option_term: {self.option_term}\n'
                    f'option_payoff_style: {self.option_payoff_style}\n'
                    f'option_exercise_style: {self.option_exercise_style}\n'
                    f'strike_price: {self._strike_price_str()}\n'
                    f'option_expiry_date: {self.option_expiry_date}\n'
                    f'ts_event: {self.ts_event_date_only_str}\n'
                    f'rtype: {self.rtype}\n'
                    f'publisher_id: {self.publisher_id}\n'
                    f'instrument_id: {self.instrument_id}\n'
                    f'open_price: {self.open}\n'
                    f'high_price: {self.high}\n'
                    f'low_price: {self.low}\n'
                    f'close_price: {self.close}\n'
                    f'volume: {self.volume}\n'
                )

class ICEOptionsData_QSY(ICEOptionsDataABC):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')
                
    
        # TFO FSM0026.U0026_OSPE0000025002052
        pattern = (r'^'
                    r'([A-Z\s]{4})'  # contract_code
                    r'([A-Z]{1})'    # contract_type 
                    r'([QSY]{1})'    # contract_delivery_term 
                    r'([A-Z])'       # contract_delivery_month_code_from
                    r'(\d{2})'       # contract_delivery_day_of_the_month_from
                    r'(\d{2})'       # contract_delivery_year_from
                    r'(\.)'          # dot 
                    r'([A-Z])'       # contract_delivery_month_code_to
                    r'(\d{2})'       # contract_delivery_day_of_the_month_to
                    r'(\d{2})'       # contract_delivery_year_to
                    r'([_])'         #underscore_char   
                    r'([O])'         # option_contract_block
                    r'([QSY]{1})'    # option_term 
                    r'([PC])'        # option_payoff_style
                    r'([E])'         # option_exercise_style
                    r'(\d{9})'       # option_raw_strike
                    r'(\d{1})'       # option_strike_decimals
                    r'(\d{2})'       # option_expiry_month
                    r'(\d{2})'       # option_expiry_day
                    r'(\d{2})'       # option_expiry_short_year
                    r'$'      
                    )
    
        
        match = re.match(pattern, self.symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
        
        # Extract raw string groups from the regex match
        
        contract_code = str(match.group(1)).strip()
        contract_type = str(match.group(2))
        contract_delivery_term = str(match.group(3))
        contract_delivery_month_code_from = str(match.group(4))
        # contract_delivery_day_of_the_month_from = int(match.group(5))
        contract_delivery_year_from = int(match.group(6))+2000
        # dot = str(match.group(7))
        contract_delivery_month_code_to = str(match.group(8))
        # contract_delivery_day_of_the_month_to = int(match.group(9))
        contract_delivery_year_to = int(match.group(10)) +2000
        # underscore_char = str(match.group(11))
        # option_contract_block = str(match.group(12))
        option_term = str(match.group(13))
        option_payoff_style = str(match.group(14))
        option_exercise_style = str(match.group(15))    
        option_raw_strike = str(match.group(16))
        option_strike_decimals = int(match.group(17))
        option_expiry_month = int(match.group(18))
        option_expiry_day = int(match.group(19))
        option_expiry_short_year = int(match.group(20))
        option_expiry_year = option_expiry_short_year+2000
        
        self.contract_code = contract_code
        self.contract_type = ICEContractType.from_code(contract_type)
        self.contract_term = ICEContractDeliveryTerm.from_code(contract_delivery_term)
        self.contract_delivery_period_from = ICEDeliveryPeriod_Month(year = contract_delivery_year_from,
                                                                month = ICEMonth.from_code(contract_delivery_month_code_from).calendar_order)
        self.contract_delivery_period_to = ICEDeliveryPeriod_Month(year = contract_delivery_year_to,
                                                                month = ICEMonth.from_code(contract_delivery_month_code_to).calendar_order)
                                            
            
        self.option_term = ICEOptionTerm.from_code(option_term)
        self.option_payoff_style = ICEPayoffStyle.from_code(option_payoff_style)
        self.option_exercise_style = ICEOptionExerciseStyle.from_code(option_exercise_style)
        self.strike_decimals = option_strike_decimals
        self.strike_price = float(option_raw_strike) / 10 ** int(option_strike_decimals)
        self.option_expiry_date = date(day=option_expiry_day, month=option_expiry_month, year=option_expiry_year)
        
        super().__init__(row)

        
    # With correct decimals
    def _strike_price_str(self)->str:
        return f'{self.strike_price:.{self.strike_decimals}f}'
        
    def __str__(self) -> str:
        return (    
                    f'symbol: {self.symbol}\n'
                    f'contract_code: {self.contract_code}\n'
                    f'contract_type: {self.contract_type}\n'
                    f'contract_delivery_term: {self.contract_term}\n'
                    f'contract_delivery: {self.contract_delivery_period_from}\n'
                    f'option_term: {self.option_term}\n'
                    f'option_payoff_style: {self.option_payoff_style}\n'
                    f'option_exercise_style: {self.option_exercise_style}\n'
                    f'strike_price: {self._strike_price_str()}\n'
                    f'option_expiry_date: {self.option_expiry_date}\n'
                    f'ts_event: {self.ts_event_date_only_str}\n'
                    f'rtype: {self.rtype}\n'
                    f'publisher_id: {self.publisher_id}\n'
                    f'instrument_id: {self.instrument_id}\n'
                    f'open_price: {self.open}\n'
                    f'high_price: {self.high}\n'
                    f'low_price: {self.low}\n'
                    f'close_price: {self.close}\n'
                    f'volume: {self.volume}\n'
                )
    
class ICEOptionsData_UnencodedABC(ICEOptionsDataABC, ABC):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'symbol: {self.symbol}\n' 
                + super().__str__())
        
class ICEOptionsData_Unencoded_Unknown(ICEOptionsData_UnencodedABC):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'symbol: {self.symbol}\n' 
                + super().__str__())


class ICEOptionsData_Unencoded_QSY_TruncationIssue(ICEOptionsData_UnencodedABC):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')
    
        # TFO FSM0026.U0026_OSPE0000025002052
        pattern = (r'^'
                    r'([A-Z\s]{4})'  # contract_code
                    r'([A-Z]{1})'    # contract_type 
                    r'([QSY]{1})'    # contract_delivery_term 
                    r'([A-Z])'       # contract_delivery_month_code_from
                    r'(\d{2})'       # contract_delivery_day_of_the_month_from
                    r'(\d{2})'       # contract_delivery_year_from
                    r'(\.)'          # dot 
                    r'([A-Z])'       # contract_delivery_month_code_to
                    r'(\d{2})'       # contract_delivery_day_of_the_month_to
                    r'(\d{2})'       # contract_delivery_year_to
                    r'([_])'         #underscore_char   
                    r'([O])'         # option_contract_block
                    r'([QSY]{1})'    # option_term 
                    r'([PC])'        # option_payoff_style
                    r'([E])'         # option_exercise_style
                    r'(\d{9})'       # option_raw_strike
                    r'(\d{1})'       # option_strike_decimals
                    r'(\d{2})'       # option_expiry_month
                    r'(\d{1})'       # option_expiry_day_truncated
                    # r'(\d{2})'       # option_expiry_short_year
                    r'$'      
                    )
        
        match = re.match(pattern, self.symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
        
        # Extract raw string groups from the regex match
        
        contract_code = str(match.group(1)).strip()
        contract_type = str(match.group(2))
        contract_delivery_term = str(match.group(3))
        contract_delivery_month_code_from = str(match.group(4))
        # contract_delivery_day_of_the_month_from = int(match.group(5))
        contract_delivery_year_from = int(match.group(6)) +2000
        # dot = str(match.group(7))
        contract_delivery_month_code_to = str(match.group(8))
        # contract_delivery_day_of_the_month_to = int(match.group(9))
        contract_delivery_year_to = int(match.group(10))+2000
        # underscore_char = str(match.group(11))
        # option_contract_block = str(match.group(12))
        option_term = str(match.group(13))
        option_payoff_style = str(match.group(14))
        option_exercise_style = str(match.group(15))    
        option_raw_strike = str(match.group(16))
        option_strike_decimals = int(match.group(17))
        # option_expiry_month = int(match.group(18))
        # option_expiry_day_truncated = int(match.group(19))
        
        self.contract_code = contract_code
        self.contract_type = ICEContractType.from_code(contract_type)
        self.contract_term = ICEContractDeliveryTerm.from_code(contract_delivery_term)
        self.contract_delivery_period_from = ICEDeliveryPeriod_Month(year = contract_delivery_year_from,
                                                                month = ICEMonth.from_code(contract_delivery_month_code_from).calendar_order)
                                            
        self.contract_delivery_period_to = ICEDeliveryPeriod_Month(year = contract_delivery_year_to,
                                                                month = ICEMonth.from_code(contract_delivery_month_code_to).calendar_order)
                                            
            
        self.option_term = ICEOptionTerm.from_code(option_term)
        self.option_payoff_style = ICEPayoffStyle.from_code(option_payoff_style)
        self.option_exercise_style = ICEOptionExerciseStyle.from_code(option_exercise_style)
        self.strike_decimals = option_strike_decimals
        self.strike_price = float(option_raw_strike) / 10 ** int(option_strike_decimals)
        # self.option_expiry_date = date(day=option_expiry_day_truncated, month=option_expiry_month, year=option_expiry_year)
        
        super().__init__(row)
        
    # With correct decimals
    def _strike_price_str(self)->str:
        return f'{self.strike_price:.{self.strike_decimals}f}'
        
    def __str__(self) -> str:
        return (    
                    f'symbol: {self.symbol}\n'
                    f'contract_code: {self.contract_code}\n'
                    f'contract_type: {self.contract_type}\n'
                    f'contract_delivery_term: {self.contract_term}\n'
                    f'contract_delivery_from: {self.contract_delivery_period_from}\n'
                    f'contract_delivery_to: {self.contract_delivery_period_to}\n'
                    f'option_term: {self.option_term}\n'
                    f'option_payoff_style: {self.option_payoff_style}\n'
                    f'option_exercise_style: {self.option_exercise_style}\n'
                    f'strike_price: {self._strike_price_str()}\n'
                    f'option_expiry_date: <TRUNCATED>\n'
                    f'ts_event: {self.ts_event_date_only_str}\n'
                    f'rtype: {self.rtype}\n'
                    f'publisher_id: {self.publisher_id}\n'
                    f'instrument_id: {self.instrument_id}\n'
                    f'open_price: {self.open}\n'
                    f'high_price: {self.high}\n'
                    f'low_price: {self.low}\n'
                    f'close_price: {self.close}\n'
                    f'volume: {self.volume}\n'
                )

class ICEOptionsData_Undencoded_Month(ICEOptionsData_UnencodedABC):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'symbol: {self.symbol}\n' 
                + super().__str__())

class ICEOptionsData_Unencoded_RecordsWithId(ICEOptionsData_UnencodedABC):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol') or ''
        
        if len(self.symbol) == 0:
            raise ValueError('symbol is None')
        
        pattern = ( 
                        r'^'
                        r'([A-Z\s]{4})'                                                                                             # contract_code
                        r'( {2}\d| \d{2}|\d{3})'                                                                                  # contract_type 
                        r'( {9}\d| {8}\d{2}| {7}\d{3}| {6}\d{4}| {5}\d{5}| {4}\d{6}| {3}\d{7}| {2}\d{8}| {1}\d{9}|\d{10})'        # contract_type 
                        r'$'      
                    )
        
        match = re.match(pattern, self.symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
        
        self.contract_code = str(match.group(1)).strip()
        self.strategy_code = int(match.group(2))
        self.market_id = int(match.group(3))
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'symbol: {self.symbol}\n' 
                + f'contract_code: {self.contract_code}\n'
                + f'strategy_code: {self.strategy_code}\n'
                + f'market_id: {self.market_id}\n'
                + super().__str__())

ICEOptionsDataUnion = Union[
                            ICEOptionsData_Month, 
                            ICEOptionsData_QSY,
                            ICEOptionsData_Undencoded_Month,
                            ICEOptionsData_Unencoded_RecordsWithId,
                            ICEOptionsData_Unencoded_QSY_TruncationIssue,
                            ICEOptionsData_Unencoded_Unknown,
                            ]