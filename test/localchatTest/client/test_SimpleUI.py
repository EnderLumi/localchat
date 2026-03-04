from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID, uuid4

from localchat.client.UIImpl.simple import SimpleUI
from localchat.client.logic import Logic
from localchat.util import BinaryIOBase, Chat, ChatInformation, User, UserMessage
from localchat.util.event import Event, EventHandler


class _DummyChatInfo(ChatInformation):
    def __init__(self, chat_id: UUID, name: str):
        super().__init__()
        self._id = chat_id
        self._name = name

    def get_id(self) -> UUID:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_ip_address(self):
        from ipaddress import IPv4Address
        return IPv4Address("0.0.0.0")

    def get_port(self) -> int:
        return 0


class _DummyUser(User):
    def __init__(self, user_id: UUID, name: str):
        super().__init__()
        self._id = user_id
        self._name = name

    def get_id(self) -> UUID:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_ip_address(self):
        from ipaddress import IPv4Address
        return IPv4Address("0.0.0.0")


class _DummyMessage(UserMessage):
    def __init__(self, sender: User, message: str, timestamp: float):
        self._sender = sender
        self._message = message
        self._timestamp = timestamp

    def sender(self) -> User:
        return self._sender

    def message(self) -> str:
        return self._message

    def timestamp(self) -> float:
        return self._timestamp


class _DummyChat(Chat):
    def __init__(self, name: str):
        super().__init__()
        self._info = _DummyChatInfo(uuid4(), name)
        self._server_user = _DummyUser(uuid4(), "server")
        self.join_calls = 0
        self.leave_calls = 0
        self.update_appearance_calls = 0
        self.posted_messages: list[str] = []

        self._on_user_joined = EventHandler()
        self._on_user_left = EventHandler()
        self._on_user_became_host = EventHandler()
        self._on_user_posted_message = EventHandler()
        self._on_user_send_private_message = EventHandler()
        self._on_connection_problem = EventHandler()
        self._on_connection_failure = EventHandler()

    def get_chat_info(self) -> ChatInformation:
        return self._info

    def set_chat_info(self, chat_info: ChatInformation):
        return

    def join(self, appearance: User):
        self.join_calls += 1

    def leave(self):
        self.leave_calls += 1

    def update_appearance(self, appearance: User):
        self.update_appearance_calls += 1

    def post_message(self, message: str):
        self.posted_messages.append(message)

    def send_private_message(self, recipient: User, message: str):
        return

    def download_chat(self, output_stream: BinaryIOBase):
        raise NotImplementedError()

    def get_server_user(self) -> User:
        return self._server_user

    def on_user_joined(self) -> EventHandler[User]:
        return self._on_user_joined

    def on_user_left(self) -> EventHandler[User]:
        return self._on_user_left

    def on_user_became_host(self) -> EventHandler[User]:
        return self._on_user_became_host

    def on_user_posted_message(self) -> EventHandler[UserMessage]:
        return self._on_user_posted_message

    def on_user_send_private_message(self) -> EventHandler[UserMessage]:
        return self._on_user_send_private_message

    def on_connection_problem(self) -> EventHandler[float]:
        return self._on_connection_problem

    def on_connection_failure(self) -> EventHandler[IOError]:
        return self._on_connection_failure


class _DummyLogic(Logic):
    def __init__(self):
        super().__init__()
        self.ui = None
        self.shutdown_called = False
        self.ui_initialized_calls = 0
        self.system_chat = _DummyChat("system")
        self.search_results: list[Chat] = []
        self.raise_search_error = False

    def start(self):
        return

    def shutdown(self):
        self.shutdown_called = True
        if self.ui is not None:
            self.ui.shutdown()

    def set_ui(self, ui: object):
        self.ui = ui

    def ui_initialized(self):
        self.ui_initialized_calls += 1

    def create_chat(self, info: ChatInformation, online: bool, port: int) -> Chat:
        return _DummyChat(info.get_name())

    def load_chat(self, input_stream: BinaryIOBase, online: bool, port: int) -> Chat:
        raise NotImplementedError()

    def search_server(self) -> list[Chat]:
        if self.raise_search_error:
            raise IOError("search failed")
        return list(self.search_results)

    def get_system_chat(self) -> Chat:
        return self.system_chat


class TestSimpleUI(TestCase):
    def test_set_logic_type_check(self):
        ui = SimpleUI()
        with self.assertRaises(TypeError):
            ui.set_logic(object())

    def test_start_requires_logic(self):
        ui = SimpleUI()
        with self.assertRaises(RuntimeError):
            ui.start()

    def test_server_search_success(self):
        ui = SimpleUI()
        logic = _DummyLogic()
        logic.search_results = [_DummyChat("Alpha"), _DummyChat("Beta")]
        ui.set_logic(logic)

        out = StringIO()
        with redirect_stdout(out):
            ui.on_event(Event(uuid4(), "server search"))

        self.assertEqual(len(ui.known_server), 2)
        self.assertIn("Alpha", out.getvalue())
        self.assertIn("Beta", out.getvalue())

    def test_server_search_io_error_clears_list(self):
        ui = SimpleUI()
        logic = _DummyLogic()
        logic.raise_search_error = True
        ui.known_server = [_DummyChat("Old")]
        ui.set_logic(logic)

        out = StringIO()
        with redirect_stdout(out):
            ui.on_event(Event(uuid4(), "server search"))
        self.assertEqual(ui.known_server, [])
        self.assertIn("I/O error:", out.getvalue())

    def test_server_join_and_leave(self):
        ui = SimpleUI()
        logic = _DummyLogic()
        join_chat = _DummyChat("JoinMe")
        ui.known_server = [join_chat]
        ui.set_logic(logic)

        out = StringIO()
        with redirect_stdout(out):
            ui.on_event(Event(uuid4(), f"server join {join_chat.get_chat_info().get_id().hex[:8]}"))
        self.assertIsNotNone(ui.get_active_chat())
        self.assertEqual(join_chat.join_calls, 1)

        with redirect_stdout(out):
            ui.on_event(Event(uuid4(), "server leave"))
        self.assertIsNone(ui.get_active_chat())
        self.assertEqual(join_chat.leave_calls, 1)

    def test_appearance_updates_active_chat(self):
        ui = SimpleUI()
        logic = _DummyLogic()
        chat = _DummyChat("JoinMe")
        ui.known_server = [chat]
        ui.set_logic(logic)
        ui.on_event(Event(uuid4(), f"server join {chat.get_chat_info().get_id().hex[:8]}"))

        ui.on_event(Event(uuid4(), "appearance name Neo"))
        self.assertEqual(ui.active_appearance.get_name(), "Neo")
        self.assertEqual(chat.update_appearance_calls, 1)

        out = StringIO()
        with redirect_stdout(out):
            ui.on_event(Event(uuid4(), "appearance id invalid-uuid"))
        self.assertIn("error: invalid id:", out.getvalue())

    def test_exit_command_calls_logic_shutdown(self):
        ui = SimpleUI()
        logic = _DummyLogic()
        ui.set_logic(logic)
        ui.on_event(Event(uuid4(), "exit"))
        self.assertTrue(logic.shutdown_called)

    def test_start_impl_bootstrap_and_loop_exit(self):
        ui = SimpleUI()
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)

        out = StringIO()
        with patch("builtins.input", side_effect=["exit"]):
            with redirect_stdout(out):
                ui.start()

        self.assertEqual(logic.system_chat.join_calls, 1)
        self.assertEqual(logic.ui_initialized_calls, 1)
        self.assertTrue(logic.shutdown_called)
        self.assertIn("Simple UI 1.0", out.getvalue())
