from localchat.net import MagicNumber
from localchat.util import BinaryIOBase
from typing import final


class Serializable:
    """
    Every class that implements 'Serializable' also needs to have its own 'MAGIC' variable.
    Every MagicNumber created has to be unique.
    (The static variable 'MAGIC' is used in 'serialize' and 'validate_magic'.)
    """
    MAGIC: MagicNumber = MagicNumber(0)
    # Ist es gewollt hier eine globale MagicNumber(0) zu erzeugen?

    # Ja das soll so.
    # Das 'MAGIC' in 'Serializable' wird überschattet durch das 'MAGIC' in
    # der Klasse, die 'Serializable' implementiert.
    # In Serializable selbst eine MAGIC-Variable zu haben ermöglicht es,
    # in Methoden, die nicht genauer spezifiezierte Serializable-Objekte verwenden, auf MAGIC
    # zuzugreifen. (So wie es in 'serialize' und 'validate_magic' getan wird.)

    @final
    def serialize(self, output_stream: BinaryIOBase):
        """
        :raises IOError: if an IOError occurs when writing to the stream
        :param output_stream: destination of the serialized object
        :return:
        """
        if self.MAGIC == Serializable.MAGIC:
            raise RuntimeError("magic number must be overwritten by child class")

        self.MAGIC.write(output_stream)
        self.serialize_impl(output_stream)

    def serialize_impl(self, output_stream: BinaryIOBase):
        """
        :raises IOError: if an IOError occurs when writing to the stream
        :param output_stream: destination of the serialized object
        :return:
        """
        raise NotImplementedError()

    @classmethod
    @final
    def validate_magic(cls, input_stream: BinaryIOBase):
        """
        :raises IOError: if the magic number is invalid or if an IOError
            occurs while reading from the stream.
        :param input_stream: the stream the magic number is read from
        """
        if cls.MAGIC == Serializable.MAGIC:
            raise RuntimeError("magic number must be overwritten by child class")
        cls.MAGIC.read_and_compare(input_stream)
