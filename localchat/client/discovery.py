"""Receives UDP broadcasts and detects available localchat servers in the LAN"""
from localchat.core.network import UDPBroadcast
from localchat.config.defaults import DISCOVERY_PORT

class ServerDiscovery:

    def __init__(self, port=DISCOVERY_PORT):
        self.port = port
        self._listener = UDPBroadcast(port=self.port)
        self.found_servers = {}  # addr -> name


    def start(self):
        """Start listening to server announcements"""
        def on_broadcast(message, addr):
            if message.startswith("LOCALCHAT_SERVER:"):
                name = message.split(":", 1)[1]
                self.found_servers[addr[0]] = name
        self._listener.listen(on_broadcast)


    def stop(self):
        """Stop the Discovery"""
        self._listener.stop()


    def list_servers(self):
        """Returns all servers found"""
        return [(name, addr) for addr, name in self.found_servers.items()]
