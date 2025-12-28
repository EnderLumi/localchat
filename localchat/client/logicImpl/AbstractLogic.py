from localchat.client import UI, Logic
from typing import final
from threading import Thread, RLock


_READY = 0
_RUNNING = 1
_STOPPING = 2
_STOPPED = 3

class AbstractLogic(Logic):
    def __init__(self):
        super().__init__()
        # noinspection PyTypeChecker
        self.ui : UI = None
        self.ui_ready = False
        self._lock = RLock()
        self._state = _READY
        # self._ui_thread = None
        self._logic_thread = None

    @final
    def set_ui(self, ui : object):
        with self._lock:
            if self._state != _READY:
                raise RuntimeError('expected state: READY')
            if not isinstance(ui,UI):
                raise TypeError('ui must be an instance of UI')
            self.ui_ready = False
            self.ui = ui

    @final
    def ui_initialized(self):
        current_state = self._state
        if current_state == _STOPPING or current_state == _STOPPED: return
        with self._lock:
            if self._state == _STOPPING or self._state == _STOPPED: return
            if self._state == _READY:
                raise RuntimeError('unexpected state: READY')
            self.ui_ready = True

    @final
    def start(self):
        with self._lock:
            if self._state != _READY:
                raise RuntimeError('expected state: READY')
            if self.ui is None:
                raise AssertionError('ui is not set')

            self._state = _RUNNING

            self._logic_thread = Thread(target=self.start_impl, name="localchat logic main thread")
            self._logic_thread.start()

            # The ui is executed by the current thread,
            # because many GUI libraries require the
            # calling thread to be the main thread.
        self.ui.start()

    @final
    def shutdown(self):
        current_state = self._state
        if current_state == _STOPPING or current_state == _STOPPED: return
        with self._lock:
            if self._state == _STOPPING or self._state == _STOPPED: return
            if self._state != _RUNNING:
                raise RuntimeError('expected state: RUNNING')
            self._state = _STOPPING

            self.ui.shutdown()
            self.shutdown_impl()
            self._logic_thread.join()

            self._state = _STOPPED

    def start_impl(self):
        raise NotImplementedError()

    def shutdown_impl(self):
        raise NotImplementedError()
