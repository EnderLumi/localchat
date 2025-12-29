from localchat.net import Serializable, MagicNumber, SerializableString, ChatSerializationMethod
from localchat.util import Chat
from localchat.config.limits import MAX_CHAT_SERIALIZATION_METHODE_NAME_LENGTH
from io import RawIOBase
from typing import Iterable


class SerializableChat(Serializable):
    MAGIC : MagicNumber = MagicNumber(0x2025_12_29_630e_a260)

    def __init__(self, serialisation_method: ChatSerializationMethod, chat : Chat):
        self._method = serialisation_method
        self._chat = chat

    def serialize_impl(self, output_stream: RawIOBase):
        serial_methode_name = SerializableString(self._method.get_name())
        serial_methode_name.serialize(output_stream)
        self._method.serialize_chat(output_stream, self._chat)

    @staticmethod
    def deserialize(
            output_stream: RawIOBase,
            serialisation_methods: Iterable[ChatSerializationMethod]
    ) -> 'SerializableChat':
        Serializable.validate_magic(output_stream)

        serial_method_name = SerializableString.deserialize(output_stream, MAX_CHAT_SERIALIZATION_METHODE_NAME_LENGTH)
        method_name = serial_method_name.value

        sorted_methods = list(serialisation_methods)
        sorted_methods.sort(key=lambda method: -method.get_priority())

        sorted_applicable_methods = [
            method for method in sorted_methods if method.supports_deserialisation_of_methode(method_name)
        ]

        if len(sorted_applicable_methods) == 0:
            raise IOError("unsupported chat serialization method '" + method_name + "'")

        chat = sorted_applicable_methods[0].deserialize_chat(output_stream)
        return SerializableChat(sorted_methods[0], chat)
