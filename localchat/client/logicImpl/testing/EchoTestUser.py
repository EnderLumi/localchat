from localchat.util import Chat, User, UserMessage
from localchat.event import Event
from localchat.client.logicImpl.testing import TestUser
from uuid import UUID
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


class EchoTestUser(TestUser):
    def __init__(self, user_id: UUID, name: str) -> None:
        super().__init__(user_id, f"{name}[EchoTestUser]")

    def user_posted_message(self, chat: Chat, message: str):
        raw_message = f"Did someone say \"{message}\"?"
        timestamp = time()
        chat_id = chat.get_chat_info().get_id()
        message = MyUserMessage(self, raw_message, timestamp)
        event = Event(chat_id, message)
        chat.on_user_posted_message().handle(event)
