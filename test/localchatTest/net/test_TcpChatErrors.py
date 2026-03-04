from io import BytesIO
from socket import AF_INET, SOCK_STREAM, socket
from time import sleep
from unittest import TestCase
from uuid import uuid4

from localchat.net import SerializableString, SerializableUser, tcp_protocol
from localchat.server.logicImpl import TcpServerLogic


def _find_free_port() -> int | None:
    probe = socket(AF_INET, SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", 0))
    except PermissionError:
        probe.close()
        return None
    port = probe.getsockname()[1]
    probe.close()
    return port


class TestTcpChatErrors(TestCase):
    @staticmethod
    def _decode_error(payload: bytes) -> str:
        return SerializableString.deserialize(BytesIO(payload[1:]), 4096).value

    def _connect_client(self, port: int) -> socket:
        client = socket(AF_INET, SOCK_STREAM)
        client.settimeout(1.0)
        client.connect(("127.0.0.1", port))
        return client

    def test_public_before_join_returns_error(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        client = self._connect_client(port)
        try:
            tcp_protocol.send_packet(client, tcp_protocol.encode_public_message("nope"))
            payload = tcp_protocol.recv_packet(client)
            self.assertEqual(payload[0], tcp_protocol.PT_S_ERROR)
            self.assertEqual(self._decode_error(payload), "join first")
        finally:
            client.close()
            server.stop()

    def test_unknown_packet_type_returns_error(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        client = self._connect_client(port)
        try:
            tcp_protocol.send_packet(client, bytes([250]))
            payload = tcp_protocol.recv_packet(client)
            self.assertEqual(payload[0], tcp_protocol.PT_S_ERROR)
            self.assertEqual(self._decode_error(payload), "unknown packet type")
        finally:
            client.close()
            server.stop()

    def test_join_twice_returns_error(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        client = self._connect_client(port)
        user = SerializableUser(uuid4(), "Alice")
        try:
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            # first join triggers joined event
            _ = tcp_protocol.recv_packet(client)
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            payload = tcp_protocol.recv_packet(client)
            self.assertEqual(payload[0], tcp_protocol.PT_S_ERROR)
            self.assertEqual(self._decode_error(payload), "already joined")
        finally:
            client.close()
            server.stop()
