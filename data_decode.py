
from abc import ABC, abstractmethod
import re
from datetime import date

from ice_helper.datetime_misc import ICE_ts_event_to_dt
from ice_helper.delivery_period_specific_types import (

    ICEDeliveryPeriod_Daily,
    ICEDeliveryPeriod_Month,
    ICEDeliveryPeriod_Quarter,
    ICEDeliveryPeriod_Season,
    ICEDeliveryPeriod_Year,
    ICEDeliveryPeriod,
    ICEDeliveryPeriod_NotSet
)

from ice_helper.types import (
    ICEContractType,
    ICEContractDeliveryTerm,
    ICEOptionTerm,
    ICEPayoffStyle,
    ICEOptionExerciseStyle,
    ICEMonth,
    ICESeason  
)

class OptionSymbolDecodeException(Exception, ABC):
    def __init__(self, symbol: str)-> None:
        self.symbol = symbol
        super().__init__(self.symbol)
    
    @property
    @abstractmethod
    def message(self) -> str:
        pass
    

class OptionSymbolDecodeException_NoMatch(OptionSymbolDecodeException):
    'Raised when tree parameters violate no-arbitrage bounds (e.g., d >= e^(r*dt) or u <= e^(r*dt))'
    def __init__(self, symbol: str)-> None:
        super().__init__(symbol=symbol)
        
    @property
    def message(self) -> str:
        return 'No match found for option symbol: {symbol}'

class ICEOptionData:
    def __init__(self, row: dict[str, str]):
        ts_event_dt = ICE_ts_event_to_dt(row.get('ts_event'))
        rtype = row.get('rtype')
        publisher_id = row.get('publisher_id')
        instrument_id = row.get('instrument_id')
        open_price = row.get('open')
        high_price = row.get('high')
        low_price = row.get('low')
        close_price = row.get('close')
        volume = row.get('volume')
        symbol:str = row.get('symbol')
        self._decode_ice_symbol_option(symbol)
        
    
    def _decode_ice_symbol_option(self, symbol :str)->None:
        
        # TFO FMK0026_OMPE0000038002042426
        pattern = (r'^([A-Z\s]{4})' # contract_code
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
                    r'(\d{2})$'      # option_expiry_short_year
                    )
        
        match = re.match(pattern, symbol)
        

        
        if not match:
            raise OptionSymbolDecodeException_NoMatch(symbol=symbol)
            
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
                    f'contract_code: {self.contract_code}\n'
                    f'contract_type: {self.contract_type}\n'
                    f'contract_delivery_term: {self.contract_term}\n'
                    f'contract_delivery: {self.contract_delivery}\n'
                    f'option_term: {self.option_term}\n'
                    f'option_payoff_style: {self.option_payoff_style}\n'
                    f'option_exercise_style: {self.option_exercise_style}\n'
                    f'strike_price: {self._strike_price_str()}\n'
                    f'exact_expiry_date: {self.exact_expiry_date}\n'
                )
    
    
        
        
        





# --- Test Execution ---
# TFO FMK0026_OMPE0000038002042426
raw_string = 'TFO FMM0026_OMPE0000037002052726'
data = ICEOptionData(raw_string)
print(data)
