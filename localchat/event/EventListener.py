from localchat.event import Event
from typing import Generic, TypeVar


_T = TypeVar('_T')

class EventListener(Generic[_T]):
    def on_event(self, event : Event[_T]):
        raise NotImplementedError()
