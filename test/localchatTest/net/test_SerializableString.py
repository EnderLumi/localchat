from localchat.net import SerializableString
from unittest import TestCase
from io import BytesIO, RawIOBase


class TestSerializableString(TestCase):

    def test_deserialisation_too_large(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        value_length = len(value)
        serial = SerializableString(value)
        serial.serialize(dest_buffer)
        src_buffer = BytesIO(dest_buffer.getvalue())

        self.assertRaises(IOError, serial.deserialize, src_buffer, value_length - 1)

    def test_deserialisation_exact_match(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        value_length = len(value)
        serial = SerializableString(value)
        serial.serialize(dest_buffer)
        src_buffer = BytesIO(dest_buffer.getvalue())
        src_buffer.seek(0)

        serial.deserialize(src_buffer, value_length)

    def test_deserialisation_space_left(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        value_length = len(value)
        serial = SerializableString(value)
        serial.serialize(dest_buffer)
        src_buffer = BytesIO(dest_buffer.getvalue())

        serial.deserialize(src_buffer, value_length + 1)

    def test_deserialisation_value_preserved(self):
        dest_buffer = BytesIO()
        value = "This is a test."
        serial = SerializableString(value)
        serial.serialize(dest_buffer)
        src_buffer = BytesIO(dest_buffer.getvalue())

        result = serial.deserialize(src_buffer, 999999)

        self.assertEqual(result.value, value)
