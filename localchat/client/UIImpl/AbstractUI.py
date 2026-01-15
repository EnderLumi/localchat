from localchat.client import UI, Logic
from typing import final
from threading import main_thread, current_thread


class AbstractUI(UI):
    """
    Die AbstractUI-Klasse vereinfacht die implementierung einer UI-Klasse und sollte
    überladen werden, wenn man eine Implementierung der UI-Klasse erstellen möchte.

    Die Klasse stellt die 'logic'-Variable bereit und überprüft, dass der Main-Thread
    die 'start'-Methode aufruft (Viele GUI-Bibliotheken, erlauben nur dem Main-Thread
    bestimmte Methoden aufzurufen).

    Sobald 'start_impl' aufgerufen wird, steht in der 'logic'-Variable
    eine implementierung der Logic-Klasse bereit, die von der UI
    genutzt werden kann.

    (Siehe Client-UI für mehr Details über die Client-UI-Klasse an sich.)
    """

    def __init__(self):
        super().__init__()
        # noinspection PyTypeChecker
        self.logic : Logic = None

    @final
    def set_logic(self, logic : object):
        if not isinstance(logic, Logic):
            raise TypeError("logic must be an instance of Logic")
        self.logic = logic
    @final
    def start(self):
        if self.logic is None:
            raise RuntimeError("logic is not set")
        if current_thread() != main_thread():
            raise RuntimeError("ui must be started by main thread")
        self.start_impl()

    def start_impl(self):
        raise NotImplementedError()
