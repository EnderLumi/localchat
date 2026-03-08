from __future__ import annotations

from typing import Callable, Protocol
from uuid import UUID

from localchat.settings import AppSettings
from localchat.settings.validators import available_color_names, normalize_name_color


class MutableAppearance(Protocol):
    def get_name(self) -> str: ...
    def get_id(self) -> UUID: ...
    def set_name(self, user_name: str): ...
    def set_id(self, user_id: UUID): ...


class CLISettingsUI:
    def __init__(
        self,
        input_reader: Callable[[str], str] = input,
        output_writer: Callable[[str], None] = print,
    ):
        self._input_reader = input_reader
        self._output_writer = output_writer

    def run(self, appearance: MutableAppearance, settings: AppSettings | None = None):
        while True:
            self._output_writer("=== Settings ===")
            self._output_writer(f"Current name: {appearance.get_name()}")
            self._output_writer(f"Current ID:   {appearance.get_id()}")
            if settings is not None:
                self._output_writer(f"Name color:   {settings.name_color}")
            self._output_writer("1) Change name")
            self._output_writer("2) Change ID")
            if settings is not None:
                self._output_writer("3) Change name color")
            self._output_writer("0) Back")

            choice = self._read_line("settings> ")
            if choice is None:
                return

            choice = choice.strip()
            if choice == "0":
                return
            if choice == "1":
                self._change_name(appearance)
                continue
            if choice == "2":
                self._change_id(appearance)
                continue
            if choice == "3" and settings is not None:
                self._change_name_color(settings)
                continue

            self._output_writer("Invalid selection.")

    def _change_name(self, appearance: MutableAppearance):
        new_name = self._read_line("New name: ")
        if new_name is None:
            return
        new_name = new_name.strip()
        if len(new_name) == 0:
            self._output_writer("Name must not be empty.")
            return
        appearance.set_name(new_name)
        self._output_writer(f"Name updated: {new_name}")

    def _change_id(self, appearance: MutableAppearance):
        raw_id = self._read_line("New ID (UUID): ")
        if raw_id is None:
            return
        raw_id = raw_id.strip()
        try:
            new_id = UUID(raw_id)
        except ValueError:
            self._output_writer("Invalid UUID.")
            return
        appearance.set_id(new_id)
        self._output_writer(f"ID updated: {new_id}")

    def _change_name_color(self, settings: AppSettings):
        raw_color = self._read_line("New name color (config color name or #RRGGBB): ")
        if raw_color is None:
            return
        try:
            normalized = normalize_name_color(raw_color)
        except ValueError as e:
            preview = ", ".join(sorted(available_color_names()))
            self._output_writer(f"Invalid color: {e}")
            self._output_writer(f"Allowed color names: {preview}")
            return
        settings.name_color = normalized
        self._output_writer(f"Name color updated: {normalized}")

    def _read_line(self, prompt: str) -> str | None:
        try:
            return self._input_reader(prompt)
        except (EOFError, KeyboardInterrupt):
            self._output_writer("")
            return None
