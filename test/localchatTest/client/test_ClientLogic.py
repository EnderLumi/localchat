from threading import Event
from time import sleep
from unittest import TestCase
from uuid import uuid4

from localchat.client import UI
from localchat.client.logicImpl import AbstractChat
from localchat.client.logicImpl import AbstractLogic
from localchat.net import SerializableChatInformation, SerializableUser
from localchat.util import BinaryIOBase, Chat, ChatInformation, User


class _DummyLogicChat(AbstractChat):
    def __init__(self):
        super().__init__()
        self._info = SerializableChatInformation(uuid4(), "dummy")

    def get_chat_info(self) -> ChatInformation:
        return self._info

    def set_chat_info(self, chat_info: ChatInformation):
        return

    def join(self, appearance: User):
        return

    def leave(self):
        return

    def update_appearance(self, appearance: User):
        return

    def post_message(self, message: str):
        return

    def send_private_message(self, recipient: User, message: str):
        return

    def download_chat(self, output_stream: BinaryIOBase):
        raise NotImplementedError()

    def get_server_user(self) -> User:
        return SerializableUser(uuid4(), "server")


class _DummyUI(UI):
    def __init__(self):
        super().__init__()
        self.logic = None
        self.start_called = False
        self.shutdown_called = False
        self.call_ui_initialized_on_start = True

    def set_logic(self, logic: object):
        self.logic = logic

    def start(self) -> None:
        self.start_called = True
        if self.call_ui_initialized_on_start and self.logic is not None:
            self.logic.ui_initialized()

    def shutdown(self) -> None:
        self.shutdown_called = True


class _DummyLogic(AbstractLogic):
    def __init__(self):
        super().__init__()
        self.ui_initialized_impl_calls = 0
        self.start_impl_calls = 0
        self.shutdown_impl_calls = 0
        self._stop_event = Event()
        self._chat = _DummyLogicChat()

    def ui_initialized_impl(self):
        self.ui_initialized_impl_calls += 1

    def start_impl(self):
        self.start_impl_calls += 1
        self._stop_event.wait(timeout=3.0)

    def shutdown_impl(self):
        self.shutdown_impl_calls += 1
        self._stop_event.set()

    def create_chat(self, info: ChatInformation, online: bool, port: int) -> Chat:
        return self._chat

    def load_chat(self, input_stream: BinaryIOBase, online: bool, port: int) -> Chat:
        raise NotImplementedError()

    def search_server(self) -> list[Chat]:
        return [self._chat]

    def get_system_chat(self) -> Chat:
        return self._chat


class TestClientLogic(TestCase):
    def test_set_ui_type_validation(self):
        logic = _DummyLogic()
        with self.assertRaises(TypeError):
            logic.set_ui(object())

    def test_ui_initialized_before_start_raises(self):
        logic = _DummyLogic()
        with self.assertRaises(RuntimeError):
            logic.ui_initialized()

    def test_start_requires_ui(self):
        logic = _DummyLogic()
        with self.assertRaises(RuntimeError):
            logic.start()

    def test_start_ui_initialized_and_shutdown_flow(self):
        logic = _DummyLogic()
        ui = _DummyUI()
        logic.set_ui(ui)
        ui.set_logic(logic)

        logic.start()
        sleep(0.02)
        self.assertTrue(ui.start_called)
        self.assertTrue(logic.ui_ready)
        self.assertEqual(logic.ui_initialized_impl_calls, 1)
        self.assertEqual(logic.start_impl_calls, 1)

        logic.shutdown()
        self.assertTrue(ui.shutdown_called)
        self.assertEqual(logic.shutdown_impl_calls, 1)

    def test_set_ui_after_start_raises(self):
        logic = _DummyLogic()
        ui = _DummyUI()
        logic.set_ui(ui)
        ui.set_logic(logic)
        logic.start()
        with self.assertRaises(RuntimeError):
            logic.set_ui(_DummyUI())
        logic.shutdown()

    def test_shutdown_without_start_raises(self):
        logic = _DummyLogic()
        with self.assertRaises(RuntimeError):
            logic.shutdown()

    def test_shutdown_idempotent_after_stopped(self):
        logic = _DummyLogic()
        ui = _DummyUI()
        logic.set_ui(ui)
        ui.set_logic(logic)
        logic.start()
        logic.shutdown()
        logic.shutdown()
