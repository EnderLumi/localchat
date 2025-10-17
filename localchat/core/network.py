# TCP/UDP connections, socket wrappers
import socket
import threading

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


"""
if __name__ == "__main__":
    import time

    def echo_handler(data):
        print("Received:", data.decode())

    # Server-Test in Thread
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
