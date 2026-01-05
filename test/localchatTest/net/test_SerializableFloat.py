from localchat.net import SerializableFloat
from io import BytesIO, RawIOBase
from unittest import TestCase


class TestSerializableFloat(TestCase):
    def test_deserialize(self):
        dest_buffer = BytesIO()
        value = 752.442 / 56.063
        serial = SerializableFloat(value)
        serial.serialize(dest_buffer)
        src_buffer = BytesIO(dest_buffer.getvalue())
        src_buffer.seek(0)

        result = SerializableFloat.deserialize(src_buffer)

        self.assertEqual(result.value, value)
