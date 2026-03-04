from __future__ import annotations

from dataclasses import dataclass
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, socket
from threading import Lock, Thread
from uuid import UUID

from localchat.config.defaults import DEFAULT_HOST, DEFAULT_PORT
from localchat.net.discovery import DiscoveredServer, UdpBroadcastDiscoveryResponder
from localchat.net import tcp_protocol
from localchat.server.logicImpl.AbstractLogic import AbstractLogic
from localchat.util import Role, User, UserMessage
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
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        super().__init__()
        self._host = host
        self._port = port
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

        self._listener = listener
        self._accept_running = True
        with self._lock:
            self._server_info.set_port(self._port)
        self._accept_thread = Thread(target=self._accept_loop, name="localchat tcp accept loop", daemon=True)
        self._accept_thread.start()
        self._discovery_responder.start()

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
            session = _Session(client_sock, addr, Lock())
            with self._sessions_lock:
                self._sessions_without_user.append(session)
            thread = Thread(target=self._client_loop, args=(session,), name=f"localchat tcp client {addr}", daemon=True)
            thread.start()

    def _client_loop(self, session: _Session):
        try:
            while True:
                payload = tcp_protocol.recv_packet(session.sock)
                packet_type, body = tcp_protocol.decode_client_packet(payload)
                if packet_type == tcp_protocol.PT_C_JOIN:
                    if session.user_id is not None:
                        self._send_to_session(session, tcp_protocol.encode_server_error("already joined"))
                        continue
                    serial_user = tcp_protocol.decode_join(body)
                    user = serial_user
                    role = Role.HOST if len(self.list_members()) == 0 else Role.MEMBER
                    session_user_id = user.get_id()
                    session.user_id = session_user_id
                    with self._sessions_lock:
                        if session in self._sessions_without_user:
                            self._sessions_without_user.remove(session)
                        self._sessions_by_user_id[session_user_id] = session
                    try:
                        self.register_member(user, role)
                    except Exception:
                        with self._sessions_lock:
                            self._sessions_by_user_id.pop(session_user_id, None)
                            self._sessions_without_user.append(session)
                        session.user_id = None
                        raise
                elif packet_type == tcp_protocol.PT_C_PUBLIC:
                    if session.user_id is None:
                        self._send_to_session(session, tcp_protocol.encode_server_error("join first"))
                        continue
                    message = tcp_protocol.decode_public_message(body)
                    sender = self._get_member_by_id(session.user_id)
                    user_message = self._make_user_message(sender, message)
                    self._record_public_message(user_message)
                    self._broadcast_public_impl(user_message)
                elif packet_type == tcp_protocol.PT_C_PRIVATE:
                    if session.user_id is None:
                        self._send_to_session(session, tcp_protocol.encode_server_error("join first"))
                        continue
                    recipient, message = tcp_protocol.decode_private_message(body)
                    sender = self._get_member_by_id(session.user_id)
                    user_message = self._make_user_message(sender, message)
                    self._record_private_message(user_message)
                    self._send_private_impl(recipient.value, user_message)
                elif packet_type == tcp_protocol.PT_C_LEAVE:
                    return
                else:
                    self._send_to_session(session, tcp_protocol.encode_server_error("unknown packet type"))
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

    def _disconnect_member_impl(self, user_id: UUID, reason: str):
        with self._sessions_lock:
            session = self._sessions_by_user_id.get(user_id)
        if session is None:
            return
        try:
            self._send_to_session(session, tcp_protocol.encode_server_error(reason if reason else "disconnected"))
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
        for session in sessions:
            try:
                self._send_to_session(session, payload)
            except IOError as e:
                self._emit_error(e)

    @staticmethod
    def _send_to_session(session: _Session, payload: bytes):
        with session.send_lock:
            tcp_protocol.send_packet(session.sock, payload)
