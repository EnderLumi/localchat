from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Callable
from uuid import UUID, uuid4

from localchat.client.UIImpl.AbstractUI import AbstractUI
from localchat.client.UIImpl.CLI.CLIChatUI import CLIChatUI
from localchat.client.UIImpl.CLI.CLISettingsUI import CLISettingsUI
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
        self._ip_address = ip_address(host)
        self._port = port

    def get_id(self) -> UUID:
        return self._chat_id

    def get_name(self) -> str:
        return self._chat_name

    def get_ip_address(self) -> IPv4Address | IPv6Address:
        return self._ip_address

    def get_port(self) -> int:
        return self._port


class CLIMenuUI(AbstractUI):
    def __init__(
        self,
        input_reader: Callable[[str], str] = input,
        output_writer: Callable[[str], None] = print,
    ):
        super().__init__()
        self._input_reader = input_reader
        self._output_writer = output_writer
        self._active = True
        self._known_servers: list[Chat] = []
        appearance_id = uuid4()
        self._appearance = _MutableUser(appearance_id, f"user-{appearance_id.hex[:8]}")
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
                self._output_writer("Starting a new server is not yet implemented in this UI.")
                continue
            if command == "3":
                self._direct_connect()
                continue
            if command == "4":
                self._settings_ui.run(self._appearance)
                continue
            if command in {"0", "exit", "quit"}:
                self.logic.shutdown()
                return

            self._output_writer("Invalid selection.")

    def shutdown(self):
        self._active = False

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

        self._open_chat(self._known_servers[selected_index - 1])

    def _direct_connect(self):
        endpoint = self._read_line("Target (IP:Port): ")
        if endpoint is None:
            return
        endpoint = endpoint.strip()
        host_port = self._parse_host_port(endpoint)
        if host_port is None:
            self._output_writer("Invalid format. Expected: IP:Port")
            return
        host, port = host_port

        try:
            chat_info = _DirectConnectChatInformation(
                chat_id=uuid4(),
                chat_name=f"direct-{host}:{port}",
                host=host,
                port=port,
            )
            chat = self.logic.create_chat(chat_info, online=True, port=port)
        except (IOError, ValueError) as e:
            self._output_writer(f"I/O error while creating chat: {e}")
            return

        self._open_chat(chat)

    def _open_chat(self, chat: Chat):
        chat_ui = CLIChatUI(
            chat=chat,
            appearance=self._appearance,
            input_reader=self._input_reader,
            output_writer=self._output_writer,
        )
        chat_ui.run()

    @staticmethod
    def _parse_host_port(text: str) -> tuple[str, int] | None:
        if ":" not in text:
            return None
        host, raw_port = text.rsplit(":", maxsplit=1)
        host = host.strip()
        raw_port = raw_port.strip()
        if len(host) == 0 or len(raw_port) == 0:
            return None
        try:
            ip_address(host)
        except ValueError:
            return None
        try:
            port = int(raw_port)
        except ValueError:
            return None
        if port <= 0 or port > 65535:
            return None
        return host, port

    def _read_line(self, prompt: str) -> str | None:
        try:
            return self._input_reader(prompt)
        except (EOFError, KeyboardInterrupt):
            self._output_writer("")
            return None
