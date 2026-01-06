from localchat.util import ChatInformation
from uuid import UUID
from ipaddress import IPv4Address, IPv6Address


class TestChatInformation(ChatInformation):
    def __init__(self, chat_id: UUID, chat_name: str):
        super().__init__()
        self._chat_id = chat_id
        self._chat_name = chat_name

    def get_id(self) -> UUID:
        return self._chat_id
    def get_name(self) -> str:
        return self._chat_name

    def set_name(self, name: str):
        self._chat_name = name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")
    def get_port(self) -> int:
        return 0


