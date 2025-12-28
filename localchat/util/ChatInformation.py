import uuid
import ipaddress


class ChatInformation:
    def __init__(self): ...

    def get_id(self) -> uuid.UUID: ...
    def get_name(self) -> str:
        """
        Returns the chats name.
        :return:
        :raise IOError: if a IOError occurs while receiving the name
        """
    def get_ip_address(self) -> ipaddress.IPv4Address | ipaddress.IPv6Address: ...
    def get_port(self) -> int: ...

    def __eq__(self, other) -> bool:
        if not isinstance(other, ChatInformation): return False
        return self.get_id() == other.get_id()
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.get_id())
