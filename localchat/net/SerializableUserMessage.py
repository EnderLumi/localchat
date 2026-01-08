from localchat.util import UserMessage, User, BinaryIOBase
from localchat.net import Serializable, MagicNumber, SerializableUser, SerializableFloat, SerializableString
from localchat.config.limits import MAX_USER_NAME_LENGTH


class SerializableUserMessage(UserMessage,Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_0902_29fc)

    def __init__(self, sender: User, message: str, timestamp: float):
        self._sender = sender
        self._message = message
        self._timestamp = timestamp

    @staticmethod
    def create_copy(user_message: UserMessage) -> 'SerializableUserMessage':
        return SerializableUserMessage(user_message.sender(), user_message.message(), user_message.timestamp())

    def sender(self) -> User:
        return self._sender
    def message(self) -> str:
        return self._message
    def timestamp(self) -> float:
        return self._timestamp

    def serialize_impl(self, output_stream: BinaryIOBase):
        serial_sender = SerializableUser.create_copy(self._sender)
        serial_message = SerializableString(self._message)
        serial_timestamp = SerializableFloat(self._timestamp)
        serial_sender.serialize(output_stream)
        serial_message.serialize(output_stream)
        serial_timestamp.serialize(output_stream)

    @classmethod
    def deserialize(cls, input_stream: BinaryIOBase) -> 'SerializableUserMessage':
        cls.validate_magic(input_stream)
        serial_sender = SerializableUser.deserialize(input_stream)
        serial_message = SerializableString.deserialize(input_stream, MAX_USER_NAME_LENGTH)
        serial_timestamp = SerializableFloat.deserialize(input_stream)
        return SerializableUserMessage(serial_sender, serial_message.value, serial_timestamp.value)

