from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from localchat.util import Chat


@dataclass(frozen=True)
class CommandResult:
    handled: bool
    should_leave: bool = False


class ChatCommandRegistry:
    """
    Central client-side command registry for the chat prompt.
    Security-sensitive authorization remains server-side.
    """

    def __init__(self, chat: Chat, output_writer: Callable[[str], None]):
        self._chat = chat
        self._output_writer = output_writer

    def execute(self, raw_input: str) -> CommandResult:
        command = raw_input.strip()
        if len(command) == 0:
            return CommandResult(False)

        if command in {"/leave", "leave", "/back", "back"}:
            return CommandResult(True, should_leave=True)

        if command in {"/help", "help"}:
            self._show_help()
            return CommandResult(True)

        if command.startswith("/say"):
            message = command[4:].strip()
            if len(message) == 0:
                self._output_writer("Usage: /say <text>")
                return CommandResult(True)
            self._chat.post_message(message)
            return CommandResult(True)

        if command.startswith("/"):
            # Forward unknown slash commands to server for authoritative handling.
            self._chat.send_private_message(self._chat.get_server_user(), command)
            return CommandResult(True)

        return CommandResult(False)

    def _show_help(self):
        self._output_writer("Available chat commands:")
        self._output_writer("/help   -> show help")
        self._output_writer("/leave  -> return to main menu")
        self._output_writer("/say <text> -> send public message")
        self._output_writer("/<command> -> forwarded to server command dispatcher")

