from localchat.net import Serializable, MagicNumber, read_exact
from localchat.typing import BinaryIOBase
from typing import Callable


class SerializableList(Serializable):
    MAGIC : MagicNumber = MagicNumber(0x2025_12_29_18b4_7260)

    def __init__(self):
        super().__init__()
        self.items : list[Serializable] = []

    def serialize_impl(self, output_stream: BinaryIOBase):
        count_bytes = len(self.items).to_bytes(8,"big")
        output_stream.write(count_bytes)
        for item in self.items:
            item.serialize(output_stream)

    @classmethod
    def deserialize(
            cls, input_stream: BinaryIOBase,
            deserializer: Callable[[BinaryIOBase],Serializable],
            max_size: int
    ) -> 'SerializableList':
        cls.validate_magic(input_stream)
        count_bytes = read_exact(input_stream, 8)
        count = int.from_bytes(count_bytes, "big")
        if count > max_size:
            raise IOError("invalid list length")
        items = []
        for i in range(count):
            items.append(deserializer(input_stream))
        result = SerializableList()
        result.items = items
        return result
