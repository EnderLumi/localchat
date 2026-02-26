from localchat.util.event import Event
from typing import Generic, TypeVar
from abc import ABC, abstractmethod


_T = TypeVar('_T')

class EventListener(ABC, Generic[_T]):

    @abstractmethod
    def on_event(self, event : Event[_T]):
        raise NotImplementedError()
