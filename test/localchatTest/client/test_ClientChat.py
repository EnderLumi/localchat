from contextlib import redirect_stdout
from io import StringIO
from threading import RLock
from unittest import TestCase
from uuid import UUID, uuid4

from localchat.client.UIImpl.simple import SimpleChatUI
from localchat.client.logicImpl import AbstractChat
from localchat.util import BinaryIOBase, ChatInformation, User, UserMessage
from localchat.util.event import Event


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


class _DummyChat(AbstractChat):
    def __init__(self):
        super().__init__()
        self._lock = RLock()
        self._chat_id = uuid4()
        self._chat_info = _DummyChatInfo(self._chat_id, "dummy")
        self._server_user = _DummyUser(uuid4(), "server")
        self._joined = False
        self._last_posted_message: str | None = None
        self._appearance: User | None = None
        self.fail_join = False

    def get_chat_info(self) -> ChatInformation:
        return self._chat_info

    def set_chat_info(self, chat_info: ChatInformation):
        return

    def join(self, appearance: User):
        if self.fail_join:
            raise IOError("join failed")
        self._joined = True
        self._appearance = appearance

    def leave(self):
        self._joined = False
        self._appearance = None

    def update_appearance(self, appearance: User):
        if not self._joined:
            raise RuntimeError("not joined")
        self._appearance = appearance

    def post_message(self, message: str):
        if not self._joined:
            raise RuntimeError("not joined")
        self._last_posted_message = message

    def send_private_message(self, recipient: User, message: str):
        return

    def download_chat(self, output_stream: BinaryIOBase):
        raise NotImplementedError()

    def get_server_user(self) -> User:
        return self._server_user


class TestClientChat(TestCase):
    def test_simple_chat_ui_receives_events_only_when_joined(self):
        chat = _DummyChat()
        ui = SimpleChatUI(chat)
        appearance = _DummyUser(uuid4(), "me")
        sender = _DummyUser(uuid4(), "Alice")
        msg = _DummyMessage(sender, "hello", 1.0)

        out = StringIO()
        with redirect_stdout(out):
            ui.join(appearance)
            chat.on_user_posted_message().handle(Event(chat.get_chat_info().get_id(), msg))
            ui.leave()
            chat.on_user_posted_message().handle(Event(chat.get_chat_info().get_id(), msg))

        output = out.getvalue()
        self.assertIn("Alice said: hello", output)
        self.assertEqual(output.count("Alice said: hello"), 1)

    def test_simple_chat_ui_say_command_calls_post_message(self):
        chat = _DummyChat()
        ui = SimpleChatUI(chat)
        appearance = _DummyUser(uuid4(), "me")
        ui.join(appearance)

        ui.on_event(Event(uuid4(), "say hello world"))
        self.assertEqual(chat._last_posted_message, "hello world")
        ui.leave()

    def test_simple_chat_ui_failed_join_deactivates_listeners(self):
        chat = _DummyChat()
        chat.fail_join = True
        ui = SimpleChatUI(chat)
        appearance = _DummyUser(uuid4(), "me")

        with self.assertRaises(IOError):
            ui.join(appearance)

        out = StringIO()
        sender = _DummyUser(uuid4(), "Alice")
        msg = _DummyMessage(sender, "hello", 1.0)
        with redirect_stdout(out):
            chat.on_user_posted_message().handle(Event(chat.get_chat_info().get_id(), msg))
        self.assertEqual(out.getvalue(), "")

    def test_abstract_chat_clear_handlers_removes_listeners(self):
        chat = _DummyChat()
        ui = SimpleChatUI(chat)
        appearance = _DummyUser(uuid4(), "me")
        ui.join(appearance)
        chat.clear_handlers()

        out = StringIO()
        sender = _DummyUser(uuid4(), "Alice")
        msg = _DummyMessage(sender, "hello", 1.0)
        with redirect_stdout(out):
            chat.on_user_posted_message().handle(Event(chat.get_chat_info().get_id(), msg))
        self.assertEqual(out.getvalue(), "")
