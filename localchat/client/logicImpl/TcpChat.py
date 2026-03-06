from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, ip_address
from socket import AF_INET, SOCK_STREAM, gaierror, gethostbyname, socket
from threading import Event as ThreadEvent, Lock, Thread
from time import time
from uuid import UUID

from localchat.client.logicImpl import AbstractChat
from localchat.config.limits import MAX_MESSAGE_LENGTH
from localchat.net import SerializableString, SerializableUser, SerializableUserMessage, tcp_protocol
from localchat.util import BinaryIOBase, ChatInformation, User, UserMessage
from localchat.util.event import Event


class _TcpChatInformation(ChatInformation):
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
        try:
            return ip_address(self._host)
        except ValueError:
            try:
                resolved_host = gethostbyname(self._host)
                return ip_address(resolved_host)
            except (gaierror, ValueError) as e:
                raise ValueError(f"could not resolve host '{self._host}'") from e

    def get_port(self) -> int:
        return self._port

    def set_name(self, name: str):
        self._name = name

    def get_host(self) -> str:
        return self._host


class _TcpUserMessage(UserMessage):
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


class TcpChat(AbstractChat):
    def __init__(self, chat_id: UUID, chat_name: str, host: str, port: int):
        super().__init__()
        self._chat_info = _TcpChatInformation(chat_id, chat_name, host, port)
        self._server_user = SerializableUser(chat_id, "server")
        self._members_by_id: dict[UUID, User] = {}
        self._appearance: User | None = None

        self._socket: socket | None = None
        self._recv_thread: Thread | None = None
        self._recv_stop = ThreadEvent()
        self._send_lock = Lock()
        self._joined = False

    def get_chat_info(self) -> ChatInformation:
        return _TcpChatInformation(
            self._chat_info.get_id(),
            self._chat_info.get_name(),
            str(self._chat_info.get_ip_address()),
            self._chat_info.get_port(),
        )

    def set_chat_info(self, chat_info: ChatInformation):
        with self._lock:
            self._chat_info.set_name(chat_info.get_name())

    def join(self, appearance: User):
        with self._lock:
            if self._joined:
                return
            self._appearance = appearance
            host = self._chat_info.get_host()
            port = self._chat_info.get_port()

        sock = socket(AF_INET, SOCK_STREAM)
        try:
            sock.connect((host, port))
            self._send_packet(sock, tcp_protocol.encode_join(appearance))
        except OSError as e:
            sock.close()
            raise IOError("failed to connect/join chat") from e

        with self._lock:
            self._socket = sock
            self._joined = True
            self._recv_stop.clear()
            self._recv_thread = Thread(target=self._recv_loop, name=f"tcp chat recv {host}:{port}", daemon=True)
            self._recv_thread.start()

    def leave(self):
        with self._lock:
            if not self._joined:
                return
            sock = self._socket
            self._joined = False
            self._recv_stop.set()
            recv_thread = self._recv_thread
            self._socket = None
            self._recv_thread = None

        if sock is not None:
            try:
                self._send_packet(sock, tcp_protocol.encode_leave())
            except Exception:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if recv_thread is not None and recv_thread.is_alive():
            recv_thread.join(timeout=1.0)

    def update_appearance(self, appearance: User):
        with self._lock:
            if not self._joined:
                raise RuntimeError("user is not a member of the chat")
            self._appearance = appearance
        # v0 protocol has no appearance update packet yet.

    def post_message(self, message: str):
        with self._lock:
            if not self._joined or self._socket is None:
                raise RuntimeError("user is not a member of the chat")
            sock = self._socket
        self._send_packet(sock, tcp_protocol.encode_public_message(message))

    def send_private_message(self, recipient: User, message: str):
        with self._lock:
            if not self._joined or self._socket is None:
                raise RuntimeError("user is not a member of the chat")
            sock = self._socket
        self._send_packet(sock, tcp_protocol.encode_private_message(recipient.get_id(), message))

    def download_chat(self, output_stream: BinaryIOBase):
        raise NotImplementedError()

    def get_server_user(self) -> User:
        return self._server_user

    def _recv_loop(self):
        while not self._recv_stop.is_set():
            with self._lock:
                sock = self._socket
            if sock is None:
                return
            try:
                payload = tcp_protocol.recv_packet(sock)
                packet_type, body = tcp_protocol.decode_client_packet(payload)
                self._handle_packet(packet_type, body)
            except IOError as e:
                if self._recv_stop.is_set():
                    return
                self.on_connection_failure().handle(Event(self._chat_info.get_id(), e))
                self._recv_stop.set()
                with self._lock:
                    self._joined = False
                    try:
                        if self._socket is not None:
                            self._socket.close()
                    except OSError:
                        pass
                    self._socket = None
                return

    def _handle_packet(self, packet_type: int, body):
        chat_id = self._chat_info.get_id()
        if packet_type == tcp_protocol.PT_S_USER_JOINED:
            user = SerializableUser.deserialize(body)
            self._members_by_id[user.get_id()] = user
            self.on_user_joined().handle(Event(chat_id, user))
            return

        if packet_type == tcp_protocol.PT_S_USER_LEFT:
            user = SerializableUser.deserialize(body)
            self._members_by_id.pop(user.get_id(), None)
            self.on_user_left().handle(Event(chat_id, user))
            return

        if packet_type == tcp_protocol.PT_S_USER_BECAME_HOST:
            user = SerializableUser.deserialize(body)
            self._members_by_id[user.get_id()] = user
            self.on_user_became_host().handle(Event(chat_id, user))
            return

        if packet_type == tcp_protocol.PT_S_PUBLIC:
            message = SerializableUserMessage.deserialize(body)
            self._members_by_id[message.sender().get_id()] = message.sender()
            self.on_user_posted_message().handle(Event(chat_id, message))
            return

        if packet_type == tcp_protocol.PT_S_PRIVATE:
            message = SerializableUserMessage.deserialize(body)
            self._members_by_id[message.sender().get_id()] = message.sender()
            self.on_user_send_private_message().handle(Event(chat_id, message))
            return

        if packet_type == tcp_protocol.PT_S_ERROR:
            msg = SerializableString.deserialize(body, MAX_MESSAGE_LENGTH).value
            sys_msg = _TcpUserMessage(self._server_user, msg, time())
            self.on_user_send_private_message().handle(Event(chat_id, sys_msg))
            return

        raise IOError(f"unknown packet type: {packet_type}")

    def _send_packet(self, sock: socket, payload: bytes):
        try:
            with self._send_lock:
                tcp_protocol.send_packet(sock, payload)
        except OSError as e:
            raise IOError("failed to send packet") from e
