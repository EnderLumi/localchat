from io import BytesIO
from socket import AF_INET, SOCK_STREAM, socket
from time import sleep, time
from unittest import TestCase
from uuid import uuid4

from localchat.net import SerializableUser, SerializableUserMessage, tcp_protocol
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


class TestTcpChatPath(TestCase):
    def _connect_client(self, port: int) -> socket:
        client = socket(AF_INET, SOCK_STREAM)
        client.settimeout(1.0)
        client.connect(("127.0.0.1", port))
        return client

    def _recv_until_type(self, client: socket, packet_type: int, timeout_s: float = 2.0) -> bytes:
        end = time() + timeout_s
        while time() < end:
            try:
                payload = tcp_protocol.recv_packet(client)
            except TimeoutError:
                continue
            if payload[0] == packet_type:
                return payload
        raise TimeoutError(f"packet type {packet_type} not received")

    def test_public_and_private_message_flow(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)

        c1 = self._connect_client(port)
        c2 = self._connect_client(port)

        u1 = SerializableUser(uuid4(), "Alice")
        u2 = SerializableUser(uuid4(), "Bob")

        tcp_protocol.send_packet(c1, tcp_protocol.encode_join(u1))
        tcp_protocol.send_packet(c2, tcp_protocol.encode_join(u2))

        ack1 = self._recv_until_type(c1, tcp_protocol.PT_S_JOIN_ACK)
        assigned_u1 = tcp_protocol.decode_server_join_ack(BytesIO(ack1[1:]))
        ack2 = self._recv_until_type(c2, tcp_protocol.PT_S_JOIN_ACK)
        assigned_u2 = tcp_protocol.decode_server_join_ack(BytesIO(ack2[1:]))

        tcp_protocol.send_packet(c1, tcp_protocol.encode_public_message("hello world"))
        public_payload = self._recv_until_type(c2, tcp_protocol.PT_S_PUBLIC)
        public_msg = SerializableUserMessage.deserialize(BytesIO(public_payload[1:]))
        self.assertEqual(public_msg.sender().get_id(), assigned_u1.get_id())
        self.assertEqual(public_msg.message(), "hello world")

        tcp_protocol.send_packet(c1, tcp_protocol.encode_private_message(assigned_u2.get_id(), "secret"))
        private_payload = self._recv_until_type(c2, tcp_protocol.PT_S_PRIVATE)
        private_msg = SerializableUserMessage.deserialize(BytesIO(private_payload[1:]))
        self.assertEqual(private_msg.sender().get_id(), assigned_u1.get_id())
        self.assertEqual(private_msg.message(), "secret")

        tcp_protocol.send_packet(c1, tcp_protocol.encode_leave())
        tcp_protocol.send_packet(c2, tcp_protocol.encode_leave())
        c1.close()
        c2.close()
        server.stop()
