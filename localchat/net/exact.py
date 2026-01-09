from localchat.util import BinaryIOBase


def readinto_exact(input_stream: BinaryIOBase, buffer : bytearray):
    buffer_view = memoryview(buffer)
    wanted = len(buffer)
    bytes_read = 0
    while bytes_read < wanted:
        new_bytes_read = input_stream.readinto(buffer_view[bytes_read:])
        if new_bytes_read is None:
            raise IOError("input stream must not be in non blocking mode")
        if new_bytes_read == 0:
            raise IOError("unexpected EOF")

            """
            vielleicht sollte man eine Detailiertere Fehlermeldung formulieren?
            z.B. raise EOFError(f"unexpected EOF after {bytes_read}/{wanted} bytes")
            """

        bytes_read += new_bytes_read

def read_exact(input_stream: BinaryIOBase, n : int) -> bytes:
    buffer = bytearray(n)
    readinto_exact(input_stream, buffer)
    return buffer
