from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, ip_address
from threading import RLock
from uuid import UUID, uuid4

from localchat.client.logicImpl import AbstractChat, AbstractLogic, TcpChat
from localchat.net.discovery import DiscoveryScanner, UdpBroadcastDiscoveryScanner
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

    def __init__(self, discovery_scanner: DiscoveryScanner | None = None):
        super().__init__()
        self._lock = RLock()
        self._system_chat = _SystemChat()
        self._known_chats: list[Chat] = []
        self._discovery_scanner = discovery_scanner if discovery_scanner is not None else UdpBroadcastDiscoveryScanner()

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

    def connect_direct(self, host: str, port: int, chat_name: str | None = None) -> Chat:
        host = host.strip()
        if len(host) == 0:
            raise ValueError("invalid host")
        if port <= 0 or port > 65535:
            raise ValueError("invalid port")

        name = chat_name if chat_name is not None and len(chat_name) > 0 else f"direct-{host}:{port}"
        chat = TcpChat(uuid4(), name, host, port)
        with self._lock:
            self._known_chats.append(chat)
        return chat

    def load_chat(self, input_stream: BinaryIOBase, online: bool, port: int) -> Chat:
        raise NotImplementedError()

    def search_server(self) -> list[Chat]:
        discovered = self._discovery_scanner.scan()
        with self._lock:
            by_chat_id: dict[UUID, Chat] = {
                chat.get_chat_info().get_id(): chat
                for chat in self._known_chats
            }
            for server in discovered:
                if server.server_id in by_chat_id:
                    continue
                info = TcpChatInformation(
                    server.server_id,
                    server.server_name,
                    server.host,
                    server.port,
                )
                by_chat_id[server.server_id] = TcpChat(
                    info.get_id(),
                    info.get_name(),
                    str(info.get_ip_address()),
                    info.get_port(),
                )
            self._known_chats = list(by_chat_id.values())
            return list(self._known_chats)

    def get_system_chat(self) -> Chat:
        return self._system_chat
