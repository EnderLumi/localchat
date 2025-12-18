
from UI import UI
from logic import Logic

class AbstractUI(UI):
    def __init__(self):
        super().__init__()
        self.logic : Logic = None
    def setLogic(self, logic : Logic):
        self.logic = logic

    def _aboutUser(self, message : str, userID : int):
        self.userSendMessage(
            self.logic.getClientApplicationUserID(),
            True,
            message.replace(
                "<userName>",
                self.logic.getUserName(userID)
            )
        )

    def userJoined(self, userID : int):
        self._aboutUser("User Joined: '<userName>'", userID)
    def userLeft(self, userID : int):
        self._aboutUser("User Left: '<userName>'", userID)
    def userBecameHost(self, userID : int):
        self._aboutUser("User Became Host: '<userName>'", userID)
    def connctionProblems(self, secondsWithoutConnection : int):
        self.userSendMessage(
            self.logic.getClientApplicationUserID(),
            True,
            f"Connection Problems: {secondsWithoutConnection} seconds"
        )
    def networkErrorOccurred(self, error : IOError):
        self.userSendMessage(
            self.logic.getClientApplicationUserID(),
            True,
            f"Connection Error: '{error}'"
        )
