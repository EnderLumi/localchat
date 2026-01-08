from localchat.client.UIImpl import AbstractUI
from localchat.client.UIImpl.simple import SimpleChatUI
from localchat.util import Chat, User
from localchat.event import EventHandler, EventListener, Event
from uuid import UUID, uuid4
from ipaddress import IPv4Address, IPv6Address


class ModifiableUser(User):
    def __init__(self, user_id: UUID, user_name: str):
        super().__init__()
        self._user_id = user_id
        self._user_name = user_name

    def get_id(self) -> UUID:
        return self._user_id
    def get_name(self) -> str:
        return self._user_name
    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return IPv4Address("0.0.0.0")

    def set_id(self, user_id: UUID):
        self._user_id = user_id
    def set_name(self, user_name: str):
        self._user_name = user_name


def on_help():
    print("""help  -show this help
exit  -exit the application
server
  search  -search all available servers
  join <server_id>  -join a server from the list of known servers
  leave  -leave the currently joined server
appearance
  show  -show the currently active appearance
  name <new_name>  -set the user name visible to other chat members
  id <new_id>  -set the user id visible to other chat members""")


class SimpleUI(AbstractUI,EventListener[str]):
    def __init__(self):
        super(SimpleUI, self).__init__()
        super(EventListener, self).__init__()
        self.command_handler = EventHandler()
        self.command_handler.add_listener(self)
        self.known_server : list[Chat] = []
        self.active_appearance: ModifiableUser = ModifiableUser(uuid4(), "N/A")
        self.active_appearance.set_name(f"user-{self.active_appearance.get_id().hex}")
        self._active_chat: SimpleChatUI|None = None
        self._system_chat: SimpleChatUI|None = None
        self._my_id = uuid4()
        self._active = True

    def set_active_chat(self, active_chat: SimpleChatUI|None):
        if self._active_chat is not None:
            self.command_handler.remove_listener(self._active_chat)
            try:
                self._active_chat.leave()
            except IOError as e:
                print("I/O error: {e}")
            self._active_chat = None
        if active_chat is not None:
            try:
                active_chat.join(self.active_appearance)
            except IOError as e:
                print("I/O error: {e}")
                return
            self._active_chat = active_chat
            self.command_handler.add_listener(self._active_chat)

    def get_active_chat(self) -> SimpleChatUI|None:
        return self._active_chat

    def on_event(self, event : Event[str]):
        raw_command = event.value()
        if raw_command.strip() == "": return
        raw_command_parts = raw_command.split()
        command = raw_command_parts[0]
        args = raw_command_parts[1:]
        if command == "help": on_help()
        elif command == "exit": self.logic.shutdown()
        elif command == "server":
            if len(args) == 0: print("error: missing at least one argument")
            elif args[0] == "search":
                print("searching for server...")
                try:
                    self.known_server = self.logic.search_server()
                except IOError as e:
                    self.known_server = []
                    print(f"I/O error: {e}")
                    return
                print("=== servers ===")
                for server in self.known_server:
                    server_info = server.get_chat_info()
                    print(f"{server_info.get_name()} ({server_info.get_id().hex})")
            elif args[0] == "join":
                if len(args) != 2:
                    print("error: expected 1 more argument")
                    return
                if self.get_active_chat() is not None:
                    print("error: already part of a chat")
                    return
                join_target = [
                    server for server in self.known_server if server.get_chat_info().get_id().hex.startswith(args[1])
                ]
                join_target.sort(key=lambda server: -len(server.get_chat_info().get_id().hex))
                if len(join_target) == 0:
                    print("error: no such server")
                    return
                new_active_chat = join_target[0]
                chat_ui = SimpleChatUI(new_active_chat)
                self.set_active_chat(chat_ui)
            elif args[0] == "leave":
                if self.get_active_chat() is None:
                    print("error: not part of a chat")
                    return
                self.set_active_chat(None)
            else: print(f"error: unknown keyword: '{args[0]}'")
        elif command == "appearance":
            if len(args) == 0: print("error: missing at least one argument")
            elif args[0] == "show":
                print("=== appearance ===")
                print(f"user id: {self.active_appearance.get_id().hex}")
                print(f"user name: {self.active_appearance.get_name()}")
            elif args[0] == "name":
                if len(args) != 2:
                    print("error: expected 1 more argument")
                    return
                self.active_appearance.set_name(args[1])
                if self.get_active_chat() is not None:
                    self.get_active_chat().update_appearance(self.active_appearance)
                print(f"new active name: '{args[1]}'")
            elif args[0] == "id":
                if len(args) != 2:
                    print("error: expected 1 more argument")
                    return
                try:
                    new_user_id = UUID(hex=args[1])
                except ValueError as e:
                    print(f"error: invalid id: {e}")
                    return
                self.active_appearance.set_id(new_user_id)
                if self.get_active_chat() is not None:
                    self.get_active_chat().update_appearance(self.active_appearance)
                print(f"new user id: {new_user_id}")
            else: print(f"error: unknown keyword: '{args[0]}'")

    def start_impl(self):
        print("=== Simple UI 1.0 ===")
        self._system_chat = SimpleChatUI(self.logic.get_system_chat())
        self._system_chat.join(self.active_appearance)
        self.logic.ui_initialized()
        while self._active:
            command = input()
            command_event = Event(self._my_id, command)
            self.command_handler.handle(command_event)

    def shutdown(self):
        self._active = False
