
import ipaddress

class Logic:
    def __init__(self): ...

    def getUserName(self, userID : int) -> str:
        "The name of a user."
    def getUserIPAddress(self, userID : int) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        "Get a users IP address."
    def getMyUserID(self) -> int:
        "The userID that represents the local user."
    def getClientApplicationUserID(self) -> int:
        "The user ID that represent the client application."
    def getServerUserID(self) -> int:
        "The servers' user ID"
    def listServers(self) -> list[int]:
        "A list with the IDs of all available servers."
    def getServerName(self, serverID : int) -> str:
        "The name of a server."
    def joinServer(self, serverID : int, myUserName : str) -> bool:
        "Join a server."
    def leaveServer(self):
        "Leave the current server."
    def sendMessage(self, body : str):
        "Send a message."
    def sendPrivateMessage(self, userID : int, body : str):
        "Send a message only visable to one user."
    def saveChatToFile(self, directory : str|None, filename : str|None) -> bool:
        "Save the current chat to a file."
    def loadChatFromFile(self, path : str) -> bool:
        "Load a chat from a file."
    def createServer(self, public : bool):
        "Create a new server."
    def runClientCommand(self, command : str):
        "Runs a command to the local client application."
    def runServerCommand(self, command : str):
        "Sends a command to the server and runs it."
