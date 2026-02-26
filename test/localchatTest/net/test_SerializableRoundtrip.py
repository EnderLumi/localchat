from io import BytesIO
from math import isinf, isnan
from unittest import TestCase
from uuid import uuid4

from localchat.net import (
    SerializableFloat,
    SerializableList,
    SerializableUUID,
    SerializableUser,
    SerializableUserMessage,
    SerializableUserMessageList,
)


class TestSerializableRoundtrip(TestCase):
    def test_uuid_roundtrip(self):
        value = uuid4()
        buffer = BytesIO()
        SerializableUUID(value).serialize(buffer)
        result = SerializableUUID.deserialize(BytesIO(buffer.getvalue()))
        self.assertEqual(result.value, value)

    def test_float_roundtrip_special_values(self):
        for value in [float("inf"), float("-inf"), float("nan")]:
            buffer = BytesIO()
            SerializableFloat(value).serialize(buffer)
            result = SerializableFloat.deserialize(BytesIO(buffer.getvalue())).value
            if isnan(value):
                self.assertTrue(isnan(result))
            elif isinf(value):
                self.assertTrue(isinf(result))
                self.assertEqual(result > 0.0, value > 0.0)

    def test_user_roundtrip(self):
        user = SerializableUser(uuid4(), "Alice")
        buffer = BytesIO()
        user.serialize(buffer)
        result = SerializableUser.deserialize(BytesIO(buffer.getvalue()))
        self.assertEqual(result.get_id(), user.get_id())
        self.assertEqual(result.get_name(), user.get_name())

    def test_user_message_roundtrip(self):
        sender = SerializableUser(uuid4(), "Bob")
        message = SerializableUserMessage(sender, "hello", 123.456)
        buffer = BytesIO()
        message.serialize(buffer)
        result = SerializableUserMessage.deserialize(BytesIO(buffer.getvalue()))
        self.assertEqual(result.sender().get_id(), sender.get_id())
        self.assertEqual(result.message(), "hello")
        self.assertEqual(result.timestamp(), 123.456)

    def test_serializable_list_roundtrip(self):
        user1 = SerializableUser(uuid4(), "A")
        user2 = SerializableUser(uuid4(), "B")
        serial_list = SerializableList()
        serial_list.items = [user1, user2]
        buffer = BytesIO()
        serial_list.serialize(buffer)
        result = SerializableList.deserialize(BytesIO(buffer.getvalue()), SerializableUser.deserialize, 10)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.items[0].get_id(), user1.get_id())
        self.assertEqual(result.items[1].get_id(), user2.get_id())

    def test_user_message_list_roundtrip(self):
        user1 = SerializableUser(uuid4(), "A")
        user2 = SerializableUser(uuid4(), "B")

        payload = SerializableUserMessageList()
        payload.items = [
            SerializableUserMessage(user1, "m1", 1.0),
            SerializableUserMessage(user2, "m2", 2.0),
            SerializableUserMessage(user1, "m3", 3.0),
        ]

        buffer = BytesIO()
        payload.serialize(buffer)
        result = SerializableUserMessageList.deserialize(BytesIO(buffer.getvalue()), 10, 10)

        self.assertEqual(len(result.items), 3)
        self.assertEqual(result.items[0].sender().get_id(), user1.get_id())
        self.assertEqual(result.items[1].sender().get_id(), user2.get_id())
        self.assertEqual(result.items[2].message(), "m3")

    def test_user_message_list_rejects_invalid_sender_index(self):
        user = SerializableUser(uuid4(), "A")
        payload = SerializableUserMessageList()
        payload.items = [SerializableUserMessage(user, "m1", 1.0)]

        buffer = BytesIO()
        payload.serialize(buffer)
        data = bytearray(buffer.getvalue())

        cursor = BytesIO(data)
        cursor.read(8)  # version
        user_count = int.from_bytes(cursor.read(8), "big")
        for _ in range(user_count):
            SerializableUser.deserialize(cursor)
        message_count = int.from_bytes(cursor.read(8), "big")
        self.assertEqual(message_count, 1)
        index_pos = cursor.tell()
        data[index_pos:index_pos + 8] = user_count.to_bytes(8, "big")

        with self.assertRaises(IOError):
            SerializableUserMessageList.deserialize(BytesIO(data), 10, 10)
