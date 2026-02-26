from localchat.util import User
from abc import ABC, abstractmethod

class UserMessage(ABC):

    @abstractmethod
    def sender(self) -> User: ...

    @abstractmethod
    def message(self) -> str: ...

    @abstractmethod
    def timestamp(self) -> float: ...
