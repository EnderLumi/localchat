from localchat.net import Serializable, MagicNumber, read_exact
from io import RawIOBase
from uuid import UUID


class SerializableUUID(Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_1ea0_4992)

    def __init__(self, value: UUID):
        self.value = value

    def serialize_impl(self, output_stream: RawIOBase):
        output_stream.write(self.value.bytes)

    @staticmethod
    def deserialize(input_stream: RawIOBase) -> 'SerializableUUID':
        Serializable.validate_magic(input_stream)
        b = read_exact(input_stream, 16)
        value = UUID(bytes=b)
        return SerializableUUID(value)

    def __repr__(self) -> str:
        return "SerializableUUID(" + str(self.value) + ")"