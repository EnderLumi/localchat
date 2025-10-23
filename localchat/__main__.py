# localchat/__main__.py:
# CLI Entry point for localchat
# Run with: localchat start   or    from the right dir with: python3 -m localchat

import sys
import time

from localchat.core.storage import get_user_name, set_user_name
from localchat.client.client import ChatClient
from localchat.client.discovery import ServerDiscovery
from localchat.server.broadcast import ServerResponder
from localchat.server.server import ChatServer
#from localchat.server.broadcast import ServerAnnouncer

from localchat.config.defaults import DEFAULT_PORT


def main():
    print("____LOCALCHAT____") #das muss noch ihrgendwie cooler

    username = get_user_name()
    print("Registered as: " + username)
    if username.startswith("New User"):
        new_name = input("Enter a name: ").strip()
        if new_name:
            set_user_name(new_name)
            username = new_name
        print(f"Your name is now: {username}")

    print("\nScan for available servers on the local network...")
    discovery = ServerDiscovery()
    #discovery.start()
    #time.sleep(2.5)
    #discovery.stop()
    discovery.scan()
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


    # starts a new server
    if choice == "n":
        server_name = input("Enter a server name: ").strip() or f"{username}'s Server"
        print(f"Starting server '{server_name}' ...")

        server = ChatServer(port = DEFAULT_PORT)
        server.start()

        responder = ServerResponder(name = server_name)
        responder.start()

        #announcer = ServerAnnouncer(name = server_name)
        #announcer.start()

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
            #announcer.stop()
            responder.stop()
            server.stop()
            print("\n[SERVER] Closed.")


    # joins Server via IP
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


    # joins Server via [number]
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