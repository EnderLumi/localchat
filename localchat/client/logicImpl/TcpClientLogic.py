from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, ip_address
from threading import RLock
from uuid import UUID, uuid4

from localchat.client.logicImpl import AbstractChat, AbstractLogic, TcpChat
from localchat.util import BinaryIOBase, Chat, ChatInformation, User


class TcpChatInformation(ChatInformation):
    def __init__(self, chat_id: UUID, name: str, host: str, port: int):
        super().__init__()
        self._id = chat_id
        self._name = name
        self._host = host
        self._port = port

    def get_id(self) -> UUID:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return ip_address(self._host)

    def get_port(self) -> int:
        return self._port


class _SystemUser(User):
    def __init__(self):
        super().__init__()
        self._id = uuid4()

    def get_id(self) -> UUID:
        return self._id

    def get_name(self) -> str:
        return "system"

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")


class _SystemChat(AbstractChat):
    def __init__(self):
        super().__init__()
        self._info = TcpChatInformation(uuid4(), "system", "127.0.0.1", 0)
        self._joined = False
        self._server_user = _SystemUser()

    def get_chat_info(self) -> ChatInformation:
        return self._info

    def set_chat_info(self, chat_info: ChatInformation):
        return

    def join(self, appearance: User):
        self._joined = True

    def leave(self):
        self._joined = False

    def update_appearance(self, appearance: User):
        if not self._joined:
            raise RuntimeError("user is not a member of the chat")

    def post_message(self, message: str):
        if not self._joined:
            raise RuntimeError("user is not a member of the chat")

    def send_private_message(self, recipient: User, message: str):
        if not self._joined:
            raise RuntimeError("user is not a member of the chat")

    def download_chat(self, output_stream: BinaryIOBase):
        raise NotImplementedError()

    def get_server_user(self) -> User:
        return self._server_user


class TcpClientLogic(AbstractLogic):
    """
    TCP-backed client logic implementation.
    Keeps UI decoupled from transport details and manages TcpChat instances.
    """

    def __init__(self):
        super().__init__()
        self._lock = RLock()
        self._system_chat = _SystemChat()
        self._known_chats: list[Chat] = []

    def start_impl(self):
        # v0 does not require a long-running background loop in client logic.
        return

    def shutdown_impl(self):
        with self._lock:
            chats = list(self._known_chats)
            self._known_chats = []
        for chat in chats:
            try:
                chat.leave()
            except Exception:
                pass

    def create_chat(self, info: ChatInformation, online: bool, port: int) -> Chat:
        if not online:
            raise NotImplementedError("offline chats are not implemented in TcpClientLogic")

        host = str(info.get_ip_address())
        target_port = info.get_port() if info.get_port() > 0 else port
        if target_port <= 0 or target_port > 65535:
            raise ValueError("invalid port")

        chat = TcpChat(info.get_id(), info.get_name(), host, target_port)
        with self._lock:
            self._known_chats.append(chat)
        return chat

    def load_chat(self, input_stream: BinaryIOBase, online: bool, port: int) -> Chat:
        raise NotImplementedError()

    def search_server(self) -> list[Chat]:
        # Discovery integration will populate this list.
        with self._lock:
            return list(self._known_chats)

    def get_system_chat(self) -> Chat:
        return self._system_chat
