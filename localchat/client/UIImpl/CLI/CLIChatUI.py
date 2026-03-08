from __future__ import annotations

from typing import Callable, TypeVar
from time import localtime, strftime

from localchat.client.commands import ChatCommandRegistry
from localchat.settings import AppSettings
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
        settings: AppSettings | None = None,
        input_reader: Callable[[str], str] = input,
        output_writer: Callable[[str], None] = print,
    ):
        self._chat = chat
        self._appearance = appearance
        self._settings = settings if settings is not None else AppSettings.default()
        self._input_reader = input_reader
        self._output_writer = output_writer
        self._active = True
        self._command_registry = ChatCommandRegistry(chat=self._chat, output_writer=self._output_writer)

        self._message_listener = _ValueListener(self._on_public_message)
        self._private_message_listener = _ValueListener(self._on_private_message)
        self._user_joined_listener = _ValueListener(self._on_user_joined)
        self._user_left_listener = _ValueListener(self._on_user_left)
        self._user_became_host_listener = _ValueListener(self._on_user_became_host)
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
            self._output_writer(
                f"Connected to {info.get_ip_address()}:{info.get_port()} (chat-id: {info.get_id()})"
            )
            self._output_writer(f"You are {self._format_user(self._appearance)}")
            self._output_writer("Type a message and press Enter.")
            self._output_writer("Use /leave to return to the main menu.")

            while self._active:
                command = self._read_line("chat> ")
                if command is None:
                    break
                try:
                    command_result = self._command_registry.execute(command)
                    if command_result.handled:
                        if command_result.should_leave:
                            break
                        continue

                    message = command.strip()
                    if len(message) == 0:
                        continue
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

    def _activate_listeners(self):
        self._chat.on_user_posted_message().add_listener(self._message_listener)
        self._chat.on_user_send_private_message().add_listener(self._private_message_listener)
        self._chat.on_user_joined().add_listener(self._user_joined_listener)
        self._chat.on_user_left().add_listener(self._user_left_listener)
        self._chat.on_user_became_host().add_listener(self._user_became_host_listener)
        self._chat.on_connection_failure().add_listener(self._connection_failure_listener)

    def _deactivate_listeners(self):
        self._chat.on_user_posted_message().remove_listener(self._message_listener)
        self._chat.on_user_send_private_message().remove_listener(self._private_message_listener)
        self._chat.on_user_joined().remove_listener(self._user_joined_listener)
        self._chat.on_user_left().remove_listener(self._user_left_listener)
        self._chat.on_user_became_host().remove_listener(self._user_became_host_listener)
        self._chat.on_connection_failure().remove_listener(self._connection_failure_listener)

    def _on_public_message(self, user_message: UserMessage):
        sender = user_message.sender()
        prefix = self._timestamp_prefix(user_message.timestamp())
        if sender == self._chat.get_server_user():
            self._output_writer(f"{prefix}[SERVER]: {user_message.message()}")
            return
        self._output_writer(f"{prefix}{sender.get_name()}: {user_message.message()}")

    def _on_private_message(self, user_message: UserMessage):
        sender = user_message.sender()
        prefix = self._timestamp_prefix(user_message.timestamp())
        if sender == self._chat.get_server_user():
            self._output_writer(f"{prefix}[SERVER][private]: {user_message.message()}")
            return
        self._output_writer(f"{prefix}{sender.get_name()} [private]: {user_message.message()}")

    def _on_user_joined(self, user: User):
        if not self._settings.show_join_leave_notifications:
            return
        self._output_writer(f"[join] {self._format_user(user)}")

    def _on_user_left(self, user: User):
        if not self._settings.show_join_leave_notifications:
            return
        self._output_writer(f"[left] {self._format_user(user)}")

    def _on_user_became_host(self, user: User):
        if not self._settings.show_join_leave_notifications:
            return
        self._output_writer(f"[host] {self._format_user(user)} is now host")

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

    @staticmethod
    def _format_user(user: User) -> str:
        user_id = str(user.get_id())
        return f"{user.get_name()} ({user_id[:8]})"

    def _timestamp_prefix(self, timestamp: float) -> str:
        if not self._settings.show_timestamps:
            return ""
        return f"[{strftime('%H:%M:%S', localtime(timestamp))}] "
