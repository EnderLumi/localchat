from localchat.net import (
    Serializable, MagicNumber, SerializableUser, SerializableList, SerializableUUID,
    SerializableString, SerializableFloat
)
from localchat.util import User, UserMessage
from localchat.config.limits import MAX_MESSAGE_LENGTH
from io import RawIOBase
from uuid import UUID


# WIP


class _MySerializableUserMessage(Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_7682_6620)

    def __init__(self, user_id: UUID, message: str, timestamp: float):
        self.user_id: UUID = user_id
        self.message: str = message
        self.timestamp: float = timestamp

    def serialize_impl(self, output_stream: RawIOBase):
        serial_uuid = SerializableUUID(self.user_id)
        serial_message = SerializableString(self.message)
        serial_timestamp = SerializableFloat(self.timestamp)
        serial_uuid.serialize(output_stream)
        serial_message.serialize(output_stream)
        serial_timestamp.serialize(output_stream)

    @staticmethod
    def deserialize(input_stream: RawIOBase):
        Serializable.validate_magic(input_stream)
        serial_uuid = SerializableUUID.deserialize(input_stream)
        serial_message = SerializableString.deserialize(input_stream, MAX_MESSAGE_LENGTH)
        serial_timestamp = SerializableFloat.deserialize(input_stream)
        return _MySerializableUserMessage(serial_uuid.value, serial_message.value, serial_timestamp.value)

class SerializableUserMessageList(Serializable):
    MAGIC : MagicNumber = MagicNumber(0x2025_12_29_4708_002e)

    def __init__(self):
        self.items : list[UserMessage] = []

    def serialize_impl(self, output_stream: RawIOBase):
        users : set[User] = set()
        for sender in [message.sender() for message in self.items[::-1]]:
            users.add(sender)

        serial_user_list = SerializableList()
        serial_user_list.items = [SerializableUser.create_copy(user) for user in users]
        serial_user_list.serialize(output_stream)

        serial_message_list = SerializableList()
        serial_message_list.items = [
            _MySerializableUserMessage(
                message.sender().get_id(), message.message(), message.timestamp()
            ) for message in self.items
        ]
        serial_message_list.serialize(output_stream)
