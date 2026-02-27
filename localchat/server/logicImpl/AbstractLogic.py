from __future__ import annotations

from abc import abstractmethod
from ipaddress import IPv4Address, IPv6Address
from threading import RLock
from time import monotonic, time
from uuid import UUID, uuid4

from localchat.config.limits import MAX_CHAT_NAME_LENGTH
from localchat.net import (
    SerializableChatInformation,
    SerializableList,
    SerializableString,
    SerializableUUID,
    SerializableUserMessageList,
    read_exact,
)
from localchat.server.logic import Logic
from localchat.util import BinaryIOBase, ChatInformation, Role, User, UserMessage
from localchat.util.event import Event, EventHandler


_READY = 0
_RUNNING = 1
_STOPPING = 2
_STOPPED = 3


class _MutableChatInformation(ChatInformation):
    def __init__(self, chat_id: UUID, name: str, port: int = 0):
        super().__init__()
        self._chat_id = chat_id
        self._name = name
        self._port = port

    def get_id(self) -> UUID:
        return self._chat_id

    def get_name(self) -> str:
        return self._name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")

    def get_port(self) -> int:
        return self._port

    def set_name(self, name: str):
        self._name = name

    def set_port(self, port: int):
        self._port = port

    def set_id(self, chat_id: UUID):
        self._chat_id = chat_id


class _ServerUser(User):
    def __init__(self, user_id: UUID, name: str = "server"):
        super().__init__()
        self._id = user_id
        self._name = name

    def get_id(self) -> UUID:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")


class _ConcreteUserMessage(UserMessage):
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


class AbstractLogic(Logic):
    _STATE_VERSION = 0x0001_0000_0000_0000

    def __init__(self):
        super().__init__()
        self._lock = RLock()
        self._state = _READY
        self._started_at: float | None = None

        self._server_info = _MutableChatInformation(uuid4(), "localchat-server", 0)
        self._locked = False
        self._host_client_port: int | None = None

        self._members_by_id: dict[UUID, User] = {}
        self._roles_by_id: dict[UUID, Role] = {}
        self._host_user_id: UUID | None = None
        self._banned_user_ids: set[UUID] = set()

        self._chat_log: list[UserMessage] = []
        self._server_user = _ServerUser(uuid4())

        self._member_joined_handler: EventHandler[User] = EventHandler()
        self._member_left_handler: EventHandler[User] = EventHandler()
        self._member_role_changed_handler: EventHandler[User] = EventHandler()
        self._public_message_handler: EventHandler[UserMessage] = EventHandler()
        self._private_message_handler: EventHandler[UserMessage] = EventHandler()
        self._error_handler: EventHandler[IOError] = EventHandler()

    def _event_owner(self) -> UUID:
        return self._server_info.get_id()

    def _emit_error(self, error: IOError):
        self._error_handler.handle(Event(self._event_owner(), error))

    def _make_user_message(self, sender: User, message: str) -> UserMessage:
        return _ConcreteUserMessage(sender, message, time())

    def _register_member(self, user: User, role: Role):
        with self._lock:
            user_id = user.get_id()
            if user_id in self._banned_user_ids:
                raise PermissionError("user is banned")
            if self._locked and role != Role.HOST:
                raise PermissionError("server is locked")
            self._members_by_id[user_id] = user
            self._roles_by_id[user_id] = role
            if role == Role.HOST:
                self._host_user_id = user_id
        self._member_joined_handler.handle(Event(self._event_owner(), user))

    def register_member(self, user: User, role: Role = Role.MEMBER):
        self._register_member(user, role)

    def _unregister_member(self, user_id: UUID):
        removed: User | None = None
        with self._lock:
            removed = self._members_by_id.pop(user_id, None)
            self._roles_by_id.pop(user_id, None)
            if self._host_user_id == user_id:
                self._host_user_id = None
        if removed is not None:
            self._member_left_handler.handle(Event(self._event_owner(), removed))

    def _record_public_message(self, message: UserMessage):
        with self._lock:
            self._chat_log.append(message)
        self._public_message_handler.handle(Event(self._event_owner(), message))

    def _record_private_message(self, message: UserMessage):
        self._private_message_handler.handle(Event(self._event_owner(), message))

    def start(self):
        with self._lock:
            if self._state == _RUNNING or self._state == _STOPPING:
                raise RuntimeError("expected state: READY or STOPPED")
            self._state = _RUNNING
            self._started_at = monotonic()
        try:
            self._on_start_impl()
        except IOError as e:
            with self._lock:
                self._state = _STOPPED
            self._emit_error(e)
            raise

    def stop(self):
        with self._lock:
            if self._state != _RUNNING:
                raise RuntimeError("expected state: RUNNING")
            self._state = _STOPPING
            member_ids = list(self._members_by_id.keys())

        for member_id in member_ids:
            try:
                self._disconnect_member_impl(member_id, "server shutdown")
            except IOError as e:
                self._emit_error(e)
            finally:
                self._unregister_member(member_id)

        try:
            self._on_stop_impl()
        finally:
            with self._lock:
                self._state = _STOPPED

    def is_running(self) -> bool:
        with self._lock:
            return self._state == _RUNNING

    def get_uptime_seconds(self) -> float:
        with self._lock:
            if self._started_at is None or self._state == _READY:
                return 0.0
            return monotonic() - self._started_at

    def get_server_info(self) -> ChatInformation:
        with self._lock:
            return _MutableChatInformation(
                self._server_info.get_id(),
                self._server_info.get_name(),
                self._server_info.get_port(),
            )

    def set_server_name(self, new_name: str):
        if len(new_name) > MAX_CHAT_NAME_LENGTH or len(new_name) == 0:
            raise ValueError("invalid server name length")
        with self._lock:
            self._server_info.set_name(new_name)

    def set_server_password(self, new_password: str | None):
        # Password storage/validation policy is transport/security specific.
        self._set_server_password_impl(new_password)

    def set_locked(self, locked: bool):
        with self._lock:
            self._locked = locked

    def is_locked(self) -> bool:
        with self._lock:
            return self._locked

    def set_host_client_port(self, port: int):
        if port <= 0 or port > 65535:
            raise ValueError("port out of range")
        with self._lock:
            self._host_client_port = port

    def get_host_client_port(self) -> int | None:
        with self._lock:
            return self._host_client_port

    def list_members(self) -> list[User]:
        with self._lock:
            return list(self._members_by_id.values())

    def get_host_user(self) -> User:
        with self._lock:
            if self._host_user_id is None:
                raise RuntimeError("host is not set")
            return self._members_by_id[self._host_user_id]

    def get_user_role(self, user_id: UUID) -> Role:
        with self._lock:
            if user_id not in self._roles_by_id:
                raise KeyError("unknown user")
            return self._roles_by_id[user_id]

    def transfer_host(self, new_host_id: UUID):
        with self._lock:
            if new_host_id not in self._members_by_id:
                raise KeyError("unknown user")
            old_host_id = self._host_user_id
            if old_host_id == new_host_id:
                return
            if old_host_id is not None and old_host_id in self._roles_by_id:
                self._roles_by_id[old_host_id] = Role.MEMBER
            self._roles_by_id[new_host_id] = Role.HOST
            self._host_user_id = new_host_id
            old_host = self._members_by_id.get(old_host_id) if old_host_id else None
            new_host = self._members_by_id[new_host_id]
        if old_host is not None:
            self._member_role_changed_handler.handle(Event(self._event_owner(), old_host))
        self._member_role_changed_handler.handle(Event(self._event_owner(), new_host))

    def kick_member(self, user_id: UUID, reason: str = ""):
        with self._lock:
            if user_id not in self._members_by_id:
                raise KeyError("unknown user")
            if self._host_user_id == user_id:
                raise PermissionError("host cannot be kicked")
        self._disconnect_member_impl(user_id, reason)
        self._unregister_member(user_id)

    def ban_member(self, user_id: UUID, reason: str = ""):
        with self._lock:
            if user_id not in self._members_by_id:
                raise KeyError("unknown user")
            if self._host_user_id == user_id:
                raise PermissionError("host cannot be banned")
            self._banned_user_ids.add(user_id)
        self._disconnect_member_impl(user_id, reason)
        self._unregister_member(user_id)

    def unban_member(self, user_id: UUID):
        with self._lock:
            self._banned_user_ids.discard(user_id)

    def list_banned_users(self) -> set[UUID]:
        with self._lock:
            return set(self._banned_user_ids)

    def post_system_message(self, message: str):
        user_message = self._make_user_message(self._server_user, message)
        self._record_public_message(user_message)
        self._broadcast_public_impl(user_message)

    def send_system_private_message(self, recipient_id: UUID, message: str):
        with self._lock:
            if recipient_id not in self._members_by_id:
                raise KeyError("unknown user")
        user_message = self._make_user_message(self._server_user, message)
        self._record_private_message(user_message)
        self._send_private_impl(recipient_id, user_message)

    def save_chat(self, output_stream: BinaryIOBase):
        serial = SerializableUserMessageList()
        with self._lock:
            serial.items = list(self._chat_log)
        serial.serialize(output_stream)

    def export_state(self, output_stream: BinaryIOBase):
        with self._lock:
            state_info = SerializableChatInformation.create_copy(self._server_info)
            locked = self._locked
            host_client_port = self._host_client_port
            banned = list(self._banned_user_ids)
            host_user_id = self._host_user_id
            chat_log = list(self._chat_log)

        output_stream.write(self._STATE_VERSION.to_bytes(8, "big"))
        state_info.serialize(output_stream)
        output_stream.write((1 if locked else 0).to_bytes(1, "big"))
        output_stream.write((host_client_port if host_client_port is not None else 0).to_bytes(8, "big"))

        serial_banned = SerializableList()
        serial_banned.items = [SerializableUUID(banned_id) for banned_id in banned]
        serial_banned.serialize(output_stream)

        output_stream.write((1 if host_user_id is not None else 0).to_bytes(1, "big"))
        if host_user_id is not None:
            SerializableUUID(host_user_id).serialize(output_stream)

        serial_log = SerializableUserMessageList()
        serial_log.items = chat_log
        serial_log.serialize(output_stream)

    def import_state(self, input_stream: BinaryIOBase, merge: bool = False):
        version = int.from_bytes(read_exact(input_stream, 8), "big")
        if version != self._STATE_VERSION:
            raise IOError(f"unsupported state version: {hex(version)}")

        imported_info = SerializableChatInformation.deserialize(input_stream)
        imported_locked = bool(int.from_bytes(read_exact(input_stream, 1), "big"))
        imported_host_client_port = int.from_bytes(read_exact(input_stream, 8), "big")

        serial_banned = SerializableList.deserialize(input_stream, SerializableUUID.deserialize, 100_000)
        imported_banned = {serial.value for serial in serial_banned.items}

        host_present = bool(int.from_bytes(read_exact(input_stream, 1), "big"))
        imported_host_user_id: UUID | None = None
        if host_present:
            imported_host_user_id = SerializableUUID.deserialize(input_stream).value

        serial_log = SerializableUserMessageList.deserialize(input_stream, 100_000, 10_000_000)
        imported_chat_log = serial_log.items

        with self._lock:
            if merge:
                self._locked = self._locked or imported_locked
                if imported_host_client_port > 0:
                    self._host_client_port = imported_host_client_port
                self._banned_user_ids.update(imported_banned)
                self._chat_log.extend(imported_chat_log)
            else:
                self._server_info.set_id(imported_info.get_id())
                self._server_info.set_name(imported_info.get_name())
                self._locked = imported_locked
                self._host_client_port = imported_host_client_port if imported_host_client_port > 0 else None
                self._banned_user_ids = set(imported_banned)
                self._chat_log = list(imported_chat_log)

            if imported_host_user_id is not None and imported_host_user_id in self._members_by_id:
                old_host_id = self._host_user_id
                self._host_user_id = imported_host_user_id
                if old_host_id is not None and old_host_id in self._roles_by_id:
                    self._roles_by_id[old_host_id] = Role.MEMBER
                self._roles_by_id[imported_host_user_id] = Role.HOST

    def on_member_joined(self) -> EventHandler[User]:
        return self._member_joined_handler

    def on_member_left(self) -> EventHandler[User]:
        return self._member_left_handler

    def on_member_role_changed(self) -> EventHandler[User]:
        return self._member_role_changed_handler

    def on_public_message(self) -> EventHandler[UserMessage]:
        return self._public_message_handler

    def on_private_message(self) -> EventHandler[UserMessage]:
        return self._private_message_handler

    def on_error(self) -> EventHandler[IOError]:
        return self._error_handler

    @abstractmethod
    def _on_start_impl(self): ...

    @abstractmethod
    def _on_stop_impl(self): ...

    @abstractmethod
    def _disconnect_member_impl(self, user_id: UUID, reason: str): ...

    @abstractmethod
    def _broadcast_public_impl(self, user_message: UserMessage): ...

    @abstractmethod
    def _send_private_impl(self, recipient_id: UUID, user_message: UserMessage): ...

    @abstractmethod
    def _set_server_password_impl(self, new_password: str | None): ...
