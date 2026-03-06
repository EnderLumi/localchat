from io import BytesIO
from socket import AF_INET, SOCK_STREAM, socket
from unittest import TestCase
from uuid import uuid4

from localchat.net import SerializableUser, SerializableUserMessageList
from localchat.server.logicImpl import InMemoryLogic, TcpServerLogic
from localchat.util import Role
from localchat.util.event import Event, EventListener


class _Collector(EventListener):
    def __init__(self):
        self.items = []

    def on_event(self, event: Event):
        self.items.append(event.value())


class TestServerLogic(TestCase):
    @staticmethod
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

    @staticmethod
    def _mk_user(name: str) -> SerializableUser:
        return SerializableUser(uuid4(), name)

    def test_lifecycle_and_uptime(self):
        logic = InMemoryLogic()
        self.assertFalse(logic.is_running())
        logic.start()
        self.assertTrue(logic.is_running())
        self.assertGreaterEqual(logic.get_uptime_seconds(), 0.0)
        with self.assertRaises(RuntimeError):
            logic.start()
        logic.stop()
        self.assertFalse(logic.is_running())

    def test_register_transfer_roles_and_events(self):
        logic = InMemoryLogic()
        joined = _Collector()
        role_changed = _Collector()
        logic.on_member_joined().add_listener(joined)
        logic.on_member_role_changed().add_listener(role_changed)
        logic.start()

        u1 = self._mk_user("Alice")
        u2 = self._mk_user("Bob")
        logic.register_member(u1, Role.HOST)
        logic.register_member(u2, Role.MEMBER)
        self.assertEqual(logic.get_host_user().get_id(), u1.get_id())
        self.assertEqual(logic.get_user_role(u1.get_id()), Role.HOST)
        self.assertEqual(logic.get_user_role(u2.get_id()), Role.MEMBER)
        self.assertEqual(len(joined.items), 2)

        logic.transfer_host(u2.get_id())
        self.assertEqual(logic.get_host_user().get_id(), u2.get_id())
        self.assertEqual(logic.get_user_role(u1.get_id()), Role.MEMBER)
        self.assertEqual(logic.get_user_role(u2.get_id()), Role.HOST)
        self.assertEqual(len(role_changed.items), 2)
        logic.stop()

    def test_lock_and_ban_rules_for_join(self):
        logic = InMemoryLogic()
        logic.start()
        host = self._mk_user("Host")
        member = self._mk_user("Member")

        logic.set_locked(True)
        with self.assertRaises(PermissionError):
            logic.register_member(member, Role.MEMBER)
        logic.register_member(host, Role.HOST)

        logic.set_locked(False)
        logic.register_member(member, Role.MEMBER)
        logic.ban_member(member.get_id(), "test")
        self.assertIn(member.get_id(), logic.list_banned_users())
        with self.assertRaises(PermissionError):
            logic.register_member(member, Role.MEMBER)
        logic.unban_member(member.get_id())
        logic.register_member(member, Role.MEMBER)
        logic.stop()

    def test_kick_member_and_host_protection(self):
        logic = InMemoryLogic()
        left = _Collector()
        logic.on_member_left().add_listener(left)
        logic.start()

        host = self._mk_user("Host")
        member = self._mk_user("Member")
        logic.register_member(host, Role.HOST)
        logic.register_member(member, Role.MEMBER)

        with self.assertRaises(PermissionError):
            logic.kick_member(host.get_id(), "forbidden")
        logic.kick_member(member.get_id(), "bye")
        self.assertEqual(len(logic.list_members()), 1)
        self.assertEqual(len(left.items), 1)
        with self.assertRaises(KeyError):
            logic.get_user_role(member.get_id())
        logic.stop()

    def test_system_messages_and_save_chat(self):
        logic = InMemoryLogic()
        pub = _Collector()
        priv = _Collector()
        logic.on_public_message().add_listener(pub)
        logic.on_private_message().add_listener(priv)
        logic.start()

        host = self._mk_user("Host")
        member = self._mk_user("Member")
        logic.register_member(host, Role.HOST)
        logic.register_member(member, Role.MEMBER)

        logic.post_system_message("hello all")
        logic.send_system_private_message(member.get_id(), "hello you")

        self.assertEqual(len(pub.items), 1)
        self.assertEqual(len(priv.items), 1)
        self.assertEqual(pub.items[0].message(), "hello all")
        self.assertEqual(priv.items[0].message(), "hello you")

        out = BytesIO()
        logic.save_chat(out)
        saved = SerializableUserMessageList.deserialize(BytesIO(out.getvalue()), 100, 1000)
        self.assertEqual(len(saved.items), 1)
        self.assertEqual(saved.items[0].message(), "hello all")
        logic.stop()

    def test_export_import_state_roundtrip(self):
        logic = InMemoryLogic()
        logic.start()
        host = self._mk_user("Host")
        member = self._mk_user("Member")
        logic.register_member(host, Role.HOST)
        logic.register_member(member, Role.MEMBER)
        logic.set_server_name("My LAN")
        logic.set_locked(True)
        logic.set_host_client_port(55000)
        logic.ban_member(member.get_id(), "nope")
        logic.post_system_message("persist me")

        blob = BytesIO()
        logic.export_state(blob)
        logic.stop()

        restored = InMemoryLogic()
        restored.import_state(BytesIO(blob.getvalue()), merge=False)
        self.assertEqual(restored.get_server_info().get_name(), "My LAN")
        self.assertTrue(restored.is_locked())
        self.assertEqual(restored.get_host_client_port(), 55000)
        self.assertIn(member.get_id(), restored.list_banned_users())

        out = BytesIO()
        restored.save_chat(out)
        saved = SerializableUserMessageList.deserialize(BytesIO(out.getvalue()), 100, 1000)
        self.assertEqual(len(saved.items), 1)
        self.assertEqual(saved.items[0].message(), "persist me")

    def test_tcp_server_with_dynamic_port_reports_actual_bound_port(self):
        probe_port = self._find_free_port()
        if probe_port is None:
            self.skipTest("local tcp sockets are not available in this environment")

        logic = TcpServerLogic(host="127.0.0.1", port=0)
        logic.start()
        try:
            info = logic.get_server_info()
            self.assertGreater(info.get_port(), 0)
            self.assertNotEqual(info.get_port(), 0)
            snapshot = logic._discovery_snapshot()
            self.assertEqual(snapshot.port, info.get_port())
        finally:
            logic.stop()
