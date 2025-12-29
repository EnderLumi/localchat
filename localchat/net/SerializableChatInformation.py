from localchat.net import Serializable, MagicNumber, SerializableUUID, SerializableString
from localchat.util import ChatInformation
from localchat.config.limits import MAX_CHAT_NAME_LENGTH
from uuid import UUID
from ipaddress import IPv4Address, IPv6Address
from io import RawIOBase


class SerializableChatInformation(ChatInformation,Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_447a0_93f0)

    def __init__(self, chat_id: UUID, name: str):
        super().__init__()
        self._id = chat_id
        self._name = name

    @staticmethod
    def create_copy(chat_info: ChatInformation) -> 'SerializableChatInformation':
        return SerializableChatInformation(chat_info.get_id(), chat_info.get_name())

    def get_id(self) -> UUID:
        return self._id
    def get_name(self) -> str:
        return self._name
    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")
    def get_port(self) -> int:
        return 0

    def serialize_impl(self, output_stream: RawIOBase):
        serial_id = SerializableUUID(self._id)
        serial_name = SerializableString(self._name)
        serial_id.serialize(output_stream)
        serial_name.serialize(output_stream)

    @classmethod
    def deserialize(cls, input_stream: RawIOBase) -> 'SerializableChatInformation':
        cls.validate_magic(input_stream)
        serial_uuid = SerializableUUID.deserialize(input_stream)
        serial_name = SerializableString.deserialize(input_stream, MAX_CHAT_NAME_LENGTH)
        return SerializableChatInformation(serial_uuid.value, serial_name.value)
