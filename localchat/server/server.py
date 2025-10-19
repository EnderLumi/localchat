# ChatServer:
# A TCP-based chat server that accepts connections from multiple clients.
# The server receives messages from clients, validates and decodes them, and sends them to all other
# connected clients (broadcast). Communication takes place in separate threads for each client so that
# the server is not blocked when it is currently working with another client.
#
# Methods:
# - start(): Starts the TCP server and accepts new clients
# - _accept_loop(): Waits for new clients and starts a thread for each connection
# - _client_loop(conn, addr): Processes messages from a single client and sends them to others
# - _send_packet(conn, packet): Sends a message to a client
# - broadcast(packet, exclude=None): Sends a message to all clients except the specified one
# - stop(): Stops the server and closes all connections
#
# Run from the localchat dir with: "python3 -m localchat.server.server"


import socket
import threading
from localchat.core.protocol import encode_packet, decode_packet, validate_packet
from localchat.config.defaults import DEFAULT_PORT

class ChatServer:

    def __init__(self, host='0.0.0.0', port=DEFAULT_PORT):
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
    from localchat.client.client import ChatClient

    server = ChatServer()
    server.start()

    print("[SERVER] running. Launching local admin client...")
    print("[SERVER] running. Type /exit to stop.")

    # interner "Server-Client"
    admin_client = ChatClient("UsernameServer", host="127.0.0.1", port=DEFAULT_PORT)
    admin_client.connect()

    try:
        while True:
            msg = input()
            if msg.lower() in ("/exit", "/quit", "/leave"):
                break
            admin_client.send_message(msg)
    except KeyboardInterrupt:
        pass
    finally:
        admin_client.close()
        server.stop()
        print("[SERVER] stopped")

