from localchat.net import (
    Serializable, MagicNumber, SerializableUser, SerializableList,
    SerializableString, SerializableFloat, read_exact
)
from localchat.util import User, UserMessage
from localchat.config.limits import MAX_MESSAGE_LENGTH
from io import RawIOBase


class _MyUserMessage(UserMessage):
    def __init__(self, sender: User, message: str, timestamp: float):
        self._sender: User = sender
        self._message: str = message
        self._timestamp: float = timestamp

    def sender(self) -> User:
        return self._sender

    def message(self) -> str:
        return self._message

    def timestamp(self) -> float:
        return self._timestamp


class SerializableUserMessageList(Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_4708_002e)

    _MAX_VERSION_NAME_LENGTH = 64

    def __init__(self):
        self.items: list[UserMessage] = []

    def serialize_impl(self, output_stream: RawIOBase):
        users: set[User] = set()
        for sender in [message.sender() for message in self.items[::-1]]:
            users.add(sender)

        version = 0x0001_0000_0000_0000
        version_bytes = version.to_bytes(8, 'big')
        output_stream.write(version_bytes)

        serializable_user_list = [SerializableUser.create_copy(user) for user in users]

        serial_user_list = SerializableList()
        serial_user_list.items = serializable_user_list
        serial_user_list.serialize(output_stream)

        user_to_index: dict[User, int] = dict(
            [(user, i) for i, user in enumerate(serializable_user_list)]
        )

        message_count_bytes = len(self.items).to_bytes(8, 'big')
        output_stream.write(message_count_bytes)

        for message in self.items:
            user_index = user_to_index[message.sender()]
            user_index_bytes = user_index.to_bytes(8, 'big')
            output_stream.write(user_index_bytes)
            serial_message_message = SerializableString(message.message())
            serial_message_timestamp = SerializableFloat(message.timestamp())
            serial_message_message.serialize(output_stream)
            serial_message_timestamp.serialize(output_stream)

    @classmethod
    def deserialize(
            cls, input_stream: RawIOBase,
            max_user_count: int,
            max_message_count: int
    ) -> 'SerializableUserMessageList':
        cls.validate_magic(input_stream)

        version_bytes = read_exact(input_stream, 8)
        version = int.from_bytes(version_bytes, 'big')
        if version & 0xFFFF_0000_0000_0000 != 0x0001_0000_0000_0000:
            raise IOError(f"unsupported binary format: '{hex(version)}'")

        serial_user_list = SerializableList.deserialize(input_stream, SerializableUser.deserialize, max_user_count)
        # noinspection PyTypeChecker
        user_list: list[User] = serial_user_list.items
        index_to_user: dict[int, User] = dict(
            [(i, user) for i, user in enumerate(user_list)]
        )
        max_user_index = len(user_list)

        message_count_bytes = read_exact(input_stream, 8)
        message_count = int.from_bytes(message_count_bytes, 'big')
        messages = list()
        for i in range(message_count):
            user_index_bytes = read_exact(input_stream, 8)
            user_index = int.from_bytes(user_index_bytes, 'big')
            if user_index > max_user_index:
                raise IOError("invalid message sender index")
            message_sender = index_to_user[user_index]
            serial_message_message = SerializableString.deserialize(input_stream, MAX_MESSAGE_LENGTH)
            serial_message_timestamp = SerializableFloat.deserialize(input_stream)
            messages.append(
                _MyUserMessage(
                    message_sender,
                    serial_message_message.value,
                    serial_message_timestamp.value
                )
            )

        result = SerializableUserMessageList()
        result.items = messages
        return result
