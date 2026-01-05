from localchat.net import Serializable, MagicNumber, SerializableUUID, SerializableString
from localchat.util import User
from localchat.typing import BinaryIOBase
from localchat.config.limits import MAX_USER_NAME_LENGTH
from uuid import UUID
from ipaddress import IPv4Address, IPv6Address


class SerializableUser(User,Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_471b_ca16)

    def __init__(self, user_id: UUID, name: str):
        super().__init__()
        self._id = user_id
        self._name = name

    @staticmethod
    def create_copy(user : User) -> 'SerializableUser':
        return SerializableUser(user.get_id(), user.get_name())

    def get_id(self) -> UUID:
        return self._id
    def get_name(self) -> str:
        return self._name
    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")

    def serialize_impl(self, output_stream: BinaryIOBase):
        serial_uuid = SerializableUUID(self._id)
        serial_name = SerializableString(self._name)

    @classmethod
    def deserialize(cls, input_stream: BinaryIOBase) -> 'SerializableUser':
        cls.validate_magic(input_stream)
        serial_uuid = SerializableUUID.deserialize(input_stream)
        serial_name = SerializableString.deserialize(input_stream, MAX_USER_NAME_LENGTH)
        return SerializableUser(serial_uuid.value, serial_name.value)
