from localchat.util import User, Chat
from uuid import UUID
from ipaddress import IPv4Address, IPv6Address


class TestUser(User):
    def __init__(self, user_id: UUID, name: str) -> None:
        super().__init__()
        self._name = name
        self._id = user_id

    def user_posted_message(self, chat: Chat, message: str): ...
    def tick(self, chat: Chat): ...

    def get_id(self) -> UUID:
        return self._id
    def get_name(self) -> str:
        return self._name
    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")

