from ._base import OutdatedError


class _DBEntryView:
    def __init__(self):
        super().__init__()
        self._is_outdated = False

    def _mark_db_entry_view_as_outdated(self):
        self._is_outdated = True

    @staticmethod
    def _outdated_error() -> OutdatedError:
        return OutdatedError(f"view of database entry is outdated and needs to be reloaded")

    def _ensure_is_not_outdated(self):
        if self._is_outdated:
            raise self._outdated_error()

