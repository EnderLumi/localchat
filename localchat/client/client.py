# ChatClient:
# A simple TCP-based chat client that connects to a chat server, sends messages,
# and receives messages from other clients.
# The client communicates with the server using a custom packet format and handles
# incoming and outgoing messages in separate threads.
#
# Methods:
# - connect(): Establishes connection to the server and starts a listener thread
# - send_message(text): Sends a public message to the server
# - send_packet(packet): Sends a prepared packet to the server
# - _listen(): Listens for incoming packets and handles them
# - _handle_packet(packet): Processes incoming messages and prints them to the terminal
# - close(): Closes the connection and terminates the client
#
# Run from the localchat dir with: "python3 -m localchat.client.client"
# (should only be run if server is already running)


import socket
import threading
from localchat.core.protocol import make_packet, encode_packet, decode_packet, validate_packet

class ChatClient:

    def __init__(self, username: str, host="127.0.0.1", port: int =51121):
        self.username = username
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.alive = False
        self._lock_ = threading.Lock()


    def connect(self):
        """Connects to the chat server and starts listener"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
        except OSError as e:
            print(f"[CLIENT] connection failed: {e}")
            return

        self.alive = True
        print(f"[CLIENT] connected to {self.host}:{self.port}")

        threading.Thread(target=self._listen, daemon=True).start()

        join_packet = make_packet("join", self.username, {"message": f"{self.username} joined"})
        self.send_packet(join_packet)


    def send_message(self, text: str):
        """Send a public message to the server"""
        if not text.strip():
            return
        self.send_packet(make_packet("public", self.username, {"message": text}))


    def send_packet(self, packet):
        """Send a prepared package"""
        if not self.alive or self.sock is None:
            print("[CLIENT] not connected to a server")
            return
        try:
            data = encode_packet(packet) + b"\n"
            with self._lock_:
                self.sock.sendall(data)
        except OSError as e:
            print(f"[CLIENT] send error: {e}")
            self.close()

    def _listen(self):
        """Listen to incoming packets"""
        buffer = b""
        while self.alive:
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("[CLIENT] server closed connection")
                    break
                buffer += data
                while b"\n" in buffer:
                    packet_bytes, buffer = buffer.split(b"\n", 1)
                    try:
                        packet = decode_packet(packet_bytes)
                        if validate_packet(packet):
                            self._handle_packet(packet)
                    except Exception as e:
                        print(f"[CLIENT] decode error: {e}")
            except OSError:
                break
        self.close()


    def _handle_packet(self, packet: dict):
        """Displays messages in the terminal"""
        ptype = packet.get("type")
        sender = packet.get("from")
        payload = packet.get("payload", {})

        if ptype == "public":
            print(f"{sender}: {payload.get('message', '')}")
        elif ptype == "system":
            print(f"[SYSTEM] {payload.get('message', '')}")


    def close(self):
        """ends the connection"""
        if not self.alive:
            return
        self.alive = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        print(f"[CLIENT] {self.username} disconnected")


if __name__ == "__main__":
    client = ChatClient("Username", host="127.0.0.1", port=51121)
    client.connect()
    print("[CLIENT] Connected to server. Press /exit to stop.")

    try:
        while True:
            msg = input()
            if msg.lower() in ("/exit", "/quit","/leave"):
                break
            client.send_message(msg)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()