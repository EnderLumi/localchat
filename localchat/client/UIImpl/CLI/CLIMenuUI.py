from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, ip_address
from socket import gaierror, gethostbyname
from typing import Callable, Protocol
from uuid import UUID, uuid4

from localchat.client.UIImpl.AbstractUI import AbstractUI
from localchat.client.UIImpl.CLI.CLIChatUI import CLIChatUI
from localchat.client.UIImpl.CLI.CLISettingsUI import CLISettingsUI
from localchat.client.parsing.join_target import parse_join_target
from localchat.config.defaults import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_MAX_CLIENTS, HARD_MAX_CLIENTS
from localchat.server.logicImpl import TcpServerLogic
from localchat.settings import AppSettings, SettingsStore
from localchat.util import Chat, ChatInformation, User


class _MutableUser(User):
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


class _DirectConnectChatInformation(ChatInformation):
    def __init__(self, chat_id: UUID, chat_name: str, host: str, port: int):
        super().__init__()
        self._chat_id = chat_id
        self._chat_name = chat_name
        self._host = host
        self._port = port

    def get_id(self) -> UUID:
        return self._chat_id

    def get_name(self) -> str:
        return self._chat_name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        try:
            return ip_address(self._host)
        except ValueError:
            try:
                resolved_host = gethostbyname(self._host)
                return ip_address(resolved_host)
            except (gaierror, ValueError) as e:
                raise ValueError(f"could not resolve host '{self._host}'") from e

    def get_port(self) -> int:
        return self._port


class _ServerControl(Protocol):
    def start(self): ...
    def stop(self): ...
    def get_server_info(self) -> ChatInformation: ...


class CLIMenuUI(AbstractUI):
    def __init__(
        self,
        input_reader: Callable[[str], str] = input,
        output_writer: Callable[[str], None] = print,
        server_factory: Callable[[str, int], _ServerControl] | None = None,
        settings: AppSettings | None = None,
        settings_store: SettingsStore | None = None,
    ):
        super().__init__()
        self._input_reader = input_reader
        self._output_writer = output_writer
        self._server_factory = server_factory if server_factory is not None else TcpServerLogic
        self._settings = settings if settings is not None else AppSettings.default()
        self._settings_store = settings_store
        self._active = True
        self._known_servers: list[Chat] = []
        self._managed_servers: list[_ServerControl] = []
        appearance_id = uuid4()
        username = self._settings.username.strip()
        if len(username) == 0:
            username = f"user-{appearance_id.hex[:8]}"
            self._settings.username = username
            self._save_settings()
        self._appearance = _MutableUser(appearance_id, username)
        self._settings_ui = CLISettingsUI(input_reader, output_writer)

    def start_impl(self):
        self._active = True
        self._output_writer("=== localchat CLI ===")
        self._output_writer("Welcome to the main menu.")
        self.logic.ui_initialized()

        while self._active:
            self._render_menu()
            command = self._read_line("menu> ")
            if command is None:
                self.logic.shutdown()
                return

            command = command.strip()
            if command == "1":
                self._search_servers()
                continue
            if command == "2":
                self._start_new_server()
                continue
            if command == "3":
                self._direct_connect()
                continue
            if command == "4":
                self._settings_ui.run(self._appearance, self._settings)
                self._settings.username = self._appearance.get_name()
                self._save_settings()
                continue
            if command in {"0", "exit", "quit"}:
                self.logic.shutdown()
                return

            self._output_writer("Invalid selection.")

    def shutdown(self):
        self._active = False
        self._stop_managed_servers()

    def _render_menu(self):
        self._output_writer("")
        self._output_writer("1) Search for servers")
        self._output_writer("2) Start a new server")
        self._output_writer("3) Connect directly (IP:Port)")
        self._output_writer("4) Settings")
        self._output_writer("0) Exit")

    def _search_servers(self):
        self._output_writer("Searching for local servers...")
        try:
            self._known_servers = self.logic.search_server()
        except IOError as e:
            self._known_servers = []
            self._output_writer(f"I/O error while searching servers: {e}")
            return

        if len(self._known_servers) == 0:
            self._output_writer("No servers found.")
            return

        self._output_writer("Discovered servers:")
        for index, server in enumerate(self._known_servers, start=1):
            info = server.get_chat_info()
            self._output_writer(
                f"{index}) {info.get_name()} ({info.get_ip_address()}:{info.get_port()})"
            )

        selection = self._read_line("Enter server number to join (Enter = back): ")
        if selection is None:
            return
        selection = selection.strip()
        if len(selection) == 0:
            return

        try:
            selected_index = int(selection)
        except ValueError:
            self._output_writer("Invalid number.")
            return
        if selected_index < 1 or selected_index > len(self._known_servers):
            self._output_writer("Number is out of range.")
            return

        selected_chat = self._known_servers[selected_index - 1]
        selected_info = selected_chat.get_chat_info()
        self._join_endpoint(
            host=str(selected_info.get_ip_address()),
            port=selected_info.get_port(),
            chat_name=selected_info.get_name(),
        )

    def _direct_connect(self):
        endpoint = self._read_line("Target (IP:Port, host:port, or URL): ")
        if endpoint is None:
            return
        endpoint = endpoint.strip()
        try:
            join_target = parse_join_target(endpoint)
        except ValueError as e:
            self._output_writer(f"Invalid join target: {e}")
            self._output_writer("Examples: 192.168.1.42:51121 or http://host:8080/join/room1")
            return
        host = join_target.host
        port = join_target.port

        self._join_endpoint(
            host=host,
            port=port,
            chat_name=f"direct-{host}:{port}",
            room_hint=join_target.room,
        )

    def _start_new_server(self):
        host_input = self._read_line(f"Bind host (Enter = {DEFAULT_HOST}): ")
        if host_input is None:
            return
        host = host_input.strip() or DEFAULT_HOST

        default_port = self._settings.default_host_server_port
        port_input = self._read_line(f"Port (Enter = {default_port}): ")
        if port_input is None:
            return
        raw_port = port_input.strip() or str(default_port)
        try:
            port = int(raw_port)
        except ValueError:
            self._output_writer("Invalid port.")
            return
        if port <= 0 or port > 65535:
            self._output_writer("Invalid port.")
            return
        if port <= 1023:
            self._output_writer("Port range 1-1023 is reserved/privileged. Recommended range is 49152-65535.")
            return
        if 1024 <= port <= 49151:
            self._output_writer(
                "Warning: ports 1024-49151 may conflict with well-known services. "
                "Recommended range is 49152-65535."
            )

        max_clients_input = self._read_line(f"Max clients (Enter = {DEFAULT_MAX_CLIENTS}, max {HARD_MAX_CLIENTS}): ")
        if max_clients_input is None:
            return
        raw_max_clients = max_clients_input.strip() or str(DEFAULT_MAX_CLIENTS)
        try:
            max_clients = int(raw_max_clients)
        except ValueError:
            self._output_writer("Invalid max clients value.")
            return
        if max_clients <= 0 or max_clients > HARD_MAX_CLIENTS:
            self._output_writer(f"Max clients must be in range 1-{HARD_MAX_CLIENTS}.")
            return

        try:
            server = self._server_factory(host, port, max_clients)
        except TypeError:
            server = self._server_factory(host, port)
        try:
            server.start()
        except (IOError, OSError) as e:
            self._output_writer(f"I/O error while starting server: {e}")
            return

        info = server.get_server_info()
        connect_host = host
        if host in {"0.0.0.0", "::"}:
            connect_host = "127.0.0.1"

        self._output_writer(f"Server started on {info.get_port()} ({host}).")
        self._output_writer("Opening host chat session...")

        joined = self._join_endpoint(
            host=connect_host,
            port=info.get_port(),
            chat_name=info.get_name(),
        )
        if not joined:
            try:
                server.stop()
            except Exception:
                pass
            return

        self._managed_servers.append(server)

    def _join_endpoint(
        self,
        host: str,
        port: int,
        chat_name: str,
        room_hint: str | None = None,
    ) -> bool:
        if room_hint is not None:
            self._output_writer(
                f"Join room hint detected ('{room_hint}'). TCP CLI currently uses host/port only."
            )
        try:
            chat = self._create_direct_chat(host, port, chat_name)
        except (IOError, ValueError) as e:
            self._output_writer(f"I/O error while creating chat: {e}")
            return False
        self._open_chat(chat)
        return True

    def _create_direct_chat(self, host: str, port: int, chat_name: str) -> Chat:
        connect_direct = getattr(self.logic, "connect_direct", None)
        if callable(connect_direct):
            return connect_direct(host, port, chat_name)

        chat_info = _DirectConnectChatInformation(
            chat_id=uuid4(),
            chat_name=chat_name,
            host=host,
            port=port,
        )
        return self.logic.create_chat(chat_info, online=True, port=port)

    def _open_chat(self, chat: Chat):
        chat_ui = CLIChatUI(
            chat=chat,
            appearance=self._appearance,
            settings=self._settings,
            input_reader=self._input_reader,
            output_writer=self._output_writer,
        )
        chat_ui.run()

    def _stop_managed_servers(self):
        servers = list(self._managed_servers)
        self._managed_servers = []
        for server in servers:
            try:
                server.stop()
            except Exception:
                pass

    def _read_line(self, prompt: str) -> str | None:
        try:
            return self._input_reader(prompt)
        except (EOFError, KeyboardInterrupt):
            self._output_writer("")
            return None

    def _save_settings(self):
        if self._settings_store is None:
            return
        try:
            self._settings_store.save(self._settings)
        except OSError:
            pass
