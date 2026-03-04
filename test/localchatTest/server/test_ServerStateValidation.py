from io import BytesIO
from unittest import TestCase
from uuid import uuid4

from localchat.config.limits import MAX_CHAT_NAME_LENGTH
from localchat.net import SerializableUser
from localchat.server.logicImpl import InMemoryLogic
from localchat.util import Role


class TestServerStateValidation(TestCase):
    @staticmethod
    def _mk_user(name: str):
        return SerializableUser(uuid4(), name)

    def test_server_name_max_boundary(self):
        logic = InMemoryLogic()
        name = "n" * MAX_CHAT_NAME_LENGTH
        logic.set_server_name(name)
        self.assertEqual(logic.get_server_info().get_name(), name)

    def test_send_system_private_message_unknown_member(self):
        logic = InMemoryLogic()
        logic.start()
        with self.assertRaises(KeyError):
            logic.send_system_private_message(uuid4(), "x")
        logic.stop()

    def test_get_host_user_without_host_raises(self):
        logic = InMemoryLogic()
        with self.assertRaises(RuntimeError):
            logic.get_host_user()

    def test_import_state_rejects_unknown_version(self):
        logic = InMemoryLogic()
        payload = (0x0002_0000_0000_0000).to_bytes(8, "big")
        with self.assertRaises(IOError):
            logic.import_state(BytesIO(payload))

    def test_import_state_merge_false_replaces_log(self):
        a = InMemoryLogic()
        a.start()
        host_a = self._mk_user("HostA")
        a.register_member(host_a, Role.HOST)
        a.post_system_message("from-a")
        blob = BytesIO()
        a.export_state(blob)
        a.stop()

        b = InMemoryLogic()
        b.start()
        host_b = self._mk_user("HostB")
        b.register_member(host_b, Role.HOST)
        b.post_system_message("from-b")
        b.import_state(BytesIO(blob.getvalue()), merge=False)

        out = BytesIO()
        b.save_chat(out)
        from localchat.net import SerializableUserMessageList
        saved = SerializableUserMessageList.deserialize(BytesIO(out.getvalue()), 100, 1000)
        messages = [m.message() for m in saved.items]
        self.assertEqual(messages, ["from-a"])
        b.stop()
