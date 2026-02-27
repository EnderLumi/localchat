from uuid import UUID

from localchat.server.logicImpl.AbstractLogic import AbstractLogic
from localchat.util import UserMessage


class InMemoryLogic(AbstractLogic):
    """
    Minimal reference implementation without network transport.
    Useful as a stable base for tests and for implementing other variants.
    Broadcast/private send hooks are no-ops by design.
    """

    def __init__(self):
        super().__init__()
        self._password: str | None = None

    def _on_start_impl(self):
        return

    def _on_stop_impl(self):
        return

    def _disconnect_member_impl(self, user_id: UUID, reason: str):
        return

    def _broadcast_public_impl(self, user_message: UserMessage):
        return

    def _send_private_impl(self, recipient_id: UUID, user_message: UserMessage):
        return

    def _set_server_password_impl(self, new_password: str | None):
        self._password = new_password
