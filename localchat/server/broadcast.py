# UDP-Server_display
# Sends regular UDP-Broadcasts to make the server visible on the LAN
import socket
import threading
from localchat.config import DISCOVERY_PORT
"""
from localchat.core.network import UDPBroadcast
from localchat.config.defaults import DISCOVERY_PORT

class ServerAnnouncer:

    def __init__(self, name="Unnamed Server", port=DISCOVERY_PORT):
        self.name = name
        self.port = port
        self._broadcaster = UDPBroadcast(port=self.port)


    def start(self):
        #Start broadcasting
        msg = f"LOCALCHAT_SERVER:{self.name}"
        self._broadcaster.broadcast(msg, interval=2.0)


    def stop(self):
        #Stop broadcasting
        self._broadcaster.stop()
"""

class ServerResponder:
    """Listens for UDP discovery requests and replies with server information"""

    def __init__(self, name="Unnamed Server", port=DISCOVERY_PORT):
        self.name = name
        self.port = port
        self.sock = None
        self.alive = False
        self.thread = None

    def start(self):
        """starts listening for UDP discovery requests"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.port))
        self.alive = True

        def loop():
            while self.alive:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    message = data.decode("utf-8")
                    if message.strip() == "DISCOVERY_LOCALCHAT_SERVER":
                        reply = f"LOCALCHAT_SERVER:{self.name}".encode("utf-8")
                        self.sock.sendto(reply, addr)
                except OSError:
                    break
            self.sock.close()

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop(self):
        """stops the responder"""
        self.alive = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
