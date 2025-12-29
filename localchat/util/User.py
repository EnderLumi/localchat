from uuid import UUID
from ipaddress import IPv4Address, IPv6Address


class User:
    def __init__(self): ...

    def get_id(self) -> UUID: ...
    def get_name(self) -> str:
        """
        Returns the users name.
        :return:
        :raise IOError: if a IOError occurs while receiving the name
        """
    def get_ip_address(self) -> IPv4Address | IPv6Address: ...

    def __eq__(self, other) -> bool:
        if not isinstance(other, User): return False
        return self.get_id() == other.get_id()
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.get_id())
