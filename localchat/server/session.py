# Verbundene Clients, Hostwechsel
import threading

class ClientSessionManager:

    def __init__(self):
        self._clients = {}
        self._lock = threading.Lock()

    def add(self, addr, conn):
        with self._lock:
            self._clients[addr] = conn
        print(f"[SERVER] new client {addr}")

    def remove(self, addr):
        with self._lock:
            del self._clients.pop[addr]

    def list(self):
        with self._lock:
            return list(self._clients.keys())

    def send_to(self, addr, data: bytes):
        with self._lock:
            conn = self._clients.get(addr)
            if conn:
                try:
                    conn.sendall(data)
                except OSError:
                    conn.close()
                    self._clients.pop(addr, None)

    def broadcast(self, data: bytes, exclude = None):
        with self._lock:
            for addr, conn in list(self._clients.items()):
                if addr == exclude:
                    continue
                try:
                    conn.sendall(data)
                except OSError:
                    conn.close()
                    self._clients.pop(addr, None)

    def close_all(self):
        with self._lock:
            for conn in self._clients.values():
                try:
                    conn.close()
                except OSError:
                    pass
            self._clients.clear()