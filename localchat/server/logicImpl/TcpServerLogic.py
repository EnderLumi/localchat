from __future__ import annotations

from dataclasses import dataclass
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, socket
from threading import Lock, Thread
from uuid import UUID, uuid4

from localchat.config.defaults import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_MAX_CLIENTS, HARD_MAX_CLIENTS
from localchat.config.limits import JOIN_TIMEOUT_S
from localchat.net import SerializableUser
from localchat.net.discovery import DiscoveredServer, UdpBroadcastDiscoveryResponder
from localchat.net import tcp_protocol
from localchat.server.commands import ServerCommandDispatcher
from localchat.server.logicImpl.AbstractLogic import AbstractLogic
from localchat.util import User, UserMessage
from localchat.util.event import Event, EventListener


@dataclass
class _Session:
    sock: socket
    addr: tuple[str, int]
    send_lock: Lock
    user_id: UUID | None = None


class _SendUserEventToClients(EventListener[User]):
    def __init__(self, outer: "TcpServerLogic", encoder):
        self._outer = outer
        self._encoder = encoder

    def on_event(self, event: Event[User]):
        user = event.value()
        self._outer._broadcast_payload(self._encoder(user))


class TcpServerLogic(AbstractLogic):
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        max_clients: int = DEFAULT_MAX_CLIENTS,
    ):
        super().__init__()
        if max_clients <= 0 or max_clients > HARD_MAX_CLIENTS:
            raise ValueError(f"max_clients must be in range 1..{HARD_MAX_CLIENTS}")
        self._host = host
        self._port = port
        self._max_clients = max_clients
        self._password: str | None = None
        self._listener: socket | None = None
        self._accept_thread: Thread | None = None
        self._accept_running = False
        self._sessions_lock = Lock()
        self._sessions_by_user_id: dict[UUID, _Session] = {}
        self._sessions_without_user: list[_Session] = []
        self._discovery_responder = UdpBroadcastDiscoveryResponder(
            snapshot_provider=self._discovery_snapshot,
            bind_host=self._host,
        )
        self._command_dispatcher = ServerCommandDispatcher(self)

        self.on_member_joined().add_listener(
            _SendUserEventToClients(self, tcp_protocol.encode_server_user_joined)
        )
        self.on_member_left().add_listener(
            _SendUserEventToClients(self, tcp_protocol.encode_server_user_left)
        )
        self.on_member_role_changed().add_listener(
            _SendUserEventToClients(self, tcp_protocol.encode_server_user_became_host)
        )

    def _on_start_impl(self):
        listener = socket(AF_INET, SOCK_STREAM)
        listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        listener.bind((self._host, self._port))
        listener.listen()
        actual_port = int(listener.getsockname()[1])

        self._listener = listener
        self._accept_running = True
        with self._lock:
            self._port = actual_port
            self._server_info.set_port(actual_port)
        self._accept_thread = Thread(target=self._accept_loop, name="localchat tcp accept loop", daemon=True)
        self._accept_thread.start()
        try:
            self._discovery_responder.start()
        except IOError as e:
            # Discovery is optional metadata transport; TCP chat should still run.
            self._emit_error(e)

    def _on_stop_impl(self):
        self._discovery_responder.stop()
        self._accept_running = False
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
            self._listener = None
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=1.0)
            self._accept_thread = None

    def _accept_loop(self):
        while self._accept_running:
            listener = self._listener
            if listener is None:
                return
            try:
                client_sock, addr = listener.accept()
            except OSError:
                return
            with self._sessions_lock:
                active_sessions = len(self._sessions_by_user_id) + len(self._sessions_without_user)
            if active_sessions >= self._max_clients:
                try:
                    tcp_protocol.send_packet(
                        client_sock,
                        tcp_protocol.encode_server_join_nack(
                            tcp_protocol.ERR_SERVER_FULL,
                            "server is full",
                        ),
                    )
                except Exception:
                    pass
                try:
                    client_sock.close()
                except OSError:
                    pass
                continue
            session = _Session(client_sock, addr, Lock())
            with self._sessions_lock:
                self._sessions_without_user.append(session)
            thread = Thread(target=self._client_loop, args=(session,), name=f"localchat tcp client {addr}", daemon=True)
            thread.start()

    def _client_loop(self, session: _Session):
        try:
            session.sock.settimeout(JOIN_TIMEOUT_S)
            joined = False
            while True:
                payload = tcp_protocol.recv_packet(session.sock)
                packet_type, body = tcp_protocol.decode_client_packet(payload)
                if packet_type == tcp_protocol.PT_C_JOIN:
                    joined = True
                    session.sock.settimeout(None)
                    if session.user_id is not None:
                        self._send_to_session(
                            session,
                            tcp_protocol.encode_server_error(
                                tcp_protocol.ERR_ALREADY_JOINED,
                                "already joined",
                            ),
                        )
                        continue
                    requested_user = tcp_protocol.decode_join(body)
                    if self._is_name_in_use(requested_user.get_name()):
                        self._send_to_session(
                            session,
                            tcp_protocol.encode_server_join_nack(
                                tcp_protocol.ERR_USER_NAME_IN_USE,
                                "user name already in use",
                            ),
                        )
                        continue
                    user = self._new_session_user(requested_user.get_name())
                    session_user_id = user.get_id()
                    with self._sessions_lock:
                        if session in self._sessions_without_user:
                            self._sessions_without_user.remove(session)
                        self._sessions_by_user_id[session_user_id] = session
                    session.user_id = session_user_id
                    try:
                        self._register_member_auto_role(user)
                        self._send_to_session(session, tcp_protocol.encode_server_join_ack(user))
                    except PermissionError as e:
                        reason = str(e) if len(str(e)) > 0 else "join rejected"
                        self._reject_join(
                            session,
                            session_user_id,
                            tcp_protocol.ERR_JOIN_REJECTED,
                            reason,
                        )
                        continue
                    except Exception:
                        self._reject_join(
                            session,
                            session_user_id,
                            tcp_protocol.ERR_JOIN_FAILED,
                            "join failed",
                        )
                        continue
                elif packet_type == tcp_protocol.PT_C_PUBLIC:
                    if session.user_id is None:
                        self._send_to_session(
                            session,
                            tcp_protocol.encode_server_error(
                                tcp_protocol.ERR_JOIN_FIRST,
                                "join first",
                            ),
                        )
                        continue
                    message = tcp_protocol.decode_public_message(body)
                    sender = self._get_member_by_id(session.user_id)
                    user_message = self._make_user_message(sender, message)
                    self._record_public_message(user_message)
                    self._broadcast_public_impl(user_message)
                elif packet_type == tcp_protocol.PT_C_PRIVATE:
                    if session.user_id is None:
                        self._send_to_session(
                            session,
                            tcp_protocol.encode_server_error(
                                tcp_protocol.ERR_JOIN_FIRST,
                                "join first",
                            ),
                        )
                        continue
                    recipient, message = tcp_protocol.decode_private_message(body)
                    try:
                        sender = self._get_member_by_id(session.user_id)
                    except KeyError:
                        self._send_to_session(
                            session,
                            tcp_protocol.encode_server_error(
                                tcp_protocol.ERR_JOIN_FIRST,
                                "join first",
                            ),
                        )
                        continue
                    user_message = self._make_user_message(sender, message)
                    if recipient.value == self._get_server_user_id():
                        handled = self._command_dispatcher.try_execute(session.user_id, message)
                        if not handled:
                            self._send_to_session(
                                session,
                                tcp_protocol.encode_server_error(
                                    tcp_protocol.ERR_UNKNOWN_COMMAND,
                                    "server command expected, prefix with '/'",
                                ),
                            )
                        continue
                    try:
                        self._send_private_impl(recipient.value, user_message)
                    except KeyError:
                        self._send_to_session(
                            session,
                            tcp_protocol.encode_server_error(
                                tcp_protocol.ERR_UNKNOWN_RECIPIENT,
                                "unknown recipient",
                            ),
                        )
                        continue
                    self._record_private_message(user_message)
                elif packet_type == tcp_protocol.PT_C_LEAVE:
                    return
                else:
                    self._send_to_session(
                        session,
                        tcp_protocol.encode_server_error(
                            tcp_protocol.ERR_UNKNOWN_PACKET_TYPE,
                            "unknown packet type",
                        ),
                    )
        except TimeoutError:
            if not joined:
                try:
                    self._send_to_session(
                        session,
                        tcp_protocol.encode_server_join_nack(
                            tcp_protocol.ERR_JOIN_TIMEOUT,
                            "join timeout",
                        ),
                    )
                except Exception:
                    pass
        except IOError:
            pass
        finally:
            self._close_session(session)

    def _get_member_by_id(self, user_id: UUID) -> User:
        for user in self.list_members():
            if user.get_id() == user_id:
                return user
        raise KeyError("unknown user")

    def _close_session(self, session: _Session):
        user_id = session.user_id
        with self._sessions_lock:
            if session in self._sessions_without_user:
                self._sessions_without_user.remove(session)
            if user_id is not None and user_id in self._sessions_by_user_id:
                self._sessions_by_user_id.pop(user_id, None)

        try:
            session.sock.close()
        except OSError:
            pass

        if user_id is not None:
            try:
                self._unregister_member(user_id)
            except Exception:
                pass

    def _reject_join(self, session: _Session, session_user_id: UUID, code: str, reason: str):
        with self._sessions_lock:
            self._sessions_by_user_id.pop(session_user_id, None)
            if session not in self._sessions_without_user:
                self._sessions_without_user.append(session)
        session.user_id = None
        try:
            self._send_to_session(session, tcp_protocol.encode_server_join_nack(code, reason))
        except IOError:
            # Connection handling stays in the main loop / finally cleanup.
            pass

    def _disconnect_member_impl(self, user_id: UUID, reason: str):
        with self._sessions_lock:
            session = self._sessions_by_user_id.get(user_id)
        if session is None:
            return
        try:
            self._send_to_session(
                session,
                tcp_protocol.encode_server_error(
                    tcp_protocol.ERR_DISCONNECTED,
                    reason if reason else "disconnected",
                ),
            )
        except Exception:
            pass
        try:
            session.sock.close()
        except OSError:
            pass

    def _broadcast_public_impl(self, user_message: UserMessage):
        payload = tcp_protocol.encode_server_public_message(user_message)
        self._broadcast_payload(payload)

    def _send_private_impl(self, recipient_id: UUID, user_message: UserMessage):
        with self._sessions_lock:
            recipient = self._sessions_by_user_id.get(recipient_id)
        if recipient is None:
            raise KeyError("unknown user")
        payload = tcp_protocol.encode_server_private_message(user_message)
        self._send_to_session(recipient, payload)

    def _set_server_password_impl(self, new_password: str | None):
        self._password = new_password

    def _discovery_snapshot(self) -> DiscoveredServer:
        info = self.get_server_info()
        return DiscoveredServer(
            server_id=info.get_id(),
            server_name=info.get_name(),
            host=self._host,
            port=self._port,
            requires_password=self._password is not None,
        )

    def _broadcast_payload(self, payload: bytes):
        with self._sessions_lock:
            sessions = list(self._sessions_by_user_id.values())
        failed_sessions: list[_Session] = []
        for session in sessions:
            try:
                self._send_to_session(session, payload)
            except (IOError, OSError) as e:
                self._emit_error(e)
                failed_sessions.append(session)
        for session in failed_sessions:
            self._close_session(session)

    @staticmethod
    def _send_to_session(session: _Session, payload: bytes):
        with session.send_lock:
            tcp_protocol.send_packet(session.sock, payload)

    def _new_session_user(self, name: str) -> SerializableUser:
        while True:
            candidate_id = uuid4()
            with self._sessions_lock:
                if candidate_id in self._sessions_by_user_id:
                    continue
            return SerializableUser(candidate_id, name)

    def _is_name_in_use(self, name: str) -> bool:
        normalized = name.strip().lower()
        if len(normalized) == 0:
            return False
        with self._sessions_lock:
            members = list(self._sessions_by_user_id.keys())
        for user_id in members:
            try:
                user = self._get_member_by_id(user_id)
            except KeyError:
                continue
            if user.get_name().strip().lower() == normalized:
                return True
        return False
