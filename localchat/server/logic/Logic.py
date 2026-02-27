from abc import ABC, abstractmethod
from uuid import UUID

from localchat.util import BinaryIOBase, ChatInformation, Role, User, UserMessage
from localchat.util.event import EventHandler


class Logic(ABC):
    """
    Server-side control interface.
    Implementations handle lifecycle, membership, moderation and server state.
    """

    def __init__(self):
        super().__init__()

    # Lifecycle
    @abstractmethod
    def start(self):
        """
        Starts the server logic.
        :raises RuntimeError: if already running
        :raises IOError: if startup fails due to network or IO errors
        """

    @abstractmethod
    def stop(self):
        """
        Stops the server logic and disconnects clients.
        :raises RuntimeError: if server is not running
        :raises IOError: if shutdown fails due to network or IO errors
        """

    @abstractmethod
    def is_running(self) -> bool: ...

    @abstractmethod
    def get_uptime_seconds(self) -> float: ...

    # Server metadata
    @abstractmethod
    def get_server_info(self) -> ChatInformation: ...

    @abstractmethod
    def set_server_name(self, new_name: str):
        """
        Updates the public server/chat name.
        :raises IOError:
        """

    @abstractmethod
    def set_server_password(self, new_password: str | None):
        """
        Sets or clears the server password.
        Pass None to clear the password.
        :raises IOError:
        """

    @abstractmethod
    def set_locked(self, locked: bool):
        """
        Locks/unlocks joins for non-host users.
        :raises IOError:
        """

    @abstractmethod
    def is_locked(self) -> bool: ...

    @abstractmethod
    def set_host_client_port(self, port: int):
        """
        Sets the localhost client port for host-bridge scenarios.
        :raises ValueError: if port is invalid
        """

    @abstractmethod
    def get_host_client_port(self) -> int | None: ...

    # Membership and roles
    @abstractmethod
    def register_member(self, user: User, role: Role = Role.MEMBER):
        """
        Registers a connected member in server state.
        Implementations should enforce ban/lock rules.
        :raises PermissionError: if join is not permitted
        :raises IOError:
        """

    @abstractmethod
    def list_members(self) -> list[User]: ...

    @abstractmethod
    def get_host_user(self) -> User: ...

    @abstractmethod
    def get_user_role(self, user_id: UUID) -> Role: ...

    @abstractmethod
    def transfer_host(self, new_host_id: UUID):
        """
        Transfers host role to another connected member.
        :raises KeyError: if member is unknown
        :raises IOError:
        """

    # Moderation
    @abstractmethod
    def kick_member(self, user_id: UUID, reason: str = ""):
        """
        Disconnects a member.
        :raises KeyError: if member is unknown
        :raises IOError:
        """

    @abstractmethod
    def ban_member(self, user_id: UUID, reason: str = ""):
        """
        Bans and disconnects a member.
        :raises KeyError: if member is unknown
        :raises IOError:
        """

    @abstractmethod
    def unban_member(self, user_id: UUID):
        """
        Removes a user from ban list.
        :raises IOError:
        """

    @abstractmethod
    def list_banned_users(self) -> set[UUID]: ...

    # Messages and persistence
    @abstractmethod
    def post_system_message(self, message: str):
        """
        Broadcasts a server-originated public message.
        :raises IOError:
        """

    @abstractmethod
    def send_system_private_message(self, recipient_id: UUID, message: str):
        """
        Sends a server-originated private message to exactly one member.
        :raises KeyError: if recipient is unknown
        :raises IOError:
        """

    @abstractmethod
    def save_chat(self, output_stream: BinaryIOBase):
        """
        Serializes chat history to a stream.
        :raises IOError:
        """

    @abstractmethod
    def export_state(self, output_stream: BinaryIOBase):
        """
        Exports full server state for host migration / backup.
        :raises IOError:
        """

    @abstractmethod
    def import_state(self, input_stream: BinaryIOBase, merge: bool = False):
        """
        Imports full server state.
        If merge is False, existing state is replaced.
        :raises IOError:
        """

    # Events
    @abstractmethod
    def on_member_joined(self) -> EventHandler[User]: ...

    @abstractmethod
    def on_member_left(self) -> EventHandler[User]: ...

    @abstractmethod
    def on_member_role_changed(self) -> EventHandler[User]: ...

    @abstractmethod
    def on_public_message(self) -> EventHandler[UserMessage]: ...

    @abstractmethod
    def on_private_message(self) -> EventHandler[UserMessage]: ...

    # Messages emitted via on_public_message/on_private_message should be
    # authoritative server-side records (sender and timestamp set by server logic).

    @abstractmethod
    def on_error(self) -> EventHandler[IOError]: ...
