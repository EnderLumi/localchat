from localchat.config.limits import MAX_CHAT_SERIALIZATION_METHODE_NAME_LENGTH
from localchat.util import Chat
from io import RawIOBase
from typing import final


class ChatSerializationMethod:
    MAX_PRIORITY = 10.0
    MIN_PRIORITY = 0.0

    def __init__(self, name: str, priority: float|int = 5.0):
        if len(name) > MAX_CHAT_SERIALIZATION_METHODE_NAME_LENGTH:
            raise ValueError(f"chat serialization method name is too large")
        if priority < ChatSerializationMethod.MIN_PRIORITY or priority > ChatSerializationMethod.MAX_PRIORITY:
            raise ValueError(
                f"Priority must be between {ChatSerializationMethod.MIN_PRIORITY} inclusive "
                f"and {ChatSerializationMethod.MAX_PRIORITY} inclusive"
            )
        self._name = name
        self._priority = float(priority)

    def get_name(self) -> str:
        return self._name

    def get_priority(self) -> float:
        return self._priority

    def supports_deserialisation_of_methode(self, chat_serialization_method_name: str) -> bool:
        return chat_serialization_method_name == self.get_name()

    def serialize_chat(self, output_stream: RawIOBase, chat: Chat):
        raise NotImplementedError()

    def deserialize_chat(self, input_stream: RawIOBase) -> Chat:
        raise NotImplementedError()

    @final
    def __hash__(self):
        return object.__hash__(self)
    @final
    def __eq__(self, other):
        return object.__eq__(self, other)
    @final
    def __ne__(self, other):
        return object.__ne__(self, other)