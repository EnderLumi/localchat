
class UI:
    def __init__(self): ...

    def userJoined(self, userID : int):
        "A user joined the chat."
    def userLeft(self, userID : int):
        "A user left the chat."
    def userBecameHost(self, userID : int):
        "A user became the new host."
    def userSendMessage(self, userID : int, privateMessage : bool, body : str):
        """
        A user send a message in the chat.
        (Only bots should be allowed to send private messages by default.)
        """
    def connctionProblems(self, secondsWithoutConnection : int):
        "The connection to the server got interrupted."
    def connectionErrorOccurred(self, error : IOError):
        "A connection error has occurred."
