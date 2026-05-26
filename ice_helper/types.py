# from  enum_abstraction import ICECodeEnum, FromCode
from abc import ABC, abstractmethod
from datetime import date
from typing import Union

from ice_helper.enum_abstraction import ICECodeEnum, FromCode

__all__ = [
    "ICEContractType",
    "ICEContractDeliveryTerm",
    "ICEOptionTerm",
    "ICEPayoffStyle",
    "ICEOptionExerciseStyle",
    "ICEMonth",
    "ICESeason"
]


class ICEContractType(FromCode, ICECodeEnum):
    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    FUTURES = ('F', 'Futures')
    OTC_SWAP_FLOW = ('S', 'OTC Swap– Flow')
    OTC_SWAP_LOTS = ('L', 'OTC Swap – Lots')
    LARGE_SIZED_FLOW = ('J', 'Large Sized Flow')
    OTC_PHYSICAL_FORWARDS = ('P', 'OTC Physical Forwards')
    INDEX = ('I', 'Index')
    COMMON_STOCK = ('E', 'Common Stock')
    IRS_FUTURES = ('R', 'IRS - Futures')
    CDS_FUTURES = ('B', 'CDS - Futures')


class ICEContractDeliveryTerm(FromCode, ICECodeEnum):
    def __init__(self, code: str, description: str):
        self.code = code
        self.description = description

    # Defining enum members mapping to their official descriptions
    DAILY = ('D', 'Day (Daily)')
    WEEK = ('W', 'Week')
    BALANCE_OF_MONTH = ('B', 'Balance of Month')
    MONTH = ('M', 'Month')
    QUARTER = ('Q', 'Quarter')
    SEASON = ('S', 'Season (Futures Only)')
    BALANCE_OF_WEEK = ('L', 'Balance of Week')
    CALENDAR_YEAR = ('Y', 'Calendar Year')
    VARIABLE = ('V', 'Variable (e.g. Seasons OTC)')
    CUSTOM = ('X', 'Custom')
    SAME_DAY = ('A', 'Same Day (for Same Day Option/SDO)')
    NEXT_DAY = ('N', 'Next Day (for Next Day Option/NDO)')
    WEEKLY_NTH = ('T', 'Weekly (2nd, 3rd, 4th, Next)')
    PACK = ('P', 'Pack (four consecutive quarter ending months)')
    BUNDLE = ('U', 'Bundle (n-number of consecutive Packs)')
    IRS_CDS = ('E', 'IRS and CDS tenor')
    BASKET = ('K', 'Basket (n- number of months in single product)')
    SPECIAL_GAS_EMISSIONS = ('C', 'Saturday, Sunday, DA, Futures Today and Yesterday contracts')
    TOM_TOMORROW = ('G', 'Tom - The tomorrow (T+1) contract')
    SPOT = ('J', 'Spot - The spot (T+2) contract')
    HOURLY = ('H', 'Hourly')
    
    def get_ice_delivery_period(self, contract_delivery_month_code: str, 
                                contract_delivery_day_of_the_month: int, 
                                contract_delivery_year: int) -> ICEDeliveryPeriod:
        match self:
            case ICEContractDeliveryTerm.DAILY:
                month_index = ICEMonth.from_code(contract_delivery_month_code).calendar_order
                return ICEDeliveryPeriod_Daily(
                                                                    date=date(day=contract_delivery_day_of_the_month, 
                                                                            month=month_index, 
                                                                            year=contract_delivery_year
                                                                            )
                )
            case ICEContractDeliveryTerm.MONTH:
                month_index = ICEMonth.from_code(contract_delivery_month_code).calendar_order
                return ICEDeliveryPeriod_Month(year = contract_delivery_year,
                                                                month = month_index)
                
            case ICEContractDeliveryTerm.QUARTER:
                calendar_order = ICEMonth.from_code(contract_delivery_month_code).calendar_order
                x = calendar_order +2
                quarter_index:float = x /3 
                
                if quarter_index not in [1, 2, 3, 4]:
                    raise ValueError('invalid quarter code')
                
                return ICEDeliveryPeriod_Quarter(year = contract_delivery_year,
                                                                quarter=int(quarter_index) )
            case ICEContractDeliveryTerm.SEASON:
                season = ICESeason.from_code(contract_delivery_month_code)
                return ICEDeliveryPeriod_Season(year = contract_delivery_year,
                                                                season = season)
            case ICEContractDeliveryTerm.CALENDAR_YEAR:
                return ICEDeliveryPeriod_Year(year = contract_delivery_year)
            case _:
                raise ValueError('Invalid delivery period')
                return 


# OPTION TYPE
class ICEOptionTerm(FromCode, ICECodeEnum): 
    def __init__(self, code: str, description: str):
        self.code = code
        self.description = description

    MONTHLY = ('M', 'Monthly')
    WEEKLY = ('W', 'Weekly')
    DAILY = ('D', 'Daily')
    SAME_DAY = ('A', 'Same Day Option')
    NEXT_DAY = ('N', 'Next Day Option')
    QUARTER = ('Q', 'Quarter')
    VARIABLE_SEASON = ('V', 'Variable Season')
    CALENDAR_YEAR = ('Y', 'Calendar Year')

class ICEPayoffStyle(FromCode, ICECodeEnum):
    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    AMERICAN = ('P', 'Put')
    EUROPEAN = ('C', 'Call')

class ICEOptionExerciseStyle(FromCode, ICECodeEnum):
    def __init__(self, code: str, description: str) -> None:
        self.code = code
        self.description = description

    AMERICAN = ('A', 'American')
    EUROPEAN = ('E', 'European')
    ASIAN = ('Z', 'Asian')
    ONE_TIME = ('U', 'One Time')


class ICEMonth(FromCode, ICECodeEnum):
    JANUARY = ('F', 'January', 1)
    FEBRUARY = ('G', 'February', 2)
    MARCH = ('H', 'March', 3)
    APRIL = ('J', 'April', 4)
    MAY = ('K', 'May', 5)
    JUNE = ('M', 'June', 6)
    JULY = ('N', 'July', 7)
    AUGUST = ('Q', 'August', 8)
    SEPTEMBER = ('U', 'September', 9)
    OCTOBER = ('V', 'October', 10)
    NOVEMBER = ('X', 'November', 11)
    DECEMBER = ('Z', 'December', 12)

    def __init__(self, code:str, description:str, calendar_order:int):
        self.code = code
        self.description = description
        self.calendar_order = calendar_order

class ICESeason(FromCode, ICECodeEnum):
    SUMMER = ('J', 'Summer')
    WINTER = ('V', 'Winter')

    def __init__(self, code:str, description:str):
        self.code = code
        self.description = description



class ICEDeliveryPeriodABC(ABC):
    def __init__(self):
        pass
    
    @abstractmethod
    def __str__(self) -> str:
        pass

class ICEDeliveryPeriod_NotSet(ICEDeliveryPeriodABC):
    def __init__(self):
        pass
            
    def __str__(self) -> str:
        return 'Not set!'
        
class ICEDeliveryPeriod_Daily(ICEDeliveryPeriodABC):
    def __init__(self, date: date):
        self.date = date
            
    def __str__(self) -> str:
        return self.date.strftime('%Y-%m-%d')

class ICEDeliveryPeriod_Month(ICEDeliveryPeriodABC):
    def __init__(self, month: int, year: int):
        self.month = month
        self.year = year

    def __str__(self) -> str:
        return f'{self.year}-{self.month:02d}'
    
class ICEDeliveryPeriod_Quarter(ICEDeliveryPeriodABC):
    def __init__(self, quarter: int, year: int):
        self._quarter = quarter
        self.year = year

    @property
    def quarter(self) -> int:
        return self._quarter

    @quarter.setter
    def quarter(self, value: int):
        if value not in [1, 2, 3, 4]:
            raise ValueError('Quarter must be between 1 and 4')
        self._quarter = value


    def __str__(self) -> str:
        return f'{self.year}-Q{self.quarter}'
    
class ICEDeliveryPeriod_Season(ICEDeliveryPeriodABC):
    def __init__(self, season: ICESeason, year: int):
        self.season = season.description
        self.year = year

    def __str__(self) -> str:
        return f'{self.year}-{self.season}'
    
class ICEDeliveryPeriod_Year(ICEDeliveryPeriodABC):
    def __init__(self, year: int):
        self.year = year

    def __str__(self) -> str:
        return f'{self.year}'
    
ICEDeliveryPeriod = Union[
                            ICEDeliveryPeriod_Daily, 
                            ICEDeliveryPeriod_Month,
                            ICEDeliveryPeriod_Quarter,
                            ICEDeliveryPeriod_Season,
                            ICEDeliveryPeriod_Year 
                        ]