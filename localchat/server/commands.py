# Serverbefehle (/kick, /ban, /info server)

import time
import socket

class ServerCommandHandler:

    def __init__(self, server):
        self.server = server
        self.banned = set()
        self.host_ips = {"127.0.0.1", server.host}


    def handle(self, command:str):
        if not command.startswith('/'):
            print(f"[SERVER] without / its not a command")
            return False
        user = socket.gethostname()
        user_ip = user.socket.gethostbyname(command)
        if not self.server.host == user_ip:
            print(f"[SERVER] {user_ip} has no permission for this command")
            return False


        parts = command.strip().split()
        cmd = parts[0].lower()

        if cmd == '/ban':
            return self._ban(parts)
        elif cmd == '/unban':
            return self._unban(parts)
        elif cmd == '/banlist':
            return self._banlist()
        elif cmd == '/help':
            return self._help()
        elif cmd == '/info':
            return self._info()
        elif cmd == '/kick':
            return self._kick(parts)
        elif cmd == '/list':
            return self._list()
        elif cmd in ("/exit", "/stop", "/shutdown", "/leave", "/quit", "/close"):
            self.server.stop()
            print("[SERVER] Shutting down")
            return True
        else:
            print(f"[SERVER] Unknown command: {cmd}")
            return True


    def _help(self):
        print("Available commands:")
        print("  /info                    - show server info")
        print("  /list                    - list connected clients")
        print("  /kick <name|ip> [reason] - disconnect a client")
        print("  /ban <name|ip>  [reason] - ban a client IP")
        print("  /unban <ip>              - unban a client")
        print("  /banlist                 - list banned clients")
        print("  /help                    - show this help")
        print("  /exit                    - stop the server")
        # noch mehr commands, die es aber auch bei client gibt, deswegen muss man mal schauen, wie das funktioniert, wenn clients/commands.py fertig ist.


    def _info(self):
        clients = len(self.server.sessions.list())
        print(f"[SERVER INFO]")
        print(f"  Host: {self.server.host}")
        print(f"  Port: {self.server.port}")
        print(f"  Clients: {clients}")
        print(f"  Banned: {len(self.banned)}")
        print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return True


    def _ban(self, parts):
        if len(parts) < 2:
            print("Usage: /ban <name|ip> [reason]")
            return True

        target = parts[1]
        reason = "".join(parts[2:]) if len(parts) > 2 else "Banned by server host"

        addr = self._find_client(target)
        if not addr:
            print(f"[SERVER] No such client: {target}")
            return True

        if addr[0] in self.host_ips:
            print(f"[SERVER] Cannot ban yourself")
            return True

        ip = addr[0]
        self.banned.add(ip)

        msg_packet = {
            "type": "system",
            "from": "server",
            "payload": {"message": f"You were banned: {reason}"}
        }
        self.server.session.send_packet(addr, msg_packet)
        self.server.sessions.remove(addr)
        print(f"[SERVER] Banned {target} ({reason})")
        return True


    def _unban(self, parts):
        """Unban a client, by removing it from the ban list"""
        if len(parts) < 2:
            print("Usage: /unban <ip>")
            return True
        ip = parts[1]
        if ip in self.banned:
            self.banned.remove(ip)
            print(f"[SERVER] Unbanned {ip}")
        else:
            print(f"[SERVER] Client: {ip} not found in ban list")
        return True


    def _banlist(self):
        if not self.banned:
            print("[SERVER] No banned clients")
            return True
        print(f"[SERVER] Banned users:")
        for i, ip in enumerate(self.banned, start=1):
            # Try to resolve the username if the client was known before the ban
            name = None
            for addr, cname in self.server.sessions.list(disconnect=True):
                if addr[0] == ip:
                    name = cname
                    break
            if name:
                print(f"  [{i}] {name} ({ip})")
            else:
                print(f"  [{i}] {ip}")
        return True

    def _kick(self, parts):
        if len(parts) < 2:
            print("Usage: /kick <name|ip> [reason]")
            return True

        target = parts[1]
        reason = "".join(parts[2:]) if len(parts) > 2 else "Kicked by server host"

        addr = self._find_client(target)
        if not addr:
            print(f"[SERVER] No such client: {target}")
            return True
        if addr[0] in self.host_ips:
            print(f"[SERVER] Cannot kick yourself")
            return True

        msg_packet = {
            "type": "system",
            "from": "server",
            "payload": {"message": f"You were kicked: {reason}"}
        }

        self.server.session.send_packet(addr, msg_packet)
        self.server.sessions.remove(addr)
        print(f"[SERVER] Kicked {target} ({reason})")
        return True


    def _list(self):
        clients = list(self.server.sessions.list())
        if not clients:
            print("[SERVER] No clients found")
        else:
            print("[SERVER] Clients found:")
            for i, addr in enumerate(clients, start=1):
                print(f"  [{i}] {addr[0]}:{addr[1]}")
        return True


    def _find_client(self, target):
        """Finds a conncted client by Username or IP"""
        for addr, name in self.server.sessions.list():
            if target == addr[0] or target.lower() in name.lower():
                return addr
        return None