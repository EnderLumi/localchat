from localchat.net import Serializable, MagicNumber, read_exact
from localchat.util import BinaryIOBase

# A class for testing how the 'Serializable' interface feels when used

class TestSerializable(Serializable):
    MAGIC = MagicNumber(0x2025_12_25_152b_f426)
    _LENGTH = 16
    def __init__(self, number : int):
        self._num = number
    def get_number(self):
        return self._num
    def serialize_impl(self, output_stream: BinaryIOBase):
        output_stream.write(self._num.to_bytes(TestSerializable._LENGTH, byteorder='big', signed=True))
    @staticmethod
    def deserialize(
            input_stream: BinaryIOBase,
            max_num: int,
            min_num: int
    ) -> 'TestSerializable':
        b = read_exact(input_stream, TestSerializable._LENGTH)
        num = int.from_bytes(b, byteorder='big', signed=True)
        if num > max_num or num < min_num:
            raise IOError(f"invalid number: out of range (min: {min_num}, max: {max_num}, real: {num})")
        return TestSerializable(num)
