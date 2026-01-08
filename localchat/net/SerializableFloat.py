from localchat.net import Serializable, MagicNumber, read_exact
from localchat.util import BinaryIOBase
import math


class SerializableFloat(Serializable):
    MAGIC: MagicNumber = MagicNumber(0x2025_12_29_300c_ff10)

    def __init__(self, value: float|int) -> None:
        self.value = float(value)

    def serialize_impl(self, output_stream: BinaryIOBase):
        if math.isinf(self.value):
            right = 0
            left = 1 if self.value > 0 else 2
        elif math.isnan(self.value):
            right = 0
            left = 2
        else:
            left, right = self.value.as_integer_ratio()
        left_bytes = left.to_bytes(8,"big",signed=True)
        right_bytes = right.to_bytes(8,"big",signed=False)
        output_stream.write(left_bytes)
        output_stream.write(right_bytes)

    @classmethod
    def deserialize(cls, input_stream: BinaryIOBase) -> 'SerializableFloat':
        cls.validate_magic(input_stream)
        left_bytes = read_exact(input_stream, 8)
        right_bytes = read_exact(input_stream, 8)
        left = int.from_bytes(left_bytes,"big",signed=True)
        right = int.from_bytes(right_bytes,"big",signed=False)
        if right == 0:
            if left == 1: value = math.inf
            elif left == 2: value = -math.inf
            elif left == 3: value = math.nan
            else: raise IOError("float is not a valid value")
        else:
            value = left / right
        return SerializableFloat(value)

    def __repr__(self) -> str:
        return "SerializableFloat(" + str(self.value) + ")"