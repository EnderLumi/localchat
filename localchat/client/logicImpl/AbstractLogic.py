
import threading
from ..logic import Logic
from ..UI import UI

class AbstractLogic(Logic):
    def __init__(self):
        super().__init__()
        self._userIDCounter = 1
        self._userIDCounterLock = threading.Lock()
        self.ui = None
        self._myUserID = self.nextUserID()
        self._clientApplicationUserID = self.nextUserID()
    def setUI(self, ui : UI):
        self.ui = ui
    def nextUserID(self) -> int:
        with self._userIDCounterLock:
            userID = self._userIDCounter
            self._userIDCounter += 1
            return userID

    def _clientAppMessage(self, message : str):
        self.ui.userSendMessage(
            self.getClientApplicationUserID(),
            True,
            message
        )

    def getUserName(self, userID : int) -> str:
        return "User{" + userID + "}"
    def getMyUserID(self) -> int:
        return self._myUserID
    def getClientApplicationUserID(self) -> int:
        return self._clientApplicationUserID

    def listServers(self) -> list[int]:
        self._clientAppMessage(
            "error: server search is not implemented yet"
        )
        return []
    def getServerName(self, serverID : int) -> str:
        return "Server{" + serverID + "}"
    def saveChatToFile(self, directory : str|None, filename : str|None) -> bool:
        self._clientAppMessage(
            "error: chat saving is not implemented yet"
        )
        return False
    def loadChatFromFile(self, path : str) -> bool:
        self._clientAppMessage(
            "error: chat loading is not implemented yet"
        )
        return False
    def runClientCommand(self, command : str):
        self.sendPrivateMessage(
            self.getClientApplicationUserID(),
            command
        )
    def runServerCommand(self, command : str):
        self.sendPrivateMessage(
            self.getServerUserID(),
            command
        )



