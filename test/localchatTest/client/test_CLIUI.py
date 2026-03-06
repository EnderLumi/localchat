from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address
from unittest import TestCase
from uuid import UUID, uuid4

from localchat.client import UI
from localchat.client.UIImpl.CLI import CLIChatUI, CLIMenuUI, CLISettingsUI
from localchat.config.defaults import DEFAULT_HOST, DEFAULT_PORT
from localchat.client.logic import Logic
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

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")

    def set_name(self, name: str):
        self._name = name

    def set_id(self, user_id: UUID):
        self._user_id = user_id


class _DummyChatInfo(ChatInformation):
    def __init__(self, chat_id: UUID, name: str, port: int = 51121):
        super().__init__()
        self._chat_id = chat_id
        self._name = name
        self._port = port

    def get_id(self) -> UUID:
        return self._chat_id

    def get_name(self) -> str:
        return self._name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("127.0.0.1")

    def get_port(self) -> int:
        return self._port


class _DummyServerInfo(ChatInformation):
    def __init__(self, chat_id: UUID, name: str, host: str, port: int):
        super().__init__()
        self._chat_id = chat_id
        self._name = name
        self._host = host
        self._port = port

    def get_id(self) -> UUID:
        return self._chat_id

    def get_name(self) -> str:
        return self._name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address(self._host)

    def get_port(self) -> int:
        return self._port


class _DummyUserMessage(UserMessage):
    def __init__(self, sender: User, message: str):
        self._sender = sender
        self._message = message

    def sender(self) -> User:
        return self._sender

    def message(self) -> str:
        return self._message

    def timestamp(self) -> float:
        return 0.0


class _DummyChat(Chat):
    def __init__(self, name: str):
        super().__init__()
        self._chat_info = _DummyChatInfo(uuid4(), name)
        self._server_user = _DummyUser(uuid4(), "server")
        self.join_calls = 0
        self.leave_calls = 0
        self.posted_messages: list[str] = []

        self._on_user_joined = EventHandler()
        self._on_user_left = EventHandler()
        self._on_user_became_host = EventHandler()
        self._on_user_posted_message = EventHandler()
        self._on_user_send_private_message = EventHandler()
        self._on_connection_problem = EventHandler()
        self._on_connection_failure = EventHandler()

    def get_chat_info(self) -> ChatInformation:
        return self._chat_info

    def set_chat_info(self, chat_info: ChatInformation):
        self._chat_info = chat_info

    def join(self, appearance: User):
        self.join_calls += 1
        self._on_user_joined.handle(Event(self._chat_info.get_id(), appearance))

    def leave(self):
        self.leave_calls += 1

    def update_appearance(self, appearance: User):
        return

    def post_message(self, message: str):
        self.posted_messages.append(message)
        self._on_user_posted_message.handle(
            Event(
                self._chat_info.get_id(),
                _DummyUserMessage(_DummyUser(uuid4(), "me"), message),
            )
        )

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
        self.ui: UI | None = None
        self.shutdown_called = False
        self.ui_initialized_calls = 0
        self.created_chat_info: list[ChatInformation] = []
        self.created_chats: list[_DummyChat] = []
        self.search_results: list[Chat] = []
        self.system_chat = _DummyChat("system")

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
        self.created_chat_info.append(info)
        chat = _DummyChat(info.get_name())
        self.created_chats.append(chat)
        return chat

    def load_chat(self, input_stream: BinaryIOBase, online: bool, port: int) -> Chat:
        raise NotImplementedError()

    def search_server(self) -> list[Chat]:
        return list(self.search_results)

    def get_system_chat(self) -> Chat:
        return self.system_chat


class _DummyServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.started = False
        self.stopped = False
        self._server_info = _DummyServerInfo(uuid4(), "hosted-server", "127.0.0.1", port)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def get_server_info(self) -> ChatInformation:
        return self._server_info


class TestCLIUI(TestCase):
    def test_cli_menu_exit_calls_logic_shutdown(self):
        output = _Output()
        reader = _Reader(["0"])
        ui = CLIMenuUI(input_reader=reader, output_writer=output)
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)

        ui.start()

        self.assertEqual(logic.ui_initialized_calls, 1)
        self.assertTrue(logic.shutdown_called)

    def test_cli_menu_direct_connect_opens_chat_and_returns(self):
        output = _Output()
        reader = _Reader(["3", "127.0.0.1:51121", "/leave", "0"])
        ui = CLIMenuUI(input_reader=reader, output_writer=output)
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)

        ui.start()

        self.assertEqual(len(logic.created_chat_info), 1)
        self.assertEqual(len(logic.created_chats), 1)
        self.assertEqual(logic.created_chats[0].join_calls, 1)
        self.assertEqual(logic.created_chats[0].leave_calls, 1)

    def test_cli_menu_direct_connect_accepts_url(self):
        output = _Output()
        reader = _Reader(["3", "http://host.local:8080/join/room1", "/leave", "0"])
        ui = CLIMenuUI(input_reader=reader, output_writer=output)
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)

        ui.start()

        self.assertEqual(len(logic.created_chat_info), 1)
        self.assertEqual(logic.created_chat_info[0].get_name(), "direct-host.local:8080")
        self.assertTrue(
            any("Join room hint detected ('room1')" in item for item in output.items)
        )

    def test_cli_menu_search_join_uses_unified_connect_path(self):
        output = _Output()
        reader = _Reader(["1", "1", "/leave", "0"])
        ui = CLIMenuUI(input_reader=reader, output_writer=output)
        logic = _DummyLogic()
        logic.search_results = [_DummyChat("discovered-server")]
        logic.set_ui(ui)
        ui.set_logic(logic)

        ui.start()

        self.assertEqual(len(logic.created_chat_info), 1)
        self.assertEqual(logic.created_chat_info[0].get_name(), "discovered-server")
        self.assertEqual(str(logic.created_chat_info[0].get_ip_address()), "127.0.0.1")
        self.assertEqual(logic.created_chat_info[0].get_port(), 51121)

    def test_cli_chat_posts_message(self):
        output = _Output()
        reader = _Reader(["hello world", "/leave"])
        chat = _DummyChat("demo")
        appearance = _DummyUser(uuid4(), "tester")
        ui = CLIChatUI(chat, appearance, input_reader=reader, output_writer=output)

        ui.run()

        self.assertEqual(chat.join_calls, 1)
        self.assertEqual(chat.leave_calls, 1)
        self.assertEqual(chat.posted_messages, ["hello world"])

    def test_cli_settings_can_update_name_and_id(self):
        output = _Output()
        target_id = UUID("12345678-1234-5678-1234-567812345678")
        reader = _Reader(["1", "Neo", "2", "invalid", "2", str(target_id), "0"])
        appearance = _DummyUser(uuid4(), "old")
        settings = CLISettingsUI(input_reader=reader, output_writer=output)

        settings.run(appearance)

        self.assertEqual(appearance.get_name(), "Neo")
        self.assertEqual(appearance.get_id(), target_id)
        self.assertTrue(any("Invalid UUID." in item for item in output.items))

    def test_cli_menu_can_start_new_server_and_shutdown_stops_it(self):
        output = _Output()
        reader = _Reader(["2", "", "", "/leave", "0"])
        created: list[_DummyServer] = []

        def _server_factory(host: str, port: int):
            server = _DummyServer(host, port)
            created.append(server)
            return server

        ui = CLIMenuUI(input_reader=reader, output_writer=output, server_factory=_server_factory)
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)

        ui.start()

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].host, DEFAULT_HOST)
        self.assertEqual(created[0].port, DEFAULT_PORT)
        self.assertTrue(created[0].started)
        self.assertTrue(created[0].stopped)
        self.assertEqual(len(logic.created_chat_info), 1)
        self.assertEqual(logic.created_chat_info[0].get_name(), "hosted-server")
        self.assertEqual(logic.created_chat_info[0].get_port(), DEFAULT_PORT)

    def test_cli_menu_rejects_privileged_server_port(self):
        output = _Output()
        reader = _Reader(["2", "", "80", "0"])
        created: list[_DummyServer] = []

        def _server_factory(host: str, port: int):
            server = _DummyServer(host, port)
            created.append(server)
            return server

        ui = CLIMenuUI(input_reader=reader, output_writer=output, server_factory=_server_factory)
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)

        ui.start()

        self.assertEqual(len(created), 0)
        self.assertTrue(
            any("reserved/privileged" in item for item in output.items)
        )

    def test_cli_menu_warns_for_registered_port_range(self):
        output = _Output()
        reader = _Reader(["2", "", "2048", "/leave", "0"])
        created: list[_DummyServer] = []

        def _server_factory(host: str, port: int):
            server = _DummyServer(host, port)
            created.append(server)
            return server

        ui = CLIMenuUI(input_reader=reader, output_writer=output, server_factory=_server_factory)
        logic = _DummyLogic()
        logic.set_ui(ui)
        ui.set_logic(logic)

        ui.start()

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].port, 2048)
        self.assertTrue(
            any("Recommended range is 49152-65535" in item for item in output.items)
        )
