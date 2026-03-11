from io import BytesIO
from socket import AF_INET, SOCK_STREAM, socket
from time import sleep, time
from unittest import TestCase
from uuid import uuid4

from localchat.config.limits import RATE_LIMIT_MAX_VIOLATIONS
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

    def test_join_rejected_for_empty_user_name(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        client = self._connect_client(port)
        try:
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(SerializableUser(uuid4(), "   ")))
            nack_payload = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_NACK)
            self.assertEqual(
                tcp_protocol.decode_server_join_nack(BytesIO(nack_payload[1:])),
                (tcp_protocol.ERR_INVALID_USER_NAME, "invalid user name"),
            )
        finally:
            client.close()
            server.stop()

    def test_rate_limited_public_messages_return_error(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        client = self._connect_client(port)
        client.settimeout(0.1)
        user = SerializableUser(uuid4(), "Alice")
        try:
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            _ = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_ACK)

            got_rate_limited = False
            for idx in range(200):
                try:
                    tcp_protocol.send_packet(client, tcp_protocol.encode_public_message(f"msg-{idx}"))
                except OSError:
                    break

            deadline = time() + 2.0
            while time() < deadline:
                try:
                    payload = tcp_protocol.recv_packet(client)
                except TimeoutError:
                    continue
                if payload[0] != tcp_protocol.PT_S_ERROR:
                    continue
                code, _msg = self._decode_error(payload)
                if code == tcp_protocol.ERR_RATE_LIMITED:
                    got_rate_limited = True
                    break
                if code == tcp_protocol.ERR_DISCONNECTED:
                    break
            self.assertTrue(got_rate_limited)
        finally:
            client.close()
            server.stop()

    def test_rate_limit_kicks_after_repeated_violations(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        client = self._connect_client(port)
        client.settimeout(0.1)
        user = SerializableUser(uuid4(), "Alice")
        try:
            tcp_protocol.send_packet(client, tcp_protocol.encode_join(user))
            _ = self._recv_until_type(client, tcp_protocol.PT_S_JOIN_ACK)

            rate_limited = 0
            disconnected = False
            for idx in range(500):
                try:
                    tcp_protocol.send_packet(client, tcp_protocol.encode_public_message(f"msg-{idx}"))
                except OSError:
                    disconnected = True
                    break

            deadline = time() + 3.0
            while time() < deadline:
                try:
                    payload = tcp_protocol.recv_packet(client)
                except TimeoutError:
                    continue
                except IOError:
                    disconnected = True
                    break
                if payload[0] != tcp_protocol.PT_S_ERROR:
                    continue
                code, _msg = self._decode_error(payload)
                if code == tcp_protocol.ERR_RATE_LIMITED:
                    rate_limited += 1
                if code == tcp_protocol.ERR_DISCONNECTED:
                    disconnected = True
                    break
                if rate_limited >= RATE_LIMIT_MAX_VIOLATIONS:
                    break

            self.assertGreaterEqual(rate_limited, RATE_LIMIT_MAX_VIOLATIONS)
            if not disconnected:
                with self.assertRaises(IOError):
                    _ = tcp_protocol.recv_packet(client)
        finally:
            client.close()
            server.stop()

    def test_join_times_out_without_client_payload(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        client = self._connect_client(port)
        try:
            client.settimeout(7.0)
            payload = tcp_protocol.recv_packet(client)
            self.assertEqual(payload[0], tcp_protocol.PT_S_JOIN_NACK)
            self.assertEqual(
                tcp_protocol.decode_server_join_nack(BytesIO(payload[1:])),
                (tcp_protocol.ERR_JOIN_TIMEOUT, "join timeout"),
            )
        finally:
            client.close()
            server.stop()

    def test_broadcast_failure_closes_session(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")
        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)
        c1 = self._connect_client(port)
        c2 = self._connect_client(port)
        try:
            tcp_protocol.send_packet(c1, tcp_protocol.encode_join(SerializableUser(uuid4(), "Alice")))
            ack1 = self._recv_until_type(c1, tcp_protocol.PT_S_JOIN_ACK)
            joined1 = tcp_protocol.decode_server_join_ack(BytesIO(ack1[1:]))

            tcp_protocol.send_packet(c2, tcp_protocol.encode_join(SerializableUser(uuid4(), "Bob")))
            ack2 = self._recv_until_type(c2, tcp_protocol.PT_S_JOIN_ACK)
            joined2 = tcp_protocol.decode_server_join_ack(BytesIO(ack2[1:]))

            self.assertEqual(len(server.list_members()), 2)

            target_session = server._sessions_by_user_id.get(joined2.get_id())
            self.assertIsNotNone(target_session)

            orig_send = TcpServerLogic._send_to_session

            def failing_send(session, payload):
                if session is target_session:
                    raise IOError("simulated send failure")
                return orig_send(session, payload)

            server._send_to_session = failing_send

            server.post_system_message("broadcast")
            sleep(0.05)

            remaining_ids = {u.get_id() for u in server.list_members()}
            self.assertIn(joined1.get_id(), remaining_ids)
            self.assertNotIn(joined2.get_id(), remaining_ids)
        finally:
            c1.close()
            c2.close()
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
