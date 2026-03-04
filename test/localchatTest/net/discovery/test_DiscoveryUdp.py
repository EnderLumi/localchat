from socket import AF_INET, SOCK_DGRAM, socket
from time import sleep
from unittest import TestCase
from uuid import uuid4

from localchat.net.discovery import (
    DiscoveredServer,
    UdpBroadcastDiscoveryResponder,
    UdpBroadcastDiscoveryScanner,
)


def _find_free_udp_port() -> int | None:
    probe = socket(AF_INET, SOCK_DGRAM)
    try:
        probe.bind(("127.0.0.1", 0))
    except PermissionError:
        probe.close()
        return None
    port = probe.getsockname()[1]
    probe.close()
    return port


class TestDiscoveryUdp(TestCase):
    def test_scanner_finds_responder(self):
        request_port = _find_free_udp_port()
        if request_port is None:
            self.skipTest("local udp sockets are not available in this environment")

        snapshot = DiscoveredServer(
            server_id=uuid4(),
            server_name="udp-server",
            host="127.0.0.1",
            port=51121,
            requires_password=False,
        )
        responder = UdpBroadcastDiscoveryResponder(
            snapshot_provider=lambda: snapshot,
            request_port=request_port,
            bind_host="127.0.0.1",
        )
        scanner = UdpBroadcastDiscoveryScanner(
            request_port=request_port,
            broadcast_address="127.0.0.1",
            timeout_s=0.25,
        )

        responder.start()
        try:
            sleep(0.05)
            found = scanner.scan()
            self.assertTrue(any(s.server_id == snapshot.server_id for s in found))
        finally:
            responder.stop()

    def test_responder_start_stop_idempotent(self):
        request_port = _find_free_udp_port()
        if request_port is None:
            self.skipTest("local udp sockets are not available in this environment")
        responder = UdpBroadcastDiscoveryResponder(
            snapshot_provider=lambda: DiscoveredServer(
                server_id=uuid4(),
                server_name="x",
                host="127.0.0.1",
                port=51121,
                requires_password=False,
            ),
            request_port=request_port,
            bind_host="127.0.0.1",
        )
        responder.start()
        responder.start()
        self.assertTrue(responder.is_running())
        responder.stop()
        responder.stop()
        self.assertFalse(responder.is_running())
