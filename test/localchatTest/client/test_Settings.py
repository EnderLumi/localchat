from pathlib import Path
from unittest import TestCase
from uuid import UUID, uuid4

from localchat.client.UIImpl.CLI import CLIChatUI, CLIMenuUI
from localchat.client.logic import Logic
from localchat.settings import AppSettings, SettingsStore
from localchat.settings.validators import normalize_name_color
from localchat.util import BinaryIOBase, Chat, ChatInformation, User, UserMessage
from localchat.util.event import Event, EventHandler


class _Reader:
    def __init__(self, values: list[str]):
        self._values = list(values)
        self._index = 0

    def __call__(self, _prompt: str = "") -> str:
        if self._index >= len(self._values):
            raise EOFError()
        value = self._values[self._index]
        self._index += 1
        return value


class _Output:
    def __init__(self):
        self.items: list[str] = []

    def __call__(self, value: str):
        self.items.append(value)


class _DummyUser(User):
    def __init__(self, user_id: UUID, name: str):
        super().__init__()
        self._user_id = user_id
        self._name = name

    def get_id(self) -> UUID:
        return self._user_id

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


class _DummyChatInfo(ChatInformation):
    def __init__(self):
        super().__init__()
        self._id = uuid4()

    def get_id(self) -> UUID:
        return self._id

    def get_name(self) -> str:
        return "dummy"

    def get_ip_address(self):
        from ipaddress import IPv4Address
        return IPv4Address("127.0.0.1")

    def get_port(self) -> int:
        return 51121


class _DummyChat(Chat):
    def __init__(self):
        super().__init__()
        self._info = _DummyChatInfo()
        self._server_user = _DummyUser(uuid4(), "server")
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
        return self._server_user

    def on_user_joined(self):
        return self._on_user_joined

    def on_user_left(self):
        return self._on_user_left

    def on_user_became_host(self):
        return self._on_user_became_host

    def on_user_posted_message(self):
        return self._on_user_posted_message

    def on_user_send_private_message(self):
        return self._on_user_send_private_message

    def on_connection_problem(self):
        return self._on_connection_problem

    def on_connection_failure(self):
        return self._on_connection_failure


class _DummyLogic(Logic):
    def __init__(self):
        super().__init__()
        self.ui = None

    def start(self):
        return

    def shutdown(self):
        if self.ui is not None:
            self.ui.shutdown()

    def set_ui(self, ui: object):
        self.ui = ui

    def ui_initialized(self):
        return

    def create_chat(self, info: ChatInformation, online: bool, port: int) -> Chat:
        return _DummyChat()

    def load_chat(self, input_stream: BinaryIOBase, online: bool, port: int) -> Chat:
        raise NotImplementedError()

    def search_server(self) -> list[Chat]:
        return []

    def get_system_chat(self) -> Chat:
        return _DummyChat()


class TestSettings(TestCase):
    def test_settings_store_roundtrip(self):
        path = Path("/tmp/localchat_settings_test_roundtrip.json")
        try:
            if path.exists():
                path.unlink()
            store = SettingsStore(str(path))
            settings = AppSettings.default()
            settings.username = "Neo"
            settings.name_color = "blue"
            settings.default_host_server_port = 51234
            settings.show_timestamps = True
            store.save(settings)

            loaded = store.load()
            self.assertEqual(loaded.username, "Neo")
            self.assertEqual(loaded.name_color, "blue")
            self.assertEqual(loaded.default_host_server_port, 51234)
            self.assertTrue(loaded.show_timestamps)
        finally:
            if path.exists():
                path.unlink()

    def test_settings_store_invalid_name_color_falls_back_to_default(self):
        path = Path("/tmp/localchat_settings_test_invalid_color.json")
        try:
            if path.exists():
                path.unlink()
            path.write_text('{"name_color":"@@bad@@","username":"x"}', encoding="utf-8")
            store = SettingsStore(str(path))
            loaded = store.load()
            self.assertEqual(loaded.name_color, AppSettings.default().name_color)
        finally:
            if path.exists():
                path.unlink()

    def test_name_color_validator_accepts_config_name_and_hex(self):
        self.assertEqual(normalize_name_color("blue"), "blue")
        self.assertEqual(normalize_name_color("#aabbcc"), "#AABBCC")
        with self.assertRaises(ValueError):
            normalize_name_color("not-a-color")

    def test_menu_uses_settings_username_and_default_port(self):
        output = _Output()
        settings = AppSettings.default()
        settings.username = "FromSettings"
        settings.default_host_server_port = 51234

        # Enter menu start-server, keep host default, use default port, then leave and exit.
        reader = _Reader(["2", "", "", "", "/leave", "0"])

        created_ports: list[int] = []

        class _DummyServer:
            def __init__(self, _host: str, port: int):
                self._port = port
                created_ports.append(port)

            def start(self):
                return

            def stop(self):
                return

            def get_server_info(self):
                return _DummyChatInfo()

        ui = CLIMenuUI(
            input_reader=reader,
            output_writer=output,
            server_factory=_DummyServer,
            settings=settings,
        )
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)
        ui.start()

        self.assertEqual(created_ports[0], 51234)

    def test_chat_ui_hides_join_leave_notifications_and_shows_timestamps(self):
        output = _Output()
        chat = _DummyChat()
        settings = AppSettings.default()
        settings.show_join_leave_notifications = False
        settings.show_timestamps = True
        appearance = _DummyUser(uuid4(), "me")
        sender = _DummyUser(uuid4(), "Alice")

        class _ReaderWithEvent:
            def __init__(self):
                self._calls = 0

            def __call__(self, _prompt: str = "") -> str:
                self._calls += 1
                if self._calls == 1:
                    chat.on_user_joined().handle(Event(chat.get_chat_info().get_id(), sender))
                    chat.on_user_posted_message().handle(
                        Event(chat.get_chat_info().get_id(), _DummyMessage(sender, "hello", 0.0))
                    )
                    return "/leave"
                raise EOFError()

        ui = CLIChatUI(
            chat,
            appearance,
            settings=settings,
            input_reader=_ReaderWithEvent(),
            output_writer=output,
        )
        ui.run()

        self.assertFalse(any(item.startswith("[join]") for item in output.items))
        timestamped_lines = [item for item in output.items if "Alice: hello" in item]
        self.assertTrue(any(item.startswith("[") and "] " in item for item in timestamped_lines))
