from __future__ import annotations

from typing import Callable, TypeVar

from localchat.util import Chat, User, UserMessage
from localchat.util.event import Event, EventListener


_T = TypeVar("_T")


class _ValueListener(EventListener[_T]):
    def __init__(self, callback: Callable[[_T], None]):
        self._callback = callback

    def on_event(self, event: Event[_T]):
        self._callback(event.value())


class CLIChatUI:
    def __init__(
        self,
        chat: Chat,
        appearance: User,
        input_reader: Callable[[str], str] = input,
        output_writer: Callable[[str], None] = print,
    ):
        self._chat = chat
        self._appearance = appearance
        self._input_reader = input_reader
        self._output_writer = output_writer
        self._active = True

        self._message_listener = _ValueListener(self._on_public_message)
        self._private_message_listener = _ValueListener(self._on_private_message)
        self._user_joined_listener = _ValueListener(self._on_user_joined)
        self._user_left_listener = _ValueListener(self._on_user_left)
        self._connection_failure_listener = _ValueListener(self._on_connection_failure)

    def run(self):
        joined = False
        self._activate_listeners()
        try:
            try:
                self._chat.join(self._appearance)
                joined = True
            except IOError as e:
                self._output_writer(self._format_join_error(e))
                return

            info = self._chat.get_chat_info()
            self._output_writer(f"=== Chat: {info.get_name()} ===")
            self._output_writer("Type a message and press Enter.")
            self._output_writer("Use /leave to return to the main menu.")

            while self._active:
                command = self._read_line("chat> ")
                if command is None:
                    break
                command = command.strip()
                if len(command) == 0:
                    continue
                if command in {"/leave", "leave", "/back"}:
                    break
                if command in {"/help", "help"}:
                    self._show_help()
                    continue

                message = command
                if command.startswith("/say "):
                    message = command[5:].strip()
                if len(message) == 0:
                    continue
                try:
                    self._chat.post_message(message)
                except (IOError, RuntimeError) as e:
                    self._output_writer(f"I/O error while sending message: {e}")
        finally:
            if joined:
                try:
                    self._chat.leave()
                except IOError as e:
                    self._output_writer(f"I/O error while leaving chat: {e}")
            self._deactivate_listeners()

    def _show_help(self):
        self._output_writer("Available chat commands:")
        self._output_writer("/help   -> show help")
        self._output_writer("/leave  -> return to main menu")
        self._output_writer("/say <text> or plain <text> to send")

    def _activate_listeners(self):
        self._chat.on_user_posted_message().add_listener(self._message_listener)
        self._chat.on_user_send_private_message().add_listener(self._private_message_listener)
        self._chat.on_user_joined().add_listener(self._user_joined_listener)
        self._chat.on_user_left().add_listener(self._user_left_listener)
        self._chat.on_connection_failure().add_listener(self._connection_failure_listener)

    def _deactivate_listeners(self):
        self._chat.on_user_posted_message().remove_listener(self._message_listener)
        self._chat.on_user_send_private_message().remove_listener(self._private_message_listener)
        self._chat.on_user_joined().remove_listener(self._user_joined_listener)
        self._chat.on_user_left().remove_listener(self._user_left_listener)
        self._chat.on_connection_failure().remove_listener(self._connection_failure_listener)

    def _on_public_message(self, user_message: UserMessage):
        sender = user_message.sender()
        if sender == self._chat.get_server_user():
            self._output_writer(f"[SERVER]: {user_message.message()}")
            return
        self._output_writer(f"{sender.get_name()}: {user_message.message()}")

    def _on_private_message(self, user_message: UserMessage):
        sender = user_message.sender()
        if sender == self._chat.get_server_user():
            self._output_writer(f"[SERVER][private]: {user_message.message()}")
            return
        self._output_writer(f"{sender.get_name()} [private]: {user_message.message()}")

    def _on_user_joined(self, user: User):
        self._output_writer(f"[join] {user.get_name()}")

    def _on_user_left(self, user: User):
        self._output_writer(f"[left] {user.get_name()}")

    def _on_connection_failure(self, error: IOError):
        self._output_writer(f"Connection lost: {error}")
        self._active = False

    @staticmethod
    def _format_join_error(error: IOError) -> str:
        cause = error.__cause__
        if isinstance(cause, ConnectionRefusedError):
            return "Could not connect: connection refused by target server."
        if isinstance(cause, TimeoutError):
            return "Could not connect: connection timed out."
        if isinstance(cause, OSError):
            return f"Could not connect: network error ({cause})."
        return f"Could not join chat: {error}"

    def _read_line(self, prompt: str) -> str | None:
        try:
            return self._input_reader(prompt)
        except (EOFError, KeyboardInterrupt):
            self._output_writer("")
            return None
