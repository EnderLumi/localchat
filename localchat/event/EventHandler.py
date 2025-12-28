from localchat.event import Event, EventListener
from typing import TypeVar, Generic, final, Iterable
from threading import RLock


_T = TypeVar('_T')

@final
class EventHandler(Generic[_T]):
    def __init__(self):
        self._listener : set[EventListener[_T]] = set()
        self._lock = RLock()

    def add_listener(self, listener: EventListener[_T]):
        with self._lock:
            self._listener.add(listener)

    def remove_listener(self, listener: EventListener[_T]):
        with self._lock:
            if listener in self._listener:
                self._listener.remove(listener)

    def update_listeners(self, listeners: Iterable[EventListener[_T]]):
        with self._lock:
            self._listener.update(listeners)

    def clear_listeners(self):
        with self._lock:
            self._listener.clear()

    def handle(self, event: Event[_T]):
        with self._lock:
            current_listeners = list(self._listener)
        for listener in current_listeners:
            listener.on_event(event)
