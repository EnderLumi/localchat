from localchat.net import SerializableString
from unittest import TestCase
from io import BytesIO, RawIOBase


def bytes_io_as_raw_io_base(bytes_io : BytesIO) -> RawIOBase:
    # noinspection PyTypeChecker
    return bytes_io


class TestSerializableString(TestCase):

    def test_deserialisation_too_large(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        value_length = len(value)
        serial = SerializableString(value)
        serial.serialize(bytes_io_as_raw_io_base(dest_buffer))
        src_buffer = BytesIO(dest_buffer.getvalue())

        self.assertRaises(IOError, serial.deserialize, bytes_io_as_raw_io_base(src_buffer), value_length - 1)

    def test_deserialisation_exact_match(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        value_length = len(value)
        serial = SerializableString(value)
        serial.serialize(bytes_io_as_raw_io_base(dest_buffer))
        src_buffer = BytesIO(dest_buffer.getvalue())
        src_buffer.seek(0)

        serial.deserialize(bytes_io_as_raw_io_base(src_buffer), value_length)

    def test_deserialisation_space_left(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        value_length = len(value)
        serial = SerializableString(value)
        serial.serialize(bytes_io_as_raw_io_base(dest_buffer))
        src_buffer = BytesIO(dest_buffer.getvalue())

        serial.deserialize(bytes_io_as_raw_io_base(src_buffer), value_length + 1)

    def test_deserialisation_value_preserved(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        serial = SerializableString(value)
        serial.serialize(bytes_io_as_raw_io_base(dest_buffer))
        src_buffer = BytesIO(dest_buffer.getvalue())

        result = serial.deserialize(bytes_io_as_raw_io_base(src_buffer), 999999)

        self.assertEqual(result.value, value)
