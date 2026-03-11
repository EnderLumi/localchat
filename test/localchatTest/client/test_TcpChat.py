from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, socket
from threading import Event as ThreadEvent, Thread
from time import sleep, time
from unittest import TestCase
from uuid import uuid4

from localchat.client.logicImpl import TcpChat
from localchat.net import SerializableUser, tcp_protocol
from localchat.server.logicImpl import TcpServerLogic
from localchat.util.event import Event, EventListener


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


class _Collector(EventListener):
    def __init__(self):
        self.items = []

    def on_event(self, event: Event):
        self.items.append(event.value())


class TestTcpChat(TestCase):
    @staticmethod
    def _wait_for(predicate, timeout_s: float = 2.0):
        end = time() + timeout_s
        while time() < end:
            if predicate():
                return True
            sleep(0.01)
        return False

    def test_post_before_join_raises(self):
        chat = TcpChat(uuid4(), "chat", "127.0.0.1", 6553)
        with self.assertRaises(RuntimeError):
            chat.post_message("x")

    def test_join_public_private_leave_flow(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")

        server = TcpServerLogic(host="127.0.0.1", port=port)
        server.start()
        sleep(0.05)

        chat_id = uuid4()
        c1 = TcpChat(chat_id, "chat", "127.0.0.1", port)
        c2 = TcpChat(chat_id, "chat", "127.0.0.1", port)

        a1 = SerializableUser(uuid4(), "Alice")
        a2 = SerializableUser(uuid4(), "Bob")

        c2_public = _Collector()
        c2_private = _Collector()
        c2_failure = _Collector()
        c2.on_user_posted_message().add_listener(c2_public)
        c2.on_user_send_private_message().add_listener(c2_private)
        c2.on_connection_failure().add_listener(c2_failure)

        try:
            c1.join(a1)
            c2.join(a2)
            sleep(0.05)

            c1.post_message("hello world")
            self.assertTrue(self._wait_for(lambda: len(c2_public.items) >= 1))
            self.assertEqual(c2_public.items[-1].message(), "hello world")
            self.assertEqual(c2_public.items[-1].sender().get_id(), a1.get_id())

            c1.send_private_message(a2, "secret")
            self.assertTrue(self._wait_for(lambda: len(c2_private.items) >= 1))
            self.assertEqual(c2_private.items[-1].message(), "secret")
            self.assertEqual(c2_private.items[-1].sender().get_id(), a1.get_id())

            self.assertEqual(len(c2_failure.items), 0)
        finally:
            c1.leave()
            c2.leave()
            server.stop()

    def test_unknown_packets_warn_and_disconnect_after_threshold(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")

        ready = ThreadEvent()

        def _run_fake_server():
            listener = socket(AF_INET, SOCK_STREAM)
            listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))
            listener.listen()
            ready.set()
            client, _ = listener.accept()
            try:
                payload = tcp_protocol.recv_packet(client)
                packet_type, _body = tcp_protocol.decode_client_packet(payload)
                if packet_type != tcp_protocol.PT_C_JOIN:
                    return
                tcp_protocol.send_packet(
                    client,
                    tcp_protocol.encode_server_join_ack(SerializableUser(uuid4(), "Joined")),
                )
                for _ in range(4):
                    tcp_protocol.send_packet(client, bytes([250]))
                    sleep(0.02)
                sleep(0.1)
            finally:
                try:
                    client.close()
                except Exception:
                    pass
                listener.close()

        server_thread = Thread(target=_run_fake_server, daemon=True)
        server_thread.start()
        ready.wait(timeout=1.0)

        chat = TcpChat(uuid4(), "chat", "127.0.0.1", port)
        appearance = SerializableUser(uuid4(), "Alice")
        warnings = _Collector()
        failures = _Collector()
        chat.on_user_send_private_message().add_listener(warnings)
        chat.on_connection_failure().add_listener(failures)

        try:
            chat.join(appearance)
            self.assertTrue(
                self._wait_for(
                    lambda: any("unknown packet type 250 ignored" in m.message() for m in warnings.items)
                )
            )
            self.assertTrue(
                self._wait_for(
                    lambda: any("sent too many unknown packet types." in m.message() for m in warnings.items)
                )
            )
            self.assertTrue(self._wait_for(lambda: len(failures.items) >= 1))
        finally:
            try:
                chat.leave()
            except Exception:
                pass
