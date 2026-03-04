from socket import AF_INET, SOCK_STREAM, socket
from time import sleep, time
from unittest import TestCase
from uuid import uuid4

from localchat.client import UI
from localchat.client.logicImpl import TcpChatInformation, TcpClientLogic
from localchat.net import SerializableUser
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


class _DummyUI(UI):
    def __init__(self):
        super().__init__()
        self.logic = None

    def set_logic(self, logic: object):
        self.logic = logic

    def start(self) -> None:
        if self.logic is not None:
            self.logic.ui_initialized()

    def shutdown(self) -> None:
        return


class _Collector(EventListener):
    def __init__(self):
        self.items = []

    def on_event(self, event: Event):
        self.items.append(event.value())


class TestE2ETcpFlow(TestCase):
    @staticmethod
    def _wait_for(predicate, timeout_s: float = 3.0) -> bool:
        end = time() + timeout_s
        while time() < end:
            if predicate():
                return True
            sleep(0.01)
        return False

    def _start_logic(self, logic: TcpClientLogic):
        ui = _DummyUI()
        logic.set_ui(ui)
        ui.set_logic(logic)
        logic.start()

    def test_server_and_two_clients_full_flow(self):
        port = _find_free_port()
        if port is None:
            self.skipTest("local tcp sockets are not available in this environment")

        server = TcpServerLogic(host="127.0.0.1", port=port)
        c_logic_1 = TcpClientLogic()
        c_logic_2 = TcpClientLogic()
        c1 = None
        c2 = None
        try:
            server.start()
            sleep(0.05)
            self._start_logic(c_logic_1)
            self._start_logic(c_logic_2)

            info = TcpChatInformation(uuid4(), "e2e-chat", "127.0.0.1", port)
            c1 = c_logic_1.create_chat(info, online=True, port=port)
            c2 = c_logic_2.create_chat(info, online=True, port=port)

            u1 = SerializableUser(uuid4(), "Alice")
            u2 = SerializableUser(uuid4(), "Bob")

            c2_public = _Collector()
            c2_private = _Collector()
            c2_left = _Collector()
            c2.on_user_posted_message().add_listener(c2_public)
            c2.on_user_send_private_message().add_listener(c2_private)
            c2.on_user_left().add_listener(c2_left)

            c1.join(u1)
            c2.join(u2)
            self.assertTrue(self._wait_for(lambda: True, timeout_s=0.05))

            c1.post_message("hello all")
            self.assertTrue(self._wait_for(lambda: any(m.message() == "hello all" for m in c2_public.items)))
            public = [m for m in c2_public.items if m.message() == "hello all"][-1]
            self.assertEqual(public.sender().get_id(), u1.get_id())

            c1.send_private_message(u2, "psst")
            self.assertTrue(self._wait_for(lambda: any(m.message() == "psst" for m in c2_private.items)))
            private = [m for m in c2_private.items if m.message() == "psst"][-1]
            self.assertEqual(private.sender().get_id(), u1.get_id())

            c1.leave()
            self.assertTrue(self._wait_for(lambda: any(u.get_id() == u1.get_id() for u in c2_left.items)))
        finally:
            if c1 is not None:
                try:
                    c1.leave()
                except Exception:
                    pass
            if c2 is not None:
                try:
                    c2.leave()
                except Exception:
                    pass
            try:
                c_logic_1.shutdown()
            except Exception:
                pass
            try:
                c_logic_2.shutdown()
            except Exception:
                pass
            try:
                server.stop()
            except Exception:
                pass
