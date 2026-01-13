from localchat.util import Chat, User, UserMessage
from localchat.util.event import EventHandler
from threading import RLock
from typing import final


class AbstractChat(Chat):
    def __init__(self):
        super().__init__()
        self._lock = RLock()

        self._user_joined_handler : EventHandler[User] = EventHandler()
        self._user_left_handler : EventHandler[User] = EventHandler()
        self._user_became_host_handler : EventHandler[User] = EventHandler()
        self._user_posted_message_handler : EventHandler[UserMessage] = EventHandler()
        self._user_send_message_handler : EventHandler[UserMessage] = EventHandler()
        self._connection_problem_handler : EventHandler[float] = EventHandler()
        self._connection_failure_handler : EventHandler[IOError] = EventHandler()

    @final
    def clear_handlers(self):
        self._user_joined_handler.clear_listeners()
        self._user_left_handler.clear_listeners()
        self._user_became_host_handler.clear_listeners()
        self._user_posted_message_handler.clear_listeners()
        self._user_send_message_handler.clear_listeners()
        self._connection_problem_handler.clear_listeners()
        self._connection_failure_handler.clear_listeners()

    @final
    def on_user_joined(self) -> EventHandler[User]:
        return self._user_joined_handler

    @final
    def on_user_left(self) -> EventHandler[User]:
        return self._user_left_handler

    @final
    def on_user_became_host(self) -> EventHandler[User]:
        return self._user_became_host_handler

    @final
    def on_user_posted_message(self) -> EventHandler[UserMessage]:
        return self._user_posted_message_handler

    @final
    def on_user_send_private_message(self) -> EventHandler[UserMessage]:
        return self._user_send_message_handler

    @final
    def on_connection_problem(self) -> EventHandler[float]:
        return self._connection_problem_handler

    @final
    def on_connection_failure(self) -> EventHandler[IOError]:
        return self._connection_failure_handler