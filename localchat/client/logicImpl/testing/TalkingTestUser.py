from localchat.util import Chat
from localchat.client.logicImpl.testing import TestUser
from uuid import UUID


class TalkingTestUser(TestUser):
    def __init__(self, user_id: UUID, name: str) -> None:
        super().__init__(user_id, f"{name}[TalkingTestUser]")

    def get_tick_message(self) -> str:
        return "Nice day for fishing aren't it?"

    def tick(self, chat: Chat):
        raw_message = self.get_tick_message()
        self.post_message(chat, raw_message)
