from unittest import TestCase
from uuid import uuid4

from localchat.client import UI
from localchat.client.logicImpl import TcpClientLogic, TcpChat, TcpChatInformation
from localchat.net.discovery import DiscoveredServer
from localchat.util import Chat


class _DummyUI(UI):
    def __init__(self):
        super().__init__()
        self.logic = None
        self.started = False
        self.stopped = False

    def set_logic(self, logic: object):
        self.logic = logic

    def start(self) -> None:
        self.started = True
        if self.logic is not None:
            self.logic.ui_initialized()

    def shutdown(self) -> None:
        self.stopped = True


class _LeaveSpyChat(Chat):
    def __init__(self):
        super().__init__()
        self.left = False

    def get_chat_info(self):
        raise NotImplementedError()

    def set_chat_info(self, chat_info):
        return

    def join(self, appearance):
        return

    def leave(self):
        self.left = True

    def update_appearance(self, appearance):
        return

    def post_message(self, message: str):
        return

    def send_private_message(self, recipient, message: str):
        return

    def download_chat(self, output_stream):
        raise NotImplementedError()

    def get_server_user(self):
        raise NotImplementedError()

    def on_user_joined(self):
        raise NotImplementedError()

    def on_user_left(self):
        raise NotImplementedError()

    def on_user_became_host(self):
        raise NotImplementedError()

    def on_user_posted_message(self):
        raise NotImplementedError()

    def on_user_send_private_message(self):
        raise NotImplementedError()

    def on_connection_problem(self):
        raise NotImplementedError()

    def on_connection_failure(self):
        raise NotImplementedError()


class _DummyScanner:
    def __init__(self, servers=None):
        self._servers = list(servers) if servers is not None else []

    def scan(self):
        return list(self._servers)


class TestTcpClientLogic(TestCase):
    def test_create_chat_returns_tcp_chat(self):
        logic = TcpClientLogic(discovery_scanner=_DummyScanner())
        info = TcpChatInformation(uuid4(), "MyChat", "127.0.0.1", 51121)
        chat = logic.create_chat(info, online=True, port=0)
        self.assertIsInstance(chat, TcpChat)
        self.assertEqual(chat.get_chat_info().get_name(), "MyChat")
        self.assertEqual(chat.get_chat_info().get_port(), 51121)

    def test_create_chat_port_fallback_and_validation(self):
        logic = TcpClientLogic(discovery_scanner=_DummyScanner())
        info_with_zero_port = TcpChatInformation(uuid4(), "MyChat", "127.0.0.1", 0)
        chat = logic.create_chat(info_with_zero_port, online=True, port=51122)
        self.assertEqual(chat.get_chat_info().get_port(), 51122)

        with self.assertRaises(ValueError):
            logic.create_chat(info_with_zero_port, online=True, port=0)

    def test_create_chat_offline_not_implemented(self):
        logic = TcpClientLogic(discovery_scanner=_DummyScanner())
        info = TcpChatInformation(uuid4(), "MyChat", "127.0.0.1", 51121)
        with self.assertRaises(NotImplementedError):
            logic.create_chat(info, online=False, port=0)

    def test_search_server_returns_known_chats(self):
        logic = TcpClientLogic(discovery_scanner=_DummyScanner())
        info = TcpChatInformation(uuid4(), "MyChat", "127.0.0.1", 51121)
        chat = logic.create_chat(info, online=True, port=0)
        results = logic.search_server()
        self.assertEqual(len(results), 1)
        self.assertIs(results[0], chat)

    def test_search_server_merges_discovery_results(self):
        discovered = DiscoveredServer(
            server_id=uuid4(),
            server_name="discovered",
            host="127.0.0.1",
            port=51121,
            requires_password=False,
        )
        logic = TcpClientLogic(discovery_scanner=_DummyScanner([discovered]))
        results = logic.search_server()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get_chat_info().get_id(), discovered.server_id)
        self.assertEqual(results[0].get_chat_info().get_name(), discovered.server_name)

    def test_start_shutdown_flow_with_ui(self):
        logic = TcpClientLogic(discovery_scanner=_DummyScanner())
        ui = _DummyUI()
        logic.set_ui(ui)
        ui.set_logic(logic)
        logic.start()
        self.assertTrue(ui.started)
        logic.shutdown()
        self.assertTrue(ui.stopped)

    def test_shutdown_impl_leaves_known_chats(self):
        logic = TcpClientLogic(discovery_scanner=_DummyScanner())
        spy = _LeaveSpyChat()
        logic._known_chats.append(spy)
        logic.shutdown_impl()
        self.assertTrue(spy.left)
