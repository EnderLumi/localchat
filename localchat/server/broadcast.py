# UDP-Server_display
# Sends regular UDP-Broadcasts to make the server visible on the LAN
from localchat.core.network import UDPBroadcast
from localchat.config.defaults import DISCOVERY_PORT


class ServerAnnouncer:

    def __init__(self, name="Unnamed Server", port=DISCOVERY_PORT):
        self.name = name
        self.port = port
        self._broadcaster = UDPBroadcast(port=self.port)


    def start(self):
        """Start broadcasting"""
        msg = f"LOCALCHAT_SERVER:{self.name}"
        self._broadcaster.broadcast(msg, interval=2.0)


    def stop(self):
        """Stop broadcasting"""
        self._broadcaster.stop()