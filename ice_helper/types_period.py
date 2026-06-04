from abc import ABC, abstractmethod
from datetime import date
from typing import Union



class ICEDeliveryPeriodABC(ABC):
    def __init__(self):
        pass
    
    @abstractmethod
    def __str__(self) -> str:
        pass

        
class ICEDeliveryPeriod_Daily(ICEDeliveryPeriodABC):
    def __init__(self, date: date):
        self.date = date
            
    def __str__(self) -> str:
        return self.date.strftime('%Y-%m-%d')

class ICEDeliveryPeriod_Month(ICEDeliveryPeriodABC):
    def __init__(self, month: int, year: int):
        
        if month < 1 or month > 12:
            raise ValueError('Month must be between 1 and 12')
        
        if year < 1900 or year > 2100:
            raise ValueError('Year must be between 1900 and 2100')
        
        self.month = month
        self.year = year

    def __str__(self) -> str:
        return f'{self.year}-{self.month:02d}'
    
class ICEDeliveryPeriod_Quarter(ICEDeliveryPeriodABC):
    def __init__(self, quarter: int, year: int):
        if year < 1900 or year > 2100:
            raise ValueError('Year must be between 1900 and 2100')
        
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
    

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# RANGE
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

class ICEDeliveryPeriod_Season(ICEDeliveryPeriodABC, ABC):
    @classmethod
    def from_values(cls, from_year: int, from_month: int, from_day:int, to_year: int, to_month: int, to_day: int)->ICEDeliveryPeriod_SeasonUnion:
        if from_day == to_day and to_day == 0:
            return ICEDeliveryPeriod_Season_MonthRange(from_year=from_year, 
                                                      from_month=from_day, 
                                                      to_year=to_year, 
                                                      to_month=to_month)
        
        try:
            return ICEDeliveryPeriod_Season_DateRange(from_year=from_year, 
                                                      from_month=from_day, 
                                                      from_day=from_day, 
                                                      to_year=to_year, 
                                                      to_month=to_month, 
                                                      to_day=to_day)
        except:
            raise ValueError('Invalid date range')
            
    
    def __init__(self, from_year: int, from_month: int, to_year: int, to_month: int):
        self.year = from_year
        self.from_month = from_month
        self.to_year = to_year
        self.to_month = to_month    

    @abstractmethod
    def __str__(self) -> str:
        pass

class ICEDeliveryPeriod_Season_MonthRange(ICEDeliveryPeriod_Season):
    def __init__(self, from_year: int, from_month: int, to_year: int, to_month: int):
        super().__init__(from_year, from_month, to_year, to_month)
    
    def __str__(self) -> str:
        return f'{self.year}/{self.from_month:02d}-{self.to_year}/{self.to_month:02d}'

class ICEDeliveryPeriod_Season_DateRange(ICEDeliveryPeriod_Season_MonthRange):
    def __init__(self, from_year: int, from_month: int, from_day:int, to_year: int, to_month: int, to_day: int):
        self.from_day = from_day
        self.to_day = to_day
        super().__init__(from_year, from_month, to_year, to_month)

    def __str__(self) -> str:
        return f'{self.year}\\{self.from_month:02d}\\{self.from_day:02d}-{self.to_year}\\{self.to_month:02d}\\{self.to_day:02d}'
    

ICEDeliveryPeriod_SeasonUnion = ICEDeliveryPeriod_Season_DateRange | ICEDeliveryPeriod_Season_MonthRange

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# END:RANGE
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

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
                            ICEDeliveryPeriod_Year, 
                            ICEDeliveryPeriod_SeasonUnion
                        ]