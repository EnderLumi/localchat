from localchat.util import Chat, ChatInformation
from localchat.typing import BinaryIOBase


class Logic:
    def __init__(self): ...

    def start(self):
        """
        Start the localchat client logic.
        Doesn't return until the localchat client
        terminates.
        Must be called with the main thread.
        :return:
        :raises RuntimeError: if logic was already started
        """
    def shutdown(self):
        """
        Terminates the localchat client logic.
        :return:
        :raises RuntimeError: if logic has not been started or was already terminated
        """

    def set_ui(self, ui : object):
        """
        Sets the UI that is used for the localchat client.
        The UI must not have been started.
        :param ui:
        :return:
        :raises RuntimeError: if logic was already started
        """
    def ui_initialized(self):
        """
        Signals to the localchat client logic that the UI has been initialized.
        Must be called by the localchat client ui.
        :return:
        :raises RuntimeError: if logic has not been started
        """

    def create_chat(self, info: ChatInformation, online : bool, port: int) -> Chat:
        """
        Creates a new chat.
        :param info:
        :param online:
        :param port:
        :return:
        :raises Error: if an error occurs while creating the chat
        """
    def load_chat(self, input_stream: BinaryIOBase, online : bool, port: int) -> Chat:
        """
        Loads a chat from a stream.
        :param input_stream:
        :param online:
        :param port:
        :return:
        :raises Error: if an error occurs while loading the chat
        :raises NotImplementedError: if this function is not implemented
        """
    def search_server(self) -> list[Chat]:
        """
        Searches for chat servers.
        :return:
        :raises Error: if an error occurs while searching for servers
        """
    def get_system_chat(self) -> Chat:
        """
        Returns a chat where messages by the localchat client application are posted and where
        commands to the localchat client logic can be sent.
        :return:
        """