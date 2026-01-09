from localchat.util import User, Chat, ChatInformation, BinaryIOBase
from localchat.client.logicImpl.AbstractChat import AbstractChat
from localchat.client.logicImpl.testing import TestUser, TestChatInformation
from localchat.util.event import Event
from threading import RLock
from uuid import UUID, uuid4
from collections.abc import Callable


class ServerUser(TestUser):
    _MESSAGES = [
        "Beep Boop",
        "Important Server Message: This is important.",
        "Bzz Bzz! Error Error!",
        "Remember to drink water!",
        "Please only share correct homework, thank you!"
    ]

    def __init__(self, user_id: UUID, name: str):
        super().__init__(user_id, name)
        self._counter = 0

    def tick(self, chat: Chat):
        if self._counter >= len(self._MESSAGES):
            self._counter = 0
        message =  self._MESSAGES[self._counter]
        self._counter += 1
        self.post_message(chat, message)

    def user_posted_message(self, chat: Chat, message: str):
        response = f"Real user attempted to execute server sided command: '{message}'"
        self.send_private_message_to_real_user(chat, response)


class TestChat(AbstractChat):
    def __init__(self, chat_id: UUID):
        super().__init__()
        self.test_users: list[TestUser] = []
        self.real_user: User|None = None
        self._chat_id = chat_id
        self._chat_info = TestChatInformation(self._chat_id, f"Test-Chat-{self._chat_id.hex}")
        self._server_user = ServerUser(uuid4(), "server")
        self._lock = RLock()
        self._on_real_user_leaves: Callable[[], None] = lambda: None

    def tick(self):
        with self._lock:
            self._server_user.tick(self)
            for test_user in self.test_users:
                test_user.tick(self)

    def set_on_real_user_leaves(self, on_real_user_leaves: Callable[[], None]):
        self._on_real_user_leaves = on_real_user_leaves

    def get_chat_info(self) -> ChatInformation:
        return self._chat_info

    def set_chat_info(self, chat_info: ChatInformation):
        with self._lock:
            self._chat_info.set_name(chat_info.get_name())

    def join(self, appearance: User):
        with self._lock:
            # self.clear_handlers()
            self.real_user = appearance
            on_joined = self.on_user_joined()
            for test_user in self.test_users:
                on_joined.handle(Event(self._chat_id, test_user))
            on_joined.handle(Event(self._chat_id, self.real_user))

    def leave(self):
        with self._lock:
            # self.clear_handlers()
            self.real_user = None
            self._on_real_user_leaves()

    def update_appearance(self, appearance: User):
        with self._lock:
            if self.real_user is None:
                raise RuntimeError("user is not a member of the chat")
            self.real_user = appearance

    def post_message(self, message: str):
        with self._lock:
            if self.real_user is None:
                raise RuntimeError("user is not a member of the chat")
            for test_user in self.test_users:
                test_user.user_posted_message(self, message)

    def send_private_message(self, recipient: User, message: str):
        with self._lock:
            if self.real_user is None:
                raise RuntimeError("user is not a member of the chat")
            if recipient != self._server_user:
                raise PermissionError("user is not permitted to send a private message to this other user")
            self._server_user.user_posted_message(self, message)

    def download_chat(self, output_stream : BinaryIOBase):
        with self._lock:
            if self.real_user is None:
                raise RuntimeError("user is not a member of the chat")
        raise NotImplementedError()

    def get_server_user(self) -> User:
        with self._lock:
            if self.real_user is None:
                raise RuntimeError("user is not a member of the chat")
            return self._server_user


