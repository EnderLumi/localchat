from __future__ import annotations

from typing import Callable, Protocol
from uuid import UUID


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

    def run(self, appearance: MutableAppearance):
        while True:
            self._output_writer("=== Settings ===")
            self._output_writer(f"Current name: {appearance.get_name()}")
            self._output_writer(f"Current ID:   {appearance.get_id()}")
            self._output_writer("1) Change name")
            self._output_writer("2) Change ID")
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

    def _read_line(self, prompt: str) -> str | None:
        try:
            return self._input_reader(prompt)
        except (EOFError, KeyboardInterrupt):
            self._output_writer("")
            return None
