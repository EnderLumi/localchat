import uuid


class User:
    def __init__(self): ...

    def get_id(self) -> uuid.UUID: ...
    def get_name(self) -> str: ...

    def __eq__(self, other) -> bool:
        if not isinstance(other, User): return False
        return self.get_id() == other.get_id()
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.get_id())
