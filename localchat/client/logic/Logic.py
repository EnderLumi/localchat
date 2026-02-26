from localchat.util import Chat, ChatInformation, BinaryIOBase
from abc import ABC, abstractmethod

class Logic:
    """
    Die Client-Logik ist eine austauschbare Komponente, die der Client-UI
    Methoden und Klassen-Instanzen bereitstellt, damit diese die Befehle
    des Benutzers ausführen kann.

    Die Client-Logic hat Methoden zu erstellen, suchen und betreten in Chats,
    und stellt implementierungen der Chat-Klasse bereit, über die
    Nachrichten gepostet und empfangen werden können.

    Der Lebenszyklus einer Client-Logik-Klasse sieht wie folgt aus:

    1. 'set_ui' wird extern mit einer Instanz der Client-UI-Klasse aufgerufen.
    2. 'start' wird von extern aufgerufen.
    3. Sobald die Client-Logik bereit ist Befehle von der Client-UI entgegenzunehmen,
       ruft sie 'start' in der Client-UI auf.
    4. Sobald die Client-UI bereit ist Befehle zu erteilen und auf Events aus der
       Client-Logik zu reagieren, ruft sie 'ui_initialized' in der Client-Logik auf.

    Die Client-UI nutzt jetzt die Dienste der Client-Logik, bis die Client-UI
    'shutdown' in der Client-Logik aufruft. Die Client-Logik verlässt dann alle Chats,
    an denen die Client-UI gerade noch teilgenommen hat und speichert alle Daten die
    gesichert werden sollen. Danach ruft die Client-Logic 'shutdown' an der Client-UI auf
    und stoppt.
    """

    #def __init__(self): ...
    def __init__(self):
        super().__init__()

    @abstractmethod
    def start(self):
        """
        Start the localchat client logic.
        Doesn't return until the localchat client
        terminates.
        Must be called with the main thread.
        :return:
        :raises RuntimeError: if logic was already started
        """

    @abstractmethod
    def shutdown(self):
        """
        Terminates the localchat client logic.
        :return:
        :raises RuntimeError: if logic has not been started or was already terminated
        """

    @abstractmethod
    def set_ui(self, ui : object):
        """
        Sets the UI that is used for the localchat client.
        The UI must not have been started.
        :param ui:
        :return:
        :raises RuntimeError: if logic was already started
        """

    @abstractmethod
    def ui_initialized(self):
        """
        Signals to the localchat client logic that the UI has been initialized.
        Must be called by the localchat client ui.
        :return:
        :raises RuntimeError: if logic has not been started
        """

    @abstractmethod
    def create_chat(self, info: ChatInformation, online : bool, port: int) -> Chat:
        """
        Creates a new chat.
        :param info:
        :param online:
        :param port:
        :return:
        :raises IOError: if an I/O error occurs while creating the chat
        """

    @abstractmethod
    def load_chat(self, input_stream: BinaryIOBase, online : bool, port: int) -> Chat:
        """
        Loads a chat from a stream.
        :param input_stream:
        :param online:
        :param port:
        :return:
        :raises IOError: if an I/O error occurs while loading the chat
        :raises NotImplementedError: if this function is not implemented
        """

    @abstractmethod
    def search_server(self) -> list[Chat]:
        """
        Searches for chat servers.
        :return:
        :raises IOError: if an I/O error occurs while searching for servers
        """

    @abstractmethod
    def get_system_chat(self) -> Chat:
        """
        Returns a chat where messages by the localchat client application are posted and where
        commands to the localchat client logic can be sent.
        :return:
        """