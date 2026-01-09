from localchat.util import BinaryIOBase


def readinto_exact(input_stream: BinaryIOBase, buffer : bytearray|memoryview[int]):
    """
    Fills the given buffer with bytes from the given stream.
    :param input_stream: the stream where bytes are read from
    :param buffer: the destination buffer
    :return:
    :raises IOError: if an IOError occurs while reading from the stream
    :raises EOFError: if EOF is reached before the destination buffer could be filled
    """
    buffer_view = memoryview(buffer)
    wanted = len(buffer)
    bytes_read = 0
    while bytes_read < wanted:
        new_bytes_read = input_stream.readinto(buffer_view[bytes_read:])
        if new_bytes_read is None:
            raise IOError("input stream must not be in non blocking mode")
        if new_bytes_read == 0:
            ex = EOFError(
                f"unexpected EOF (attempted to read exactly {wanted} bytes,"
                f" but there where only {bytes_read} bytes remaining)"
            )
            raise IOError() from ex
            """
            vielleicht sollte man eine Detailiertere Fehlermeldung formulieren?
            z.B. raise EOFError(f"unexpected EOF after {bytes_read}/{wanted} bytes")
            
            Leon:
            Hab die Fehlermeldung informativer gemacht. Ich hab den EOFError erstmal in einem
            IOError verpackt, da Code der diese Funktion verwendet nur IOError erwartet.
            Mir fällt aber auch kein Fall ein, in dem eine expliziete Unterscheidung
            zwischen einem EOFError und einem IOErrors notwendig währe bei der Fehlerbehandlung in
            Localchat, also können wir es soweit ich sehen kann auch langzeitig so lassen.
            """

        bytes_read += new_bytes_read

def read_exact(input_stream: BinaryIOBase, n : int) -> bytes:
    buffer = bytearray(n)
    readinto_exact(input_stream, buffer)
    return buffer
