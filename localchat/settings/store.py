from __future__ import annotations

import json
from pathlib import Path

from localchat.config.defaults import SETTINGS_FILE
from localchat.settings.model import AppSettings
from localchat.settings.validators import normalize_name_color


class SettingsStore:
    def __init__(self, path: str = SETTINGS_FILE):
        self._path = Path(path).expanduser()

    def load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings.default()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppSettings.default()
        if not isinstance(raw, dict):
            return AppSettings.default()

        defaults = AppSettings.default()
        return AppSettings(
            username=self._as_str(raw.get("username"), defaults.username),
            name_color=self._as_name_color(raw.get("name_color"), defaults.name_color),
            default_host_server_port=self._as_port(
                raw.get("default_host_server_port"),
                defaults.default_host_server_port,
            ),
            show_timestamps=self._as_bool(raw.get("show_timestamps"), defaults.show_timestamps),
            show_join_leave_notifications=self._as_bool(
                raw.get("show_join_leave_notifications"),
                defaults.show_join_leave_notifications,
            ),
            default_chat_export_path=self._as_str(
                raw.get("default_chat_export_path"),
                defaults.default_chat_export_path,
            ),
            enable_command_suggestions=self._as_bool(
                raw.get("enable_command_suggestions"),
                defaults.enable_command_suggestions,
            ),
            theme=self._as_str(raw.get("theme"), defaults.theme),
        )

    def save(self, settings: AppSettings):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "username": settings.username,
            "name_color": settings.name_color,
            "default_host_server_port": settings.default_host_server_port,
            "show_timestamps": settings.show_timestamps,
            "show_join_leave_notifications": settings.show_join_leave_notifications,
            "default_chat_export_path": settings.default_chat_export_path,
            "enable_command_suggestions": settings.enable_command_suggestions,
            "theme": settings.theme,
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    @staticmethod
    def _as_str(value, fallback: str) -> str:
        if isinstance(value, str):
            return value
        return fallback

    @staticmethod
    def _as_bool(value, fallback: bool) -> bool:
        if isinstance(value, bool):
            return value
        return fallback

    @staticmethod
    def _as_port(value, fallback: int) -> int:
        if not isinstance(value, int):
            return fallback
        if value <= 0 or value > 65535:
            return fallback
        return value

    @staticmethod
    def _as_name_color(value, fallback: str) -> str:
        if not isinstance(value, str):
            return fallback
        try:
            return normalize_name_color(value)
        except ValueError:
            return fallback
