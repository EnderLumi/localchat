from uuid import UUID
from ipaddress import IPv4Address, IPv6Address
from typing import final
from abc import ABC, abstractmethod

class User(ABC):
    #def __init__(self): ...
    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_id(self) -> UUID: ...
    @abstractmethod
    def get_name(self) -> str:
        """
        Returns the users name.
        :return:
        :raise IOError: if a IOError occurs while receiving the name
        """
    @abstractmethod
    def get_ip_address(self) -> IPv4Address | IPv6Address: ...

    @final
    def __eq__(self, other) -> bool:
        if not isinstance(other, User): return False
        return self.get_id() == other.get_id()
    @final
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
    @final
    def __hash__(self) -> int:
        return hash(self.get_id())
