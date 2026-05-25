from datetime import date
from abc import ABC, abstractmethod
from typing import Union
from ice_helper.types import ICESeason




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
                            ICEDeliveryPeriod_NotSet,   
                            ICEDeliveryPeriod_Daily, 
                            ICEDeliveryPeriod_Month,
                            ICEDeliveryPeriod_Quarter,
                            ICEDeliveryPeriod_Season,
                            ICEDeliveryPeriod_Year 
                        ]