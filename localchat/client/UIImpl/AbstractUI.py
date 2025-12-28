from localchat.client import UI, Logic
from typing import final


class AbstractUI(UI):
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
            raise AssertionError("logic is not set")
        self.start_impl()

    def start_impl(self):
        raise NotImplementedError()
