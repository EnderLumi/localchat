"""Discovers via UDP broadcast available localchat servers on the LAN"""
from localchat.core.network import UDPBroadcast
import socket
import time
from localchat.config.defaults import DISCOVERY_PORT

"""
class ServerDiscovery:

    def __init__(self, port=DISCOVERY_PORT):
        self.port = port
        self._listener = UDPBroadcast(port=self.port)
        self.found_servers = {}


    def start(self):
        #Start listening to server announcements
        def on_broadcast(message, addr):
            if message.startswith("LOCALCHAT_SERVER:"):
                name = message.split(":", 1)[1]
                self.found_servers[addr[0]] = name
        self._listener.listen(on_broadcast)


    def stop(self):
        #Stop the Discovery
        self._listener.stop()


    def list_servers(self):
        #Returns all servers found
        return [(name, addr) for addr, name in self.found_servers.items()]
"""

class ServerDiscovery:
    """Discovers available LocalChat servers on the LAN"""

    def __init__(self, port=DISCOVERY_PORT, timeout=2.0):
        self.port = port
        self.timeout = timeout
        self.found_servers = {}

    def scan(self):
        """Broadcasts a discovery request and listens for responses"""
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(self.timeout)

        # Send discovery message
        message = "DISCOVERY_LOCALCHAT_SERVER".encode("utf-8")
        sock.sendto(message, ("255.255.255.255", self.port))

        # Collect responses
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8")
                if text.startswith("LOCALCHAT_SERVER:"):
                    name = text.split(":", 1)[1]
                    self.found_servers[addr[0]] = name
            except socket.timeout:
                break
            except OSError:
                break

        sock.close()

    def list_servers(self):
        """Return list of discovered servers as (name, address)"""
        return [(name, addr) for addr, name in self.found_servers.items()]