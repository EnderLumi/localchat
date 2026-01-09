from localchat.util import User, Chat, UserMessage
from localchat.util.event import Event
from uuid import UUID
from ipaddress import IPv4Address, IPv6Address
from time import time


class MyUserMessage(UserMessage):
    def __init__(self, sender: User, message: str, timestamp: float):
        self._sender = sender
        self._message = message
        self._timestamp = timestamp

    def sender(self):
        return self._sender
    def message(self):
        return self._message
    def timestamp(self):
        return self._timestamp


class TestUser(User):
    def __init__(self, user_id: UUID, name: str) -> None:
        super().__init__()
        self._name = name
        self._id = user_id

    def _raw_message_to_event(self, chat: Chat, message: str) -> Event[UserMessage]:
        timestamp = time()
        chat_id = chat.get_chat_info().get_id()
        user_message = MyUserMessage(self, message, timestamp)
        return Event(chat_id, user_message)

    def post_message(self, chat: Chat, message: str):
        event = self._raw_message_to_event(chat, message)
        chat.on_user_posted_message().handle(event)

    def send_private_message_to_real_user(self, chat: Chat, message: str):
        event = self._raw_message_to_event(chat, message)
        chat.on_user_send_private_message().handle(event)

    def user_posted_message(self, chat: Chat, message: str): ...
    def tick(self, chat: Chat): ...

    def get_id(self) -> UUID:
        return self._id
    def get_name(self) -> str:
        return self._name
    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")

