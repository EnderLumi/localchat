from typing import Generic, TypeVar, final
from uuid import UUID


_T = TypeVar('_T')

@final
class Event(Generic[_T]):
    def __init__(self, owner : UUID, value : _T):
        self._owner = owner
        self._value = value

    def owner(self) -> UUID:
        return self._owner
    def value(self) -> _T:
        return self._value

    def __repr__(self) -> str:
        return "Event[owner=" + str(self._owner) + ",value=" + str(self._value) + "]"
