from __future__ import annotations

from socket import (
    AF_INET,
    SOCK_DGRAM,
    SOL_SOCKET,
    SO_BROADCAST,
    SO_REUSEADDR,
    socket,
)
from threading import Event as ThreadEvent, Thread
from time import monotonic
from typing import Callable
from uuid import uuid4

from localchat.config.defaults import BUFFER_SIZE, DEFAULT_HOST, DISCOVERY_PORT
from localchat.net.discovery.base import DiscoveryResponder, DiscoveryScanner
from localchat.net.discovery.models import DiscoveredServer
from localchat.net.discovery.protocol import (
    DiscoveryRequest,
    DiscoveryResponse,
    decode_discovery_request,
    decode_discovery_response,
    encode_discovery_request,
    encode_discovery_response,
)


class UdpBroadcastDiscoveryScanner(DiscoveryScanner):
    def __init__(
        self,
        request_port: int = DISCOVERY_PORT,
        broadcast_address: str = "255.255.255.255",
        timeout_s: float = 0.7,
        buffer_size: int = BUFFER_SIZE,
    ):
        self._request_port = request_port
        self._broadcast_address = broadcast_address
        self._timeout_s = timeout_s
        self._buffer_size = buffer_size

    def scan(self) -> list[DiscoveredServer]:
        nonce = uuid4()

        recv_sock = socket(AF_INET, SOCK_DGRAM)
        recv_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        recv_sock.bind((DEFAULT_HOST, 0))
        recv_sock.settimeout(0.05)
        reply_port = recv_sock.getsockname()[1]

        send_sock = socket(AF_INET, SOCK_DGRAM)
        send_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

        try:
            request = DiscoveryRequest(nonce=nonce, reply_port=reply_port)
            payload = encode_discovery_request(request)
            send_sock.sendto(payload, (self._broadcast_address, self._request_port))

            deadline = monotonic() + self._timeout_s
            by_server_id: dict[str, DiscoveredServer] = {}
            while monotonic() < deadline:
                try:
                    data, _addr = recv_sock.recvfrom(self._buffer_size)
                except TimeoutError:
                    continue
                try:
                    response = decode_discovery_response(data)
                except IOError:
                    continue
                if response.nonce != nonce:
                    continue
                by_server_id[str(response.server.server_id)] = response.server

            return list(by_server_id.values())
        except OSError as e:
            raise IOError("failed to scan for discovery responses") from e
        finally:
            recv_sock.close()
            send_sock.close()


class UdpBroadcastDiscoveryResponder(DiscoveryResponder):
    def __init__(
        self,
        snapshot_provider: Callable[[], DiscoveredServer],
        request_port: int = DISCOVERY_PORT,
        bind_host: str = DEFAULT_HOST,
        buffer_size: int = BUFFER_SIZE,
    ):
        self._snapshot_provider = snapshot_provider
        self._request_port = request_port
        self._bind_host = bind_host
        self._buffer_size = buffer_size

        self._sock: socket | None = None
        self._thread: Thread | None = None
        self._stop_event = ThreadEvent()
        self._running = False

    def start(self):
        if self._running:
            return
        try:
            sock = socket(AF_INET, SOCK_DGRAM)
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            sock.bind((self._bind_host, self._request_port))
            sock.settimeout(0.1)
        except OSError as e:
            raise IOError("failed to start discovery responder") from e

        self._sock = sock
        self._stop_event.clear()
        self._running = True
        self._thread = Thread(target=self._loop, name="localchat discovery responder", daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._stop_event.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _loop(self):
        while not self._stop_event.is_set():
            sock = self._sock
            if sock is None:
                return
            try:
                data, addr = sock.recvfrom(self._buffer_size)
            except TimeoutError:
                continue
            except OSError:
                return

            try:
                request = decode_discovery_request(data)
            except IOError:
                continue

            try:
                snapshot = self._snapshot_provider()
                advertised_host = snapshot.host
                if advertised_host == "0.0.0.0":
                    advertised_host = _guess_local_ip_for_peer(addr[0])
                response = DiscoveryResponse(
                    nonce=request.nonce,
                    server=DiscoveredServer(
                        server_id=snapshot.server_id,
                        server_name=snapshot.server_name,
                        host=advertised_host,
                        port=snapshot.port,
                        requires_password=snapshot.requires_password,
                    ),
                )
                payload = encode_discovery_response(response)
                sock.sendto(payload, (addr[0], request.reply_port))
            except Exception:
                continue


def _guess_local_ip_for_peer(peer_ip: str) -> str:
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect((peer_ip, 1))
        local_ip = s.getsockname()[0]
        if not isinstance(local_ip, str) or len(local_ip) == 0:
            return "127.0.0.1"
        return local_ip
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
