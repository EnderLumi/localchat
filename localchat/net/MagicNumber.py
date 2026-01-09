from localchat.net import read_exact
from localchat.util import BinaryIOBase
from typing import final


@final
class MagicNumber:
    _KNOWN_MAGIC : set[int] = set()
    _LENGTH = 8

    def __init__(self, number : int):
        """
        A class used to represent a magic number.
        Every magic number has to be unique.
        :param number: the magic number
        """
        self._number = number
        try:
            self._bytes = number.to_bytes(length=MagicNumber._LENGTH, byteorder='big', signed=True)
        except OverflowError:
            raise ValueError("magic number is too large")
        assert MagicNumber._validate_magic(number), "magic number must be unique"

        """
        Ich würde das assert durch einfaches:
            if not MagicNumber._validate_magic(number):
                raise ValueError("magic number must be unique")
        tauschen.
        Ich habe gehört, assert soll möglichst vermieden werden, weil in veerschiedenen python versionen,
        oder z.B. auch mit der Optimierten Version "Python -O" alle assert statements entfernt werden.
        Man kann assert gut im development/debuggen nehmen, aber nicht bei Programmlogik.
        """

    @staticmethod
    def _validate_magic(magic : int) -> bool:
        if magic in MagicNumber._KNOWN_MAGIC: return False
        MagicNumber._KNOWN_MAGIC.add(magic)
        return True

    def write(self, output_stream : BinaryIOBase):
        """
        :raises IOError: if an IOError occurs when writing to the stream
        :param output_stream:
        :return:
        """
        output_stream.write(self._bytes)

    def read_and_compare(self, input_stream : BinaryIOBase):
        """
        :raises IOError: if an IOError occurs when reading from the stream
        :param input_stream:
        :return:
        """
        b = read_exact(input_stream, MagicNumber._LENGTH)
        other_num = int.from_bytes(b, byteorder='big', signed=True)
        if other_num != self._number:
            raise IOError("incorrect magic number")

    def __eq__(self, other):
        if not isinstance(other, MagicNumber):
            raise TypeError("other must be an instance of MagicNumber")
        return other._number == self._number
    def __ne__(self, other):
        return not self.__eq__(other)
