from io import BytesIO
from unittest import TestCase
from uuid import uuid4

from localchat.net import (
    SerializableList,
    SerializableString,
    SerializableUUID,
    SerializableUser,
    SerializableUserMessage,
    SerializableUserMessageList,
)
from localchat.config.limits import MAX_USER_NAME_LENGTH


class TestSerializableValidation(TestCase):
    def test_uuid_deserialize_rejects_short_input(self):
        with self.assertRaises(IOError):
            SerializableUUID.deserialize(BytesIO(b"\x00" * 15))

    def test_user_deserialize_rejects_too_large_name(self):
        user_id = SerializableUUID(uuid4())
        name = SerializableString("x" * (MAX_USER_NAME_LENGTH + 1))
        buffer = BytesIO()
        user_id.serialize(buffer)
        name.serialize(buffer)
        with self.assertRaises(IOError):
            SerializableUser.deserialize(BytesIO(buffer.getvalue()))

    def test_user_message_deserialize_rejects_too_large_message(self):
        sender = SerializableUser(uuid4(), "A")
        msg = SerializableString("X" * (64 * 1024 + 1))
        ts = BytesIO()
        sender.serialize(ts)
        msg.serialize(ts)
        # timestamp as float=1.0 serialized via existing serializer path
        from localchat.net import SerializableFloat
        SerializableFloat(1.0).serialize(ts)
        with self.assertRaises(IOError):
            SerializableUserMessage.deserialize(BytesIO(ts.getvalue()))

    def test_serializable_list_rejects_count_above_max(self):
        # count=2, max=1
        payload = (2).to_bytes(8, "big")
        with self.assertRaises(IOError):
            SerializableList.deserialize(BytesIO(payload), SerializableUUID.deserialize, 1)

    def test_user_message_list_rejects_unsupported_version(self):
        payload = bytearray()
        payload += (0x0002_0000_0000_0000).to_bytes(8, "big")
        with self.assertRaises(IOError):
            SerializableUserMessageList.deserialize(BytesIO(payload), 10, 10)

    def test_user_message_list_rejects_message_count_above_max(self):
        user = SerializableUser(uuid4(), "A")
        msg_list = SerializableUserMessageList()
        msg_list.items = [SerializableUserMessage(user, "m1", 1.0)]
        data = bytearray()
        buf = BytesIO()
        msg_list.serialize(buf)
        data.extend(buf.getvalue())

        # Patch message count to 2 without appending second message payload.
        cursor = BytesIO(data)
        cursor.read(8)  # version
        user_count = int.from_bytes(cursor.read(8), "big")
        for _ in range(user_count):
            SerializableUser.deserialize(cursor)
        message_count_pos = cursor.tell()
        data[message_count_pos:message_count_pos + 8] = (2).to_bytes(8, "big")

        with self.assertRaises(IOError):
            SerializableUserMessageList.deserialize(BytesIO(data), 10, 1)
