# Hauptklasse Client
import socket
import threading
from localchat.core.protocol import make_packet, encode_packet, decode_packet, validate_packet

class ChatClient:

    def __init__(self, username, host="127.0.0.1", port=51121):
        self.username = username
        self.host = host
        self.port = port
        self.sock = None
        self.alive = False
        #self.listener_thread = None


    def connect(self):
        """Connects to the chat server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.alive = True
        print(f"[CLIENT] connected to {self.host}:{self.port}")
        threading.Thread(target=self._listen, daemon=True).start()

        join_packet = make_packet("join", self.username, {"message": f"{self.username} joined"})
        self.send_packet(join_packet)


    def send_message(self, text: str):
        """Send a message to the chat server"""
        pkt = make_packet("public", self.username, {"message": text})
        self.send_packet(pkt)


    def send_packet(self, packet):
        """Send a prepared package"""
        if not self.alive:
            raise ConnectionError("Not connected")
        try:
            self.sock.sendall(encode_packet(packet))
        except OSError as e:
            print(f"[CLIENT] send error: {e}")
            self.alive = False
            #self.close()


    def _listen(self):
        """Receives incoming packets"""
        while self.alive:
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("[CLIENT] server closed connection")
                    break
                packet = decode_packet(data)
                if validate_packet(packet):
                    self._handle_packet(packet)
            except (OSError, ValueError) as e:
                print(f"[CLIENT] Listen error: {e}")
                break
        self.close()


    def _handle_packet(self, packet):
        """Displays messages in the terminal"""
        ptype = packet["type"]
        sender = packet["from"]
        payload = packet["payload"]

        if ptype == "public":
            print(f"{sender}: {payload.get('message', '')}")
            #msg = payload.get("message", "")
            #print(f"[sender] {msg}")
        elif ptype == "system":
            print(f"[SYSTEM] {payload.get('message', '')}")


    def close(self):
        if not self.alive:
            return
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass
        print(f"[CLIENT] {self.username} disconnected")


if __name__ == "__main__":
    import time
    client = ChatClient("Alice", host="127.0.0.1", port=51121)
    client.connect()
    time.sleep(1)
    client.send_message("hello world")
    #time.sleep(1)
    #client.close()
