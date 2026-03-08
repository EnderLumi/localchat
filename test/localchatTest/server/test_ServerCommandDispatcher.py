from unittest import TestCase
from uuid import uuid4

from localchat.net import SerializableUser
from localchat.server.commands import ServerCommandDispatcher
from localchat.server.logicImpl import InMemoryLogic
from localchat.util import Role
from localchat.util.event import Event, EventListener


class _Collector(EventListener):
    def __init__(self):
        self.items = []

    def on_event(self, event: Event):
        self.items.append(event.value())


class TestServerCommandDispatcher(TestCase):
    @staticmethod
    def _mk_user(name: str) -> SerializableUser:
        return SerializableUser(uuid4(), name)

    def test_member_cannot_execute_host_command(self):
        logic = InMemoryLogic()
        logic.start()
        private_events = _Collector()
        logic.on_private_message().add_listener(private_events)

        host = self._mk_user("Host")
        member = self._mk_user("Member")
        target = self._mk_user("Target")
        logic.register_member(host, Role.HOST)
        logic.register_member(member, Role.MEMBER)
        logic.register_member(target, Role.MEMBER)

        dispatcher = ServerCommandDispatcher(logic)
        handled = dispatcher.try_execute(member.get_id(), f"/kick {target.get_id()}")
        self.assertTrue(handled)
        self.assertIn(target.get_id(), {u.get_id() for u in logic.list_members()})
        self.assertTrue(any("permission denied" in m.message().lower() for m in private_events.items))
        logic.stop()

    def test_host_can_kick_member(self):
        logic = InMemoryLogic()
        logic.start()

        host = self._mk_user("Host")
        target = self._mk_user("Target")
        logic.register_member(host, Role.HOST)
        logic.register_member(target, Role.MEMBER)

        dispatcher = ServerCommandDispatcher(logic)
        handled = dispatcher.try_execute(host.get_id(), f"/kick {target.get_id()}")
        self.assertTrue(handled)
        self.assertNotIn(target.get_id(), {u.get_id() for u in logic.list_members()})
        logic.stop()

    def test_unknown_command_returns_feedback(self):
        logic = InMemoryLogic()
        logic.start()
        private_events = _Collector()
        logic.on_private_message().add_listener(private_events)

        host = self._mk_user("Host")
        logic.register_member(host, Role.HOST)

        dispatcher = ServerCommandDispatcher(logic)
        handled = dispatcher.try_execute(host.get_id(), "/doesnotexist")
        self.assertTrue(handled)
        self.assertTrue(any("unknown command" in m.message().lower() for m in private_events.items))
        logic.stop()

    def test_newhost_transfers_role(self):
        logic = InMemoryLogic()
        logic.start()

        host = self._mk_user("Host")
        member = self._mk_user("Member")
        logic.register_member(host, Role.HOST)
        logic.register_member(member, Role.MEMBER)

        dispatcher = ServerCommandDispatcher(logic)
        handled = dispatcher.try_execute(host.get_id(), f"/newhost {member.get_id()}")
        self.assertTrue(handled)
        self.assertEqual(logic.get_user_role(member.get_id()), Role.HOST)
        self.assertEqual(logic.get_user_role(host.get_id()), Role.MEMBER)
        logic.stop()

    def test_list_and_serverinfo_return_metadata(self):
        logic = InMemoryLogic()
        logic.start()
        private_events = _Collector()
        logic.on_private_message().add_listener(private_events)

        host = self._mk_user("Host")
        member = self._mk_user("Member")
        logic.register_member(host, Role.HOST)
        logic.register_member(member, Role.MEMBER)

        dispatcher = ServerCommandDispatcher(logic)
        self.assertTrue(dispatcher.try_execute(host.get_id(), "/list"))
        self.assertTrue(dispatcher.try_execute(host.get_id(), "/serverinfo"))
        self.assertTrue(dispatcher.try_execute(member.get_id(), "/whoami"))

        payloads = [m.message().lower() for m in private_events.items]
        self.assertTrue(any("members:" in p and "host" in p and "member" in p for p in payloads))
        self.assertTrue(any("server '" in p and "members=" in p for p in payloads))
        self.assertTrue(any("you are" in p and "role=member" in p for p in payloads))
        logic.stop()
