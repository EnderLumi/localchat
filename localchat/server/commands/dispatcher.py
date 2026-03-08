from __future__ import annotations

from dataclasses import dataclass
from shlex import split as shell_split
from uuid import UUID

from localchat.server.logic import Logic
from localchat.util import Role, User


@dataclass(frozen=True)
class _CommandSpec:
    name: str
    host_only: bool
    usage: str


class ServerCommandDispatcher:
    """
    Authoritative server-side command execution.
    All permission checks happen on the server.
    """

    def __init__(self, logic: Logic):
        self._logic = logic
        self._commands: dict[str, _CommandSpec] = {
            "help": _CommandSpec("help", False, "/help"),
            "whoami": _CommandSpec("whoami", False, "/whoami"),
            "kick": _CommandSpec("kick", True, "/kick <user-id-prefix> [reason]"),
            "newhost": _CommandSpec("newhost", True, "/newhost <user-id-prefix>"),
        }

    def try_execute(self, actor_id: UUID, raw_message: str) -> bool:
        message = raw_message.strip()
        if len(message) == 0 or not message.startswith("/"):
            return False

        try:
            parts = shell_split(message)
        except ValueError as e:
            self._reply(actor_id, f"invalid command syntax: {e}")
            return True
        if len(parts) == 0:
            self._reply(actor_id, "empty command")
            return True

        raw_name = parts[0][1:].lower()
        args = parts[1:]
        spec = self._commands.get(raw_name)
        if spec is None:
            self._reply(actor_id, f"unknown command: /{raw_name}")
            return True

        if spec.host_only and not self._is_host(actor_id):
            self._reply(actor_id, "permission denied: host role required")
            return True

        if raw_name == "help":
            self._handle_help(actor_id)
            return True
        if raw_name == "whoami":
            self._handle_whoami(actor_id)
            return True
        if raw_name == "kick":
            self._handle_kick(actor_id, args)
            return True
        if raw_name == "newhost":
            self._handle_newhost(actor_id, args)
            return True

        self._reply(actor_id, "unknown command")
        return True

    def _handle_help(self, actor_id: UUID):
        role = self._logic.get_user_role(actor_id)
        base = ["/help", "/whoami"]
        host_only = ["/kick <user-id-prefix> [reason]", "/newhost <user-id-prefix>"]
        if role == Role.HOST:
            body = "available commands: " + ", ".join(base + host_only)
        else:
            body = "available commands: " + ", ".join(base)
        self._reply(actor_id, body)

    def _handle_whoami(self, actor_id: UUID):
        user = self._find_member(actor_id)
        role = self._logic.get_user_role(actor_id)
        self._reply(actor_id, f"you are '{user.get_name()}' ({actor_id}) with role '{role.value}'")

    def _handle_kick(self, actor_id: UUID, args: list[str]):
        if len(args) < 1:
            self._reply(actor_id, f"usage: {self._commands['kick'].usage}")
            return
        target = self._resolve_member(args[0])
        reason = " ".join(args[1:]).strip()
        if target is None:
            self._reply(actor_id, "target user not found")
            return
        if target.get_id() == actor_id:
            self._reply(actor_id, "cannot kick yourself")
            return
        try:
            self._logic.kick_member(target.get_id(), reason)
            self._reply(actor_id, f"kicked '{target.get_name()}'")
        except PermissionError as e:
            self._reply(actor_id, f"permission denied: {e}")
        except KeyError:
            self._reply(actor_id, "target user not found")

    def _handle_newhost(self, actor_id: UUID, args: list[str]):
        if len(args) != 1:
            self._reply(actor_id, f"usage: {self._commands['newhost'].usage}")
            return
        target = self._resolve_member(args[0])
        if target is None:
            self._reply(actor_id, "target user not found")
            return
        try:
            self._logic.transfer_host(target.get_id())
            self._reply(actor_id, f"host transferred to '{target.get_name()}'")
        except KeyError:
            self._reply(actor_id, "target user not found")

    def _is_host(self, user_id: UUID) -> bool:
        try:
            return self._logic.get_user_role(user_id) == Role.HOST
        except KeyError:
            return False

    def _resolve_member(self, token: str) -> User | None:
        token = token.strip().lower()
        if len(token) == 0:
            return None

        # Exact UUID first.
        try:
            user_id = UUID(token)
            for member in self._logic.list_members():
                if member.get_id() == user_id:
                    return member
        except ValueError:
            pass

        # Unique UUID prefix.
        prefix_matches = [m for m in self._logic.list_members() if str(m.get_id()).lower().startswith(token)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
        if len(prefix_matches) > 1:
            return None

        # Unique name (case-insensitive).
        name_matches = [m for m in self._logic.list_members() if m.get_name().lower() == token]
        if len(name_matches) == 1:
            return name_matches[0]
        return None

    def _find_member(self, user_id: UUID) -> User:
        for member in self._logic.list_members():
            if member.get_id() == user_id:
                return member
        raise KeyError("unknown user")

    def _reply(self, recipient_id: UUID, message: str):
        self._logic.send_system_private_message(recipient_id, message)

