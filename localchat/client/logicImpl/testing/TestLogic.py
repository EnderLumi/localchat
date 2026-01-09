from localchat.util import Chat, ChatInformation, BinaryIOBase
from localchat.client.logicImpl import AbstractLogic
from localchat.client.logicImpl.testing import TestChat, EchoTestUser, TalkingTestUser, TestUser
from uuid import uuid4
from threading import RLock, Thread
from time import sleep


class TestLogic(AbstractLogic):
    def __init__(self):
        super().__init__()
        self._lock = RLock()
        self._system_chat = TestChat(uuid4())
        self._system_chat_user = TestUser(uuid4(), "system")
        self._system_chat_user.test_users = [self._system_chat_user]
        self._test_chats: list[TestChat] = []
        self._chat_tick_thread: Thread | None = None
        self._do_tick = True

    def tick_work(self):
        while True:
            sleep(3.0)
            with self._lock:
                if not self._do_tick: return
                for test_chat in self._test_chats:
                    test_chat.tick()

    def send_system_message(self, message: str):
        self._system_chat_user.send_private_message_to_real_user(
            self._system_chat,
            message
        )

    def ui_initialized_impl(self):
        self.send_system_message("=== Test Logic 1.0 ===")
        # the logic should not assume any UI details like commands
        # self.send_system_message("type 'help' for a list of available commands")

    def start_impl(self):
        self._chat_tick_thread = Thread(target=self.tick_work)
        self._chat_tick_thread.start()

    def shutdown_impl(self):
        with self._lock:
            self._do_tick = False
        self._chat_tick_thread.join()

    def create_chat(self, info: ChatInformation, online: bool, port: int) -> Chat:
        with self._lock:
            chat = TestChat(info.get_id())
            chat.set_chat_info(info)
            chat.set_on_real_user_leaves(
                lambda: self._test_chats.remove(chat)
            )
            self._test_chats.append(chat)
            return chat

    def load_chat(self, input_stream: BinaryIOBase, online: bool, port: int) -> Chat:
        raise NotImplementedError()

    @staticmethod
    def _make_up_server() -> TestChat:
        chat = TestChat(uuid4())
        user1 = EchoTestUser(uuid4(), "Alice")
        user2 = EchoTestUser(uuid4(), "Bob")
        user3 = TalkingTestUser(uuid4(), "Charlie")
        user4 = TalkingTestUser(uuid4(), "David")
        chat.test_users = [user1, user2, user3, user4]
        return chat

    def search_server(self) -> list[Chat]:
        with self._lock:
            for i in range(3):
                self._test_chats.append(self._make_up_server())
            return self._test_chats

    def get_system_chat(self) -> Chat:
        return self._system_chat