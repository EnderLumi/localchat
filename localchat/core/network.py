# TCP/UDP connections, socket wrappers
import socket
import threading
import time

from localchat.config.defaults import UDP_BROADCAST_PORT

class TCPConnection:

    def __init__(self):
        self.sock = None
        self.alive = False
        self.listener_thread = None


    def connect(self, host, port):
        """Connects to a TCP server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.alive = True


    def send(self, data:bytes):
        """Sends bytes over the connection"""
        if not self.alive:
            raise ConnectionError("Connection closed")
        self.sock.sendall(data)


    def receive(self, bufsize=4096) -> bytes:
        """Receives bytes synchronously"""
        if not self.alive:
            raise ConnectionError("Connection closed")
        return self.sock.recv(bufsize)


    def listen(self, callback, bufsize=4096):
        """Starts background thread, calls callback(raw_bytes) when new data arrives"""
        if not callable(callback):
            raise TypeError("callback must be a function")

        def loop():
            while self.alive:
                try:
                    data = self.sock.recv(bufsize)
                    if not data:
                        break
                    callback(data)
                except OSError:
                    break
            self.alive = False

        self.listener_thread = threading.Thread(target=loop, daemon=True)
        self.listener_thread.start()


    def close(self):
        """Terminates connection and thread"""
        self.alive = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
        self.sock = None



class UDPBroadcast:

    def __init__(self, port=UDP_BROADCAST_PORT):
        self.port = port
        self.sock = None
        self.alive = False
        self.thread = None


    def broadcast(self, message: str, interval=2.0):
        """Regularly sends broadcasts to all devices on the LAN"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.alive = True

        def loop():
            data = message.encode("utf-8")
            while self.alive:
                try:
                    self.sock.sendto(data, ("255.255.255.255", self.port))
                except OSError:
                    break
                time.sleep(interval)
            self.sock.close()

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()


    def listen(self, callback):
        """Receives broadcasts and calls callback(message, addr)"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.port))
        self.alive = True

        def loop():
            while self.alive:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    callback(data.decode("utf-8"), addr)
                except OSError:
                    break
            self.sock.close()

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()


    def stop(self):
        """Terminates broadcast or listener"""
        self.alive = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None


#testmethode (einfach_ignorieren):
"""
if __name__ == "__main__":

    def echo_handler(data):
        print("Received:", data.decode())

    # Server test in thread
    def server():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 9999))
        s.listen(1)
        conn, _ = s.accept()
        while True:
            data = conn.recv(1024)
            if not data:
                break
            conn.sendall(data)
        conn.close()
        s.close()

    threading.Thread(target=server, daemon=True).start()
    time.sleep(0.3)

    client = TCPConnection()
    client.connect("127.0.0.1", 9999)
    client.listen(echo_handler)
    client.send(b"hello network")
    time.sleep(0.5)
    client.close()
"""


#testmethode2 (einfach_ignorieren2):
"""
if __name__ == "__main__":

    def on_broadcast(msg, addr):
        print(f"Server detected: {msg} von {addr}")

    # Start server broadcast
    server = UDPBroadcast(port=50000)
    server.broadcast("localchat.servername")

    # Client listening
    client = UDPBroadcast(port=50000)
    client.listen(on_broadcast)

    time.sleep(5)
    server.stop()
    client.stop()
"""