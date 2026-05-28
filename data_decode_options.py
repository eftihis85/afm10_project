
from abc import ABC, abstractmethod
import re
from datetime import date
from typing import Union

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



class ICEOptionsData(ABC):
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
                    return ICEOptionsData_Month(row)
                # case 17:
                #     # QSY
                #     return ICEFuturesData_QSY(row)
                # case 23:
                #     return ICEFuturesData_Spread_Month(row)
                # case 35:
                #     return ICEFuturesData_Spread_QSY(row)
                case _:
                    return ICEOptionsData_Unencoded(row)
        except:
            return ICEOptionsData_Unencoded(row)
                
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

class ICEOptionsData_Month(ICEOptionsData):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol')
        
        if not self.symbol:
            raise ValueError('symbol is None')
        
        self._decode_ice_symbol(symbol=self.symbol)
        
    
    def _decode_ice_symbol(self, symbol :str)->None:
        
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
        
        match = re.match(pattern, symbol)
        

        
        if not match:
            raise ValueError('symbol does not match pattern')
            
        # Extract raw string groups from the regex match
        
        contract_code = str(match.group(1)).strip()
        contract_type = str(match.group(2))
        contract_delivery_term = str(match.group(3))
        contract_delivery_month_code = str(match.group(4))
        # contract_delivery_day_of_the_month = int(match.group(5))
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
        self.contract_delivery_period = ICEDeliveryPeriod_Month(year = contract_delivery_year,
                                                                month = ICEMonth.from_code(contract_delivery_month_code).calendar_order)
                                            
            
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
                    f'contract_delivery: {self.contract_delivery_period}\n'
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
    
    
        
        
        
class ICEOptionsData_Unencoded(ICEOptionsData):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol')
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'symbol: {self.symbol}\n' 
                + super().__str__())









ICEOptionsDataUnion = Union[
                            ICEOptionsData_Unencoded, 
                            ICEOptionsData_Month, 
                            ]