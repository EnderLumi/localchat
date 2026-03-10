from io import BytesIO
from socket import AF_INET, SOCK_STREAM, socket
from time import sleep
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


class TestTcpChatErrors(TestCase):
    @staticmethod
    def _decode_error(payload: bytes) -> tuple[str, str]:
        return tcp_protocol.decode_server_error(BytesIO(payload[1:]))

    def _connect_client(self, port: int) -> socket:
        client = socket(AF_INET, SOCK_STREAM)
        client.settimeout(1.0)
        client.connect(("127.0.0.1", port))
        return client

    def _recv_until_type(self, client: socket, packet_type: int, max_reads: int = 8) -> bytes:
        for _ in range(max_reads):
            try:
                payload = tcp_protocol.recv_packet(client)
            except TimeoutError:
                continue
            if payload[0] == packet_type:
                return payload
        raise TimeoutError(f"packet type {packet_type} not received")

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
            self.assertEqual(self._decode_error(payload), (tcp_protocol.ERR_JOIN_FIRST, "join first"))
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
            self.assertEqual(
                self._decode_error(payload),
                (tcp_protocol.ERR_UNKNOWN_PACKET_TYPE, "unknown packet type"),
            )
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
            # First join emits membership event(s) and explicit join ACK.
            _ = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_ACK)
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            payload = self._recv_until_type(client, tcp_protocol.PT_S_ERROR)
            self.assertEqual(payload[0], tcp_protocol.PT_S_ERROR)
            self.assertEqual(
                self._decode_error(payload),
                (tcp_protocol.ERR_ALREADY_JOINED, "already joined"),
            )
        finally:
            client.close()
            server.stop()

    def test_server_full_returns_join_nack(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port, max_clients=1)
        server.start()
        sleep(0.05)
        c1 = self._connect_client(port)
        user = SerializableUser(uuid4(), "Alice")
        try:
            tcp_protocol.send_packet(c1, tcp_protocol.encode_join(user))
            _ = self._recv_until_type(c1, tcp_protocol.PT_S_JOIN_ACK)

            c2 = self._connect_client(port)
            try:
                nack_payload = self._recv_until_type(c2, tcp_protocol.PT_S_JOIN_NACK)
                self.assertEqual(
                    tcp_protocol.decode_server_join_nack(BytesIO(nack_payload[1:])),
                    (tcp_protocol.ERR_SERVER_FULL, "server is full"),
                )
            finally:
                c2.close()
        finally:
            c1.close()
            server.stop()

    def test_private_to_unknown_recipient_returns_error_but_connection_stays_alive(self):
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
            ack_payload = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_ACK)
            assigned_user = tcp_protocol.decode_server_join_ack(BytesIO(ack_payload[1:]))

            tcp_protocol.send_packet(client, tcp_protocol.encode_private_message(uuid4(), "secret"))
            err_payload = self._recv_until_type(client, tcp_protocol.PT_S_ERROR)
            self.assertEqual(
                self._decode_error(err_payload),
                (tcp_protocol.ERR_UNKNOWN_RECIPIENT, "unknown recipient"),
            )

            tcp_protocol.send_packet(client, tcp_protocol.encode_public_message("still alive"))
            pub_payload = self._recv_until_type(client, tcp_protocol.PT_S_PUBLIC)
            public_msg = SerializableUserMessage.deserialize(BytesIO(pub_payload[1:]))
            self.assertEqual(public_msg.sender().get_id(), assigned_user.get_id())
            self.assertEqual(public_msg.message(), "still alive")
        finally:
            client.close()
            server.stop()

    def test_client_supplied_duplicate_user_id_is_ignored(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        c1 = self._connect_client(port)
        c2 = self._connect_client(port)
        observer = self._connect_client(port)
        duplicate_id = uuid4()
        first_user = SerializableUser(duplicate_id, "Alice-1")
        second_user = SerializableUser(duplicate_id, "Alice-2")
        observer_user = SerializableUser(uuid4(), "Observer")
        try:
            tcp_protocol.send_packet(c1, tcp_protocol.encode_join(first_user))
            _ = self._recv_until_type(c1, tcp_protocol.PT_S_JOIN_ACK)

            tcp_protocol.send_packet(c2, tcp_protocol.encode_join(second_user))
            _ = self._recv_until_type(c2, tcp_protocol.PT_S_JOIN_ACK)

            tcp_protocol.send_packet(observer, tcp_protocol.encode_join(observer_user))
            _ = self._recv_until_type(observer, tcp_protocol.PT_S_JOIN_ACK)

            tcp_protocol.send_packet(c1, tcp_protocol.encode_public_message("origin check"))
            pub_payload = self._recv_until_type(observer, tcp_protocol.PT_S_PUBLIC)
            public_msg = SerializableUserMessage.deserialize(BytesIO(pub_payload[1:]))
            self.assertNotEqual(public_msg.sender().get_id(), duplicate_id)
            self.assertEqual(public_msg.sender().get_name(), "Alice-1")
            self.assertEqual(public_msg.message(), "origin check")
        finally:
            c1.close()
            c2.close()
            observer.close()
            server.stop()

    def test_join_rejected_by_lock_keeps_connection_for_retry(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        host_client = self._connect_client(port)
        host_user = SerializableUser(uuid4(), "Host")
        tcp_protocol.send_packet(host_client, tcp_protocol.encode_join(host_user))
        _ = self._recv_until_type(host_client, tcp_protocol.PT_S_JOIN_ACK)

        server.set_locked(True)
        client = self._connect_client(port)
        user = SerializableUser(uuid4(), "Alice")
        try:
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            nack_payload = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_NACK)
            self.assertEqual(
                tcp_protocol.decode_server_join_nack(BytesIO(nack_payload[1:])),
                (tcp_protocol.ERR_JOIN_REJECTED, "server is locked"),
            )

            server.set_locked(False)
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            ack_payload = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_ACK)
            joined_user = tcp_protocol.decode_server_join_ack(BytesIO(ack_payload[1:]))
            self.assertNotEqual(joined_user.get_id(), user.get_id())
        finally:
            host_client.close()
            client.close()
            server.stop()

    def test_join_rejected_for_duplicate_user_name(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        first = self._connect_client(port)
        second = self._connect_client(port)
        try:
            tcp_protocol.send_packet(first, tcp_protocol.encode_join(SerializableUser(uuid4(), "Alice")))
            _ = self._recv_until_type(first, tcp_protocol.PT_S_JOIN_ACK)

            tcp_protocol.send_packet(second, tcp_protocol.encode_join(SerializableUser(uuid4(), "Alice")))
            nack_payload = self._recv_until_type(second, tcp_protocol.PT_S_JOIN_NACK)
            self.assertEqual(
                tcp_protocol.decode_server_join_nack(BytesIO(nack_payload[1:])),
                (tcp_protocol.ERR_USER_NAME_IN_USE, "user name already in use"),
            )
        finally:
            first.close()
            second.close()
            server.stop()

    def test_join_internal_error_keeps_connection_for_retry(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)

        original_register = server._register_member_auto_role
        state = {"failed_once": False}

        def flaky_register(user):
            if not state["failed_once"]:
                state["failed_once"] = True
                raise RuntimeError("simulated failure")
            return original_register(user)

        server._register_member_auto_role = flaky_register

        client = self._connect_client(port)
        user = SerializableUser(uuid4(), "Alice")
        try:
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            nack_payload = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_NACK)
            self.assertEqual(
                tcp_protocol.decode_server_join_nack(BytesIO(nack_payload[1:])),
                (tcp_protocol.ERR_JOIN_FAILED, "join failed"),
            )

            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            ack_payload = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_ACK)
            joined_user = tcp_protocol.decode_server_join_ack(BytesIO(ack_payload[1:]))
            self.assertNotEqual(joined_user.get_id(), user.get_id())
        finally:
            client.close()
            server.stop()
