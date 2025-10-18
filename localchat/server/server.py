# Hauptklasse Server
import socket
import threading

from attr.filters import exclude

from localchat.core.protocol import encode_packet, decode_packet, validate_packet

class ChatServer:

    def __init__(self, host='0.0.0.0', port=51121):
        self.host = host
        self.port = port
        self.sock = None
        self.clients = {}
        self.alive = False
        self.lock = threading.Lock()


    def start(self):
        """Starts the TCP server and accepts new clients"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.alive = True
        print(f"[SERVER] running on {self.host}:{self.port}")

        threading.Thread(target=self._accept_loop, daemon=True).start()


    def _accept_loop(self):
        """Accepts new clients in a loop"""
        while self.alive:
            try:
                conn, addr = self.sock.accept()
                with self.lock:
                    self.clients[addr] = conn
                print(f"[SERVER] new client {addr}")
                threading.Thread(target=self._client_loop, args=(conn, addr), daemon=True).start()
            except OSError:
                break


    def _client_loop(self, conn, addr):
        """Handles a single client connection. Receives messages"""
        buffer = b""
        try:
            # welcome system message:
            welcome_packet = {"type": "system", "from": "server", "payload": {"message": "joined"}}
            self._send_packet(conn, welcome_packet)

            while self.alive:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        packet_bytes, buffer = buffer.split(b"\n", 1)
                        try:
                            packet = decode_packet(packet_bytes)
                            if not validate_packet(packet):
                                continue
                            self.broadcast(packet, exclude=addr)
                        except Exception as e:
                            print(f"[SERVER] decode error: {e}")
                except OSError:
                    break
        finally:
            print(f"[SERVER] Client disconnected: {addr}")
            with self.lock:
                self.clients.pop(addr, None)
            conn.close()


    def _send_packet(self, conn, packet):
        """Sends a single packet to a connection"""
        raw = encode_packet(packet) + b"\n"
        conn.sendall(raw)


    def broadcast(self, packet: dict, exclude=None):
        """Sends a packet to all connected clients"""
        #raw = encode_packet(packet)
        with self.lock:
            for addr, conn in list(self.clients.items()):
                if addr == exclude:
                    continue
                try:
                    self._send_packet(conn, packet)
                except OSError:
                    conn.close()
                    self.clients.pop(addr, None)


    def stop(self):
        """Shut down the server and close all connections"""
        self.alive = False
        with self.lock:
            for conn in list(self.clients.values()):
                try:
                    conn.close()
                except OSError:
                    pass
            self.clients.clear()
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        print("[SERVER] stopped")


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



#aufrufen aus dem localchat dc mit python3 -m localchat.server.server