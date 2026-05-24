from enum import Enum
from abc import ABC,abstractmethod
from typing import Self, Iterable, cast


class ICETermException(Exception, ABC):
    def __init__(self, message: str, char: str)-> None:

        super().__init__(message)

class ICETermException_NoMatchingCharacter(ICETermException):
    def __init__(self, char: str)-> None:
        super().__init__(message=f'No matching character found: {char}', char=char)

class ICECodeEnum(Enum):
    """Template for ICE Enums with code and description."""

    @classmethod
    @abstractmethod
    def from_code(cls, code: str) -> Self:
        pass
    
    
class FromCode:
    """Mixin to provide from_code lookup for ICECodeEnums."""
    code: str  # Type hint so the linter knows this property exists on members

    @classmethod
    def from_code(cls, code: str) -> Self:
        target_char = code.strip().upper()
        
        for member in cast(Iterable[Self], cls):
            if member.code == target_char:
                return member
                
        raise ICETermException_NoMatchingCharacter(char=code)