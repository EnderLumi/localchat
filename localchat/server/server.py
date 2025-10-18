# Hauptklasse Server
import socket
import threading
from localchat.core.protocol import encode_packet, decode_packet, validate_packet

class ChatServer:

    def __init__(self, host='0.0.0.0', port=51121):
        self.host = host
        self.port = port
        self.server_sock = None
        self.clients = {}
        self.alive = False


    def start(self):
        """Starts the TCP server and accepts new clients"""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.alive = True
        print(f"[SERVER] running on {self.host}:{self.port}")

        threading.Thread(target=self._accept_loop, daemon=True).start()


    def _accept_loop(self):
        """Accepts new clients"""
        while self.alive:
            try:
                conn, addr = self.server_sock.accept()
                self.clients[addr] = conn
                print(f"[SERVER] new client {addr}")
                threading.Thread(target=self._client_loop, args=(conn, addr), daemon=True).start()
            except OSError:
                break


    def _client_loop(self, conn, addr):
        """Receives messages from the client and distributes them"""
        try:
            welcome_packet = {"type": "system", "from": "server", "payload": {"message": "joined"}}
            conn.sendall(encode_packet(welcome_packet))
        except OSError:
            pass

        while self.alive:
            try:
                raw = conn.recv(4096)
                if not raw:
                    break
                try:
                    packet = decode_packet(raw)
                    if not validate_packet(packet):
                        continue
                    self.broadcast(packet, exclude=addr)
                except ValueError:
                    continue
            except OSError:
                break

        print(f"[SERVER] Client disconnected: {addr}")
        conn.close()
        self.clients.pop(addr, None)


    def broadcast(self, packet: dict, exclude=None):
        """Sends a packet to all connected clients"""
        raw = encode_packet(packet)
        for addr, conn in list(self.clients.items()):
            if addr == exclude:
                continue
            try:
                conn.send(raw)
            except OSError:
                conn.close()
                self.clients.pop(addr, None)


    def stop(self):
        """Shut down the server and close all connections"""
        self.alive = False
        for conn in self.clients.values():
            try:
                conn.close()
            except OSError:
                pass
        self.clients.clear()
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
        print("[SERVER] stopped")


"""
if __name__ == "__main__":
    from localchat.core.protocol import make_packet
    import time
    import socket

    server = ChatServer(host="127.0.0.1", port=6000)
    server.start()
    time.sleep(0.5)

    def simulate_client(name):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 6000))
        pkt = make_packet("public", name, {"message": f"Hello from {name}"})
        s.sendall(encode_packet(pkt))
        time.sleep(0.5)
        s.close()

    simulate_client("Alice")
    simulate_client("Bob")

    time.sleep(3)
    #server.stop()
"""

if __name__ == "__main__":
    server = ChatServer()
    server.start()
    print("[SERVER] running. Press Ctrl+C to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("[SERVER] stopping...")
        server.stop()