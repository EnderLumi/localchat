# localchat/__main__.py:
# CLI Entry point for LocalChat
# Run with: localchat start   or    from the right dir with: python3 -m localchat

import sys
import time

from localchat.core.storage import get_user_name, set_user_name
from localchat.client.client import ChatClient
from localchat.client.discovery import ServerDiscovery
from localchat.server.server import ChatServer
from localchat.server.broadcast import ServerAnnouncer
from localchat.config.defaults import DEFAULT_PORT

def main():
    print("____LOCALCHAT____") #das muss noch ihrgendwie cooler

    username = get_user_name()
    print("Registered as:: " + username)
    if username.startswith("New User"):
        new_name = input("Enter a name: ").strip()
        if new_name:
            set_user_name(new_name)
            username = new_name
        print(f"Your name is now: {username}")

    print("\nScan for available servers on the local network...")
    discovery = ServerDiscovery()
    discovery.start()
    time.sleep(2.5)
    discovery.stop()
    servers = discovery.list_servers()

    if servers:
        print("\nFound servers:")
        for i, (name, addr) in enumerate(servers, start=1):
            print(f"[{i}] {name} ({addr})")
    else:
        print("No servers found")

    print("\nOptions:")
    print("  [N] Start new server")
    print("  [Z] Join server via IP")
    print("  [1–n] Join found server")

    choice = input("Enter a choice: ").strip().lower()

    if choice == "n":
        server_name = input("Enter a server name: ").strip() or f"{username}'s Server"
        print(f"Starting server '{server_name}' ...")

        server = ChatServer(port = DEFAULT_PORT)
        server.start()

        announcer = ServerAnnouncer(name = server_name)
        announcer.start()

        print(f"Server '{server_name}' is running. Clients can now join")
        print("Type /exit to stop.")

        # Host joins as a client itself
        client = ChatClient(username)
        client.connect()

        try:
            while True:
                msg = input()
                if msg.lower() in ("/exit", "/quit", "/leave", "/close"):
                    break
                client.send_message(msg)
        except KeyboardInterrupt:
            pass
        finally:
            client.close()
            announcer.stop()
            server.stop()
            print("\n[SERVER] Closed.")

    elif choice == "z":
        host = input("IP address: ").strip() or "127.0.0.1"
        port = DEFAULT_PORT

        client = ChatClient(username, host = host, port = port)
        client.connect()
        print(f"Connected with {host}:{port}")
        print("Type /exit to stop.")

        try:
            while True:
                msg = input()
                if msg.lower() in ("/exit", "/quit", "/leave", "/close"):
                    break
                client.send_message(msg)
        except KeyboardInterrupt:
            pass
        finally:
            client.close()

    elif choice.isnumeric():
        try:
            index = int(choice) -1
            if 0 <= index < len(servers):
                name, addr = servers[index]
                port = DEFAULT_PORT
                print(f"Connecting to {name} ({addr}) ...")
                client = ChatClient(username, host = addr, port = port)
                client.connect()

                try:
                    while True:
                        msg = input()
                        if msg.lower() in ("/exit", "/quit", "/leave", "/close"):
                            break
                        client.send_message(msg)
                except KeyboardInterrupt:
                    pass
                finally:
                    client.close()
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid choice.")

    else:
        print("Invalid choice.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        main()
    else:
        print("Try use: localchat start")


"""
def discover_servers(timeout: float = 3.0):
    #Sends UDP broadcast to find other running LocalChat servers
    servers = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', DISCOVERY_PORT))
    sock.settimeout(timeout)
    start = time.time()

    while time.time() - start < timeout:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8', errors='ignore')
            if msg.startswith("LOCALCHAT_SERVER"):
                name = msg.split(":", 1)[1]
                servers[addr[0]] = name
        except socket.timeout:
            break
    sock.close()
    return servers


def start_server(name, password=None):
    #Start a new server with broadcast
    server = ChatServer(host="0.0.0.0", port=DEFAULT_PORT, name=name, password=password)
    broadcaster = UDPBroadcast(DISCOVERY_PORT)

    threading.Thread(target=server.start, daemon=True).start()
    threading.Thread(target=broadcaster.start_broadcast, args=(name,), daemon=True).start()

    print(f"[SYSTEM] Server '{name}' is running on port {DEFAULT_PORT}")
    print("[SERVER] Type /exit to stop.")

    # internal "Server-Client"
    admin_client = ChatClient(username = get_user_name(), host="127.0.0.1", port=51121)
    admin_client.connect()

    try:
        while True:
            msg = input()
            if msg.lower() in ("/exit", "/quit","/leave"):
                break
            admin_client.send_message(msg)
    except KeyboardInterrupt:
        pass
    finally:
        admin_client.close()


def start_client(name, password=None):
    #Starts client, displays available servers, and connects
    servers discover_servers()
    if servers:
        print("\nServers found on the network:")
        for i, (ip, name) in enumerate(servers.items(),1):
            print(f" {i}. {name} ({ip})")
        choice = input("\nChoose a server or 'n' for new server: ")
        if choice == "n":
            name = input("Server name: ").strip() or "Unnamed server"
            pw = input("Server password (leave empty if none): ").strip() or None
            start_server(name, pw)
            return
        else:
            try:
                idx = int(choice)-1
                ip = list(server.keys())[idx]
                client = ChatClient(username, host="127.0.0.1", port=51121)
                client.connect()
                print(f"[SYSTEM] Connected to  {servers[ip]} ({ip})")
                while True:
                    msg = input()
                    if msg.lower() in ("/exit", "/quit","/leave"):
                        break
                    client.send_message(msg)
                client.close()
                return
            except Exception as e:
                print(f"[ERROR] Connection failed: {e}")
    else:
        print("Exit LocalChat")


def main():
    parser = argparse.ArgumentParser(description="starting LocalChat")
    parser.add_argument("command", nargs="?", default="start", help="Command: start, server, client")
    args = parser.parse_args()

    username = get_user_name()

    if args.command == "start":
        start_client(username)
    elif args.command == "server":
        name = input("Server name: ").strip() or "Unnamed server"
        pw = input("Server password (leave empty if none): ").strip() or None
        start_server(name, pw)
    elif args.command == "client":
        start_client(username)
    else:
        print("Unknown command")

if __name__ == "__main__":
    main()
"""