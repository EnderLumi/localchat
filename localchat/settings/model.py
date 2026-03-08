from __future__ import annotations

from dataclasses import dataclass

from localchat.config.defaults import (
    DEFAULT_CHAT_EXPORT_PATH,
    DEFAULT_ENABLE_COMMAND_SUGGESTIONS,
    DEFAULT_HOST_SERVER_PORT,
    DEFAULT_NAME_COLOR,
    DEFAULT_SHOW_JOIN_LEAVE_NOTIFICATIONS,
    DEFAULT_SHOW_TIMESTAMPS,
    DEFAULT_THEME,
)


@dataclass
class AppSettings:
    username: str
    name_color: str
    default_host_server_port: int
    show_timestamps: bool
    show_join_leave_notifications: bool
    default_chat_export_path: str
    enable_command_suggestions: bool
    theme: str

    @classmethod
    def default(cls) -> "AppSettings":
        return cls(
            username="",
            name_color=DEFAULT_NAME_COLOR,
            default_host_server_port=DEFAULT_HOST_SERVER_PORT,
            show_timestamps=DEFAULT_SHOW_TIMESTAMPS,
            show_join_leave_notifications=DEFAULT_SHOW_JOIN_LEAVE_NOTIFICATIONS,
            default_chat_export_path=DEFAULT_CHAT_EXPORT_PATH,
            enable_command_suggestions=DEFAULT_ENABLE_COMMAND_SUGGESTIONS,
            theme=DEFAULT_THEME,
        )

