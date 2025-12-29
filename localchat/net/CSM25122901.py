from localchat.util import Chat
from localchat.net import (
    ChatSerializationMethod, Serializable, MagicNumber, SerializableList,
    SerializableUser, SerializableChat, SerializableChatInformation
)
from io import RawIOBase


# WIP


class _MySerializableChat(Serializable):
    MAGIC : MagicNumber = MagicNumber(0x2025_12_29_ca0e_40b2)

    def __init__(self, chat: Chat):
        self.chat = chat

    def serialize_impl(self, output_stream: RawIOBase):
        serial_chat_info = SerializableChatInformation.create_copy(self.chat.get_chat_info())
        serial_user_message_list = SerializableList()
        serial_user_message_list



class CSM25122902(ChatSerializationMethod):
    def __init__(self):
        super().__init__("CSM25122901", 1.5)

    def serialize_chat(self, output_stream: RawIOBase, chat: Chat ) -> None:
        ...




