from localchat.net import MagicNumber
from localchat.typing import BinaryIOBase
from typing import final


class Serializable:
    MAGIC: MagicNumber = MagicNumber(0)

    @final
    def serialize(self, output_stream: BinaryIOBase):
        """
        :raises IOError: if an IOError occurs when writing to the stream
        :param output_stream: destination of the serialized object
        :return:
        """
        assert self.MAGIC != Serializable.MAGIC, "magic number must be overwritten by child class"
        self.MAGIC.write(output_stream)
        self.serialize_impl(output_stream)

    def serialize_impl(self, output_stream: BinaryIOBase):
        """
        :raises IOError: if an IOError occurs when writing to the stream
        :param output_stream: destination of the serialized object
        :return:
        """
        raise NotImplementedError()

    @classmethod
    @final
    def validate_magic(cls, input_stream: BinaryIOBase):
        """
        :raises IOError: if the magic number is invalid or if an IOError
            occurs while reading from the stream.
        :param input_stream: the stream the magic number is read from
        """
        assert cls.MAGIC != Serializable.MAGIC, "magic number must be overwritten by child class"
        cls.MAGIC.read_and_compare(input_stream)
