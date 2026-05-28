from abc import ABC, abstractmethod
import re
from typing import Union

from ice_helper.datetime_misc import ICE_ts_event_to_dt
from ice_helper.types import (  ICEContractDeliveryTerm, 
                                ICEContractType, 
                                ICEMonth, 
                                
)
from ice_helper.types_period import (                               
                                        ICEDeliveryPeriod, 
                                        # ICEDeliveryPeriod_Daily, 
                                        ICEDeliveryPeriod_Month, 
                                        # ICEDeliveryPeriod_Quarter, 
                                        ICEDeliveryPeriod_Season, 
                                        # ICEDeliveryPeriod_Year
                                        )



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
                    return ICEFuturesData_QSY(row)
                case 23:
                    return ICEFuturesData_Spread_Month(row)
                case 35:
                    return ICEFuturesData_Spread_QSY(row)
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
        # contract_delivery_day_of_the_month = int(match.group(5))
        contract_delivery_year = int(match.group(6))
        
        self.contract_delivery_period:ICEDeliveryPeriod = ICEDeliveryPeriod_Month(year = contract_delivery_year,
                                                                                month = ICEMonth.from_code(contract_delivery_month_code).calendar_order)
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'contract_code: {self.contract_code}\n'
                f'contract_type: {self.contract_type}\n'
                f'contract_delivery_term: {self.contract_delivery_term}\n'
                f'contract_delivery: {self.contract_delivery_period}\n'
                + super().__str__())

class ICEFuturesData_QSY(ICEFuturesData):
    def __init__(self, row: dict[str, str]):
        # up to here is ensured that 'symbol' is not null
        symbol:str =  row.get('symbol') or ''
        
        pattern =  (
                r'^'
                r'([A-Z\s]{4})'  # contract_code
                r'([A-Z]{1})'    # contract_type 
                r'([QSY])'       # contract_delivery_term 
                r'([A-Z])'       # contract_delivery_month_code_from
                r'(\d{2})'       # contract_delivery_day_of_the_month_from
                r'(\d{2})'       # contract_delivery_year_from
                r'([\.])'        # dot
                r'([A-Z])'       # contract_delivery_month_code_to
                r'(\d{2})'       # contract_delivery_day_of_the_month_to
                r'(\d{2})'       # contract_delivery_year_to
                r'$'        
            )
        
        match = re.match(pattern, symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
        
        self.contract_code = str(match.group(1)).strip()
        self.contract_type = ICEContractType.from_code(str(match.group(2)))
        self.contract_delivery_term = ICEContractDeliveryTerm.from_code(str(match.group(3)))
        
        contract_delivery_month_code_from = str(match.group(4))
        contract_delivery_day_of_the_month_from = int(match.group(5))
        contract_delivery_year_from = int(match.group(6))
        
        contract_delivery_month_code_to = str(match.group(8))
        contract_delivery_day_of_the_month_to = int(match.group(9))
        contract_delivery_year_to = int(match.group(10))
        
        self.contract_delivery_period = ICEDeliveryPeriod_Season.from_values(
                                                                                from_year = contract_delivery_year_from,
                                                                                from_month = ICEMonth.from_code(contract_delivery_month_code_from).calendar_order,
                                                                                from_day = contract_delivery_day_of_the_month_from,
                                                                                to_year = contract_delivery_year_to,
                                                                                to_month = ICEMonth.from_code(contract_delivery_month_code_to).calendar_order, 
                                                                                to_day = contract_delivery_day_of_the_month_to
                                                                            )
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'contract_code: {self.contract_code}\n'
                f'contract_type: {self.contract_type}\n'
                f'contract_delivery_term: {self.contract_delivery_term}\n'
                f'contract_delivery: {self.contract_delivery_period}\n'
                + super().__str__())
        
class ICEFuturesData_Spread_Month(ICEFuturesData):
    def __init__(self, row: dict[str, str]):
        # up to here is ensured that 'symbol' is not null
        symbol:str =  row.get('symbol') or ''
        
        pattern =  (
                r'^'
                r'([A-Z\s]{4})'  # contract_code_from
                r'([A-Z]{1})'    # contract_type _from
                r'([M])'         # contract_delivery_term _from
                r'([A-Z])'       # contract_delivery_month_code_from
                r'(\d{2})'       # contract_delivery_day_of_the_month_from
                r'(\d{2})'       # contract_delivery_year_from
                r'([-])'         # dash
                r'([A-Z\s]{4})'  # contract_code_to
                r'([A-Z]{1})'    # contract_type _to
                r'([M])'         # contract_delivery_term _to
                r'([A-Z])'       # contract_delivery_month_code_to
                r'(\d{2})'       # contract_delivery_day_of_the_month_to
                r'(\d{2})'       # contract_delivery_year_to
                r'$'        
            )
        
        match = re.match(pattern, symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
        
        self.leg1_contract_code = str(match.group(1)).strip()
        self.leg1_contract_type = ICEContractType.from_code(str(match.group(2)))
        self.leg1_contract_delivery_term = ICEContractDeliveryTerm.from_code(str(match.group(3)))
        
        leg1_contract_delivery_month_code = str(match.group(4))
        # leg1_contract_delivery_day_of_the_month = int(match.group(5))
        leg1_contract_delivery_year = int(match.group(6))
        
        self.leg1_contract_delivery_period:ICEDeliveryPeriod = ICEDeliveryPeriod_Month(year = leg1_contract_delivery_year,
                                                                                month = ICEMonth.from_code(leg1_contract_delivery_month_code).calendar_order)
        # self.dash = str(match.group(7))
        self.leg2_contract_code = str(match.group(8)).strip()
        self.leg2_contract_type = ICEContractType.from_code(str(match.group(9)))
        self.leg2_contract_delivery_term = ICEContractDeliveryTerm.from_code(str(match.group(10)))
        
        leg2_contract_delivery_month_code = str(match.group(11))
        # leg2_contract_delivery_day_of_the_month = int(match.group(12))
        leg2_contract_delivery_year = int(match.group(13))
        
        self.leg2_contract_delivery_period:ICEDeliveryPeriod = ICEDeliveryPeriod_Month(year = leg2_contract_delivery_year,
                                                                                month = ICEMonth.from_code(leg2_contract_delivery_month_code).calendar_order)
        
        if self.leg1_contract_code != self.leg2_contract_code:
            raise ValueError('leg1_contract_code != leg2_contract_code')
            
        if self.leg1_contract_type != self.leg2_contract_type:
            raise ValueError('leg1_contract_type != leg2_contract_type')
                             
        if self.leg1_contract_delivery_term != self.leg2_contract_delivery_term:
            raise ValueError('leg1_contract_delivery_term != leg2_contract_delivery_term')
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'contract_code: {self.leg1_contract_code}\n'
                f'contract_type: {self.leg1_contract_type}\n'
                f'contract_delivery_term: {self.leg1_contract_delivery_term}\n'
                f'contract_delivery: {self.leg1_contract_delivery_period}\n'
                + super().__str__())
        
class ICEFuturesData_Spread_QSY(ICEFuturesData):
    def __init__(self, row: dict[str, str]):
        # up to here is ensured that 'symbol' is not null
        symbol:str =  row.get('symbol') or ''
        
        pattern =  (
                r'^'
                r'([A-Z\s]{4})'  # contract_code
                r'([A-Z]{1})'    # contract_type 
                r'([QSY])'       # contract_delivery_term 
                r'([A-Z])'       # contract_delivery_month_code_from
                r'(\d{2})'       # contract_delivery_day_of_the_month_from
                r'(\d{2})'       # contract_delivery_year_from
                r'([\.])'        # dot
                r'([A-Z])'       # contract_delivery_month_code_to
                r'(\d{2})'       # contract_delivery_day_of_the_month_to
                r'(\d{2})'       # contract_delivery_year_to
                r'([-])'         # dash
                r'([A-Z\s]{4})'  # contract_code
                r'([A-Z]{1})'    # contract_type 
                r'([QSY])'       # contract_delivery_term 
                r'([A-Z])'       # contract_delivery_month_code_from
                r'(\d{2})'       # contract_delivery_day_of_the_month_from
                r'(\d{2})'       # contract_delivery_year_from
                r'([\.])'        # dot
                r'([A-Z])'       # contract_delivery_month_code_to
                r'(\d{2})'       # contract_delivery_day_of_the_month_to
                r'(\d{2})'       # contract_delivery_year_to
                r'$'        
            )
        
        match = re.match(pattern, symbol)
        
        if not match:
            raise ValueError('symbol does not match pattern')
        
        self.leg1_contract_code = str(match.group(1)).strip()
        self.leg1_contract_type = ICEContractType.from_code(str(match.group(2)))
        self.leg1_contract_delivery_term = ICEContractDeliveryTerm.from_code(str(match.group(3)))
        
        leg1_contract_delivery_month_code_from = str(match.group(4))
        leg1_contract_delivery_day_of_the_month_from = int(match.group(5))
        leg1_contract_delivery_year_from = int(match.group(6))
        # leg1_dot = str(match.group(7))
        leg1_contract_delivery_month_code_to = str(match.group(8))
        leg1_contract_delivery_day_of_the_month_to = int(match.group(9))
        leg1_contract_delivery_year_to = int(match.group(10))
        
        self.leg1_contract_delivery_period = ICEDeliveryPeriod_Season.from_values(
                                                                                        from_year = leg1_contract_delivery_year_from,
                                                                                        from_month = ICEMonth.from_code(leg1_contract_delivery_month_code_from).calendar_order,
                                                                                        from_day = leg1_contract_delivery_day_of_the_month_from,
                                                                                        to_year = leg1_contract_delivery_year_to,
                                                                                        to_month = ICEMonth.from_code(leg1_contract_delivery_month_code_to).calendar_order, 
                                                                                        to_day = leg1_contract_delivery_day_of_the_month_to
                                                                                    )
        # self.dash = str(match.group(11))
        self.leg2_contract_code = str(match.group(12)).strip()
        self.leg2_contract_type = ICEContractType.from_code(str(match.group(13)))
        self.leg2_contract_delivery_term = ICEContractDeliveryTerm.from_code(str(match.group(14)))
        
        leg2_contract_delivery_month_code_from = str(match.group(15))
        leg2_contract_delivery_day_of_the_month_from = int(match.group(16))
        leg2_contract_delivery_year_from = int(match.group(17))
        # from__dot = str(match.group(18))
        leg2_contract_delivery_month_code_to = str(match.group(19))
        leg2_contract_delivery_day_of_the_month_to = int(match.group(20))
        leg2_contract_delivery_year_to = int(match.group(21))
        
        self.leg2_contract_delivery_period = ICEDeliveryPeriod_Season.from_values(
                                                                                        from_year = leg2_contract_delivery_year_from,
                                                                                        from_month = ICEMonth.from_code(leg2_contract_delivery_month_code_from).calendar_order,
                                                                                        from_day = leg2_contract_delivery_day_of_the_month_from,
                                                                                        to_year = leg2_contract_delivery_year_to,
                                                                                        to_month = ICEMonth.from_code(leg2_contract_delivery_month_code_to).calendar_order, 
                                                                                        to_day = leg2_contract_delivery_day_of_the_month_to
                                                                                    )
        
        if self.leg1_contract_code != self.leg2_contract_code:
            raise ValueError('leg1_contract_code != leg2_contract_code')
            
        if self.leg1_contract_type != self.leg2_contract_type:
            raise ValueError('leg1_contract_type != leg2_contract_type')
                             
        if self.leg1_contract_delivery_term != self.leg2_contract_delivery_term:
            raise ValueError('leg1_contract_delivery_term != leg2_contract_delivery_term')
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'contract_code: {self.leg1_contract_code}\n'
                f'contract_type: {self.leg1_contract_type}\n'
                f'contract_delivery_term: {self.leg1_contract_delivery_term}\n'
                f'contract_delivery: {self.leg1_contract_delivery_period}\n'
                + super().__str__())

class ICEFuturesData_Unencoded(ICEFuturesData):
    def __init__(self, row: dict[str, str]):
        self.symbol = row.get('symbol')
        
        super().__init__(row)
        
    def __str__(self) -> str:
        return (f'symbol: {self.symbol}\n' 
                + super().__str__())





ICEFuturesDataUnion = Union[
                            ICEFuturesData_Unencoded, 
                            ICEFuturesData_Month, 
                            ICEFuturesData_QSY, 
                            ICEFuturesData_Spread_Month, 
                            ICEFuturesData_Spread_QSY,
                            ]


