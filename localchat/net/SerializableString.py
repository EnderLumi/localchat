from localchat.net import Serializable, MagicNumber, read_exact
from localchat.util import BinaryIOBase


class SerializableString(Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_c012_4b03)

    def __init__(self, value: str) -> None:
        self.value = value

    def serialize_impl(self, output_stream: BinaryIOBase):
        b = self.value.encode("utf-8","strict")
        b_len_bytes = len(b).to_bytes(8,"big")
        output_stream.write(b_len_bytes)
        output_stream.write(b)

    @classmethod
    def deserialize(cls, input_stream: BinaryIOBase, max_size : int) -> 'SerializableString':
        cls.validate_magic(input_stream)
        b_len_bytes = read_exact(input_stream, 8)
        b_len = int.from_bytes(b_len_bytes, "big")
        MAX_BYTES = max_size * 4
        if b_len > MAX_BYTES or b_len < 0: # utf-8 encoded characters can take up 4 bytes each at most
            raise IOError("Invalid string size")
        b = read_exact(input_stream, b_len)
        try:
            value = b.decode("utf-8","strict")
        except UnicodeDecodeError:
            raise IOError("Invalid string encoding")
        if len(value) > max_size:
            raise IOError("Invalid string size")
        return SerializableString(value)

    def __str__(self) -> str:
        return self.value
    def __repr__(self) -> str:
        return "SerializableString(" + str(self.value) + ")"