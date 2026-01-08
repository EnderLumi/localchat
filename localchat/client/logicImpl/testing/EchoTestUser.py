from localchat.util import Chat
from localchat.client.logicImpl.testing import TestUser
from uuid import UUID


class EchoTestUser(TestUser):
    def __init__(self, user_id: UUID, name: str) -> None:
        super().__init__(user_id, f"{name}[EchoTestUser]")

    def user_posted_message(self, chat: Chat, message: str):
        raw_message = f"Did someone say \"{message}\"?"
        self.post_message(chat, raw_message)
