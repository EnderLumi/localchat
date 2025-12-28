from localchat.util import User, UserMessage, ChatInformation
from localchat.event import EventHandler
from io import RawIOBase


class Chat:
    def __init__(self): ...

    def get_chat_info(self) -> ChatInformation:
        """
        Return the chats information.
        :return:
        """
    def set_chat_info(self, chat_info: ChatInformation):
        """
        Uploads a new version of the chat information.
        :param chat_info:
        :return:
        :raises IOError:
        :raises PermissionError: if the client is not the host
        """

    def join(self, appearance : User):
        """
        Joins the chat.
        If the client is already in the chat, nothing happens.
        :param appearance:
        :return:
        :raises IOError:
        """
    def leave(self):
        """
        Leaves the chat.
        If the client is not a part of the chat, nothing happens.
        :return:
        :raises IOError:
        """

    def update_appearance(self, appearance: User):
        """
        Updates the clients appearance in the chat.
        :param appearance:
        :return:
        :raises IOError:
        """

    def post_message(self, message: str):
        """
        Posts a message to the chat.
        :param message:
        :return:
        :raises IOError:
        """
    def send_private_message(self, recipient: User, message: str):
        """
        Sends a private message to a member of the chat.
        :param recipient:
        :param message:
        :return:
        :raises IOError:
        :raises PermissionError: if the client is not permitted to send a private
            message to the recipient
        """

    def download_chat(self, output_stream : RawIOBase):
        """
        Downloads the chat.
        :param output_stream:
        :return:
        :raises IOError:
        :raises NotImplementedError: if this function is not implemented
        """

    def on_user_joined(self) -> EventHandler[User]: ...
    def on_user_left(self) -> EventHandler[User]: ...
    def on_user_became_host(self) -> EventHandler[User]: ...

    def on_user_posted_message(self) -> EventHandler[UserMessage]: ...
    def on_user_send_private_message(self) -> EventHandler[UserMessage]: ...

    def on_connection_problem(self) -> EventHandler[float]: ...
    def on_connection_failure(self) -> EventHandler[IOError]: ...
