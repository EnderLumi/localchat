from io import BytesIO
from threading import Thread
from unittest import TestCase
from uuid import uuid4

from localchat.server.logicImpl import InMemoryLogic
from localchat.util import Role
from localchat.util.event import Event, EventListener


class _TagCollector(EventListener):
    def __init__(self, tag: str, out: list[str]):
        self._tag = tag
        self._out = out

    def on_event(self, event: Event):
        self._out.append(self._tag)


class _FailingStartLogic(InMemoryLogic):
    def _on_start_impl(self):
        raise IOError("start failed")


class _FailingStopLogic(InMemoryLogic):
    def _on_stop_impl(self):
        raise IOError("stop failed")


class TestServerLogicEdgeCases(TestCase):
    @staticmethod
    def _mk_user(name: str):
        from localchat.net import SerializableUser
        return SerializableUser(uuid4(), name)

    def test_negative_lifecycle_cases(self):
        logic = InMemoryLogic()
        with self.assertRaises(RuntimeError):
            logic.stop()
        logic.start()
        logic.stop()
        with self.assertRaises(RuntimeError):
            logic.stop()

    def test_start_failure_emits_error(self):
        logic = _FailingStartLogic()
        errors = []
        logic.on_error().add_listener(_TagCollector("error", errors))
        with self.assertRaises(IOError):
            logic.start()
        self.assertIn("error", errors)
        self.assertFalse(logic.is_running())

    def test_stop_failure_sets_stopped_state(self):
        logic = _FailingStopLogic()
        logic.start()
        with self.assertRaises(IOError):
            logic.stop()
        self.assertFalse(logic.is_running())

    def test_event_order_for_join_and_role_change(self):
        logic = InMemoryLogic()
        order: list[str] = []
        logic.on_member_joined().add_listener(_TagCollector("joined", order))
        logic.on_member_role_changed().add_listener(_TagCollector("role", order))
        logic.start()
        u1 = self._mk_user("A")
        u2 = self._mk_user("B")
        logic.register_member(u1, Role.HOST)
        logic.register_member(u2, Role.MEMBER)
        logic.transfer_host(u2.get_id())
        logic.stop()
        self.assertEqual(order[:2], ["joined", "joined"])
        self.assertEqual(order[2:], ["role", "role"])

    def test_boundary_validation(self):
        logic = InMemoryLogic()
        with self.assertRaises(ValueError):
            logic.set_server_name("")
        with self.assertRaises(ValueError):
            logic.set_host_client_port(0)
        with self.assertRaises(ValueError):
            logic.set_host_client_port(70000)

    def test_membership_edge_cases(self):
        logic = InMemoryLogic()
        logic.start()
        host = self._mk_user("Host")
        member = self._mk_user("Member")
        logic.register_member(host, Role.HOST)
        logic.register_member(member, Role.MEMBER)
        with self.assertRaises(KeyError):
            logic.transfer_host(uuid4())
        with self.assertRaises(KeyError):
            logic.kick_member(uuid4(), "missing")
        with self.assertRaises(KeyError):
            logic.ban_member(uuid4(), "missing")
        logic.stop()

    def test_import_state_merge_true(self):
        logic_a = InMemoryLogic()
        logic_a.start()
        u1 = self._mk_user("U1")
        logic_a.register_member(u1, Role.HOST)
        logic_a.post_system_message("a")
        blob_a = BytesIO()
        logic_a.export_state(blob_a)
        logic_a.stop()

        logic_b = InMemoryLogic()
        logic_b.start()
        u2 = self._mk_user("U2")
        logic_b.register_member(u2, Role.HOST)
        logic_b.post_system_message("b")
        logic_b.import_state(BytesIO(blob_a.getvalue()), merge=True)
        out = BytesIO()
        logic_b.save_chat(out)
        from localchat.net import SerializableUserMessageList
        saved = SerializableUserMessageList.deserialize(BytesIO(out.getvalue()), 100, 1000)
        messages = [m.message() for m in saved.items]
        self.assertIn("a", messages)
        self.assertIn("b", messages)
        logic_b.stop()

    def test_concurrency_smoke_register_members(self):
        logic = InMemoryLogic()
        logic.start()

        users = [self._mk_user(f"U{i}") for i in range(30)]

        def worker(batch):
            for u in batch:
                logic.register_member(u, Role.MEMBER)

        threads = [
            Thread(target=worker, args=(users[0:10],)),
            Thread(target=worker, args=(users[10:20],)),
            Thread(target=worker, args=(users[20:30],)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        member_ids = {u.get_id() for u in logic.list_members()}
        self.assertEqual(len(member_ids), 30)
        logic.stop()
