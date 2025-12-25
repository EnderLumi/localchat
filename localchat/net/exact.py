from io import RawIOBase

def readinto_exact(input_stream: RawIOBase, buffer : bytearray):
    wanted = len(buffer)
    bytes_read = 0
    while bytes_read < wanted:
        new_bytes_read = input_stream.readinto(buffer[bytes_read:])
        if new_bytes_read is None:
            raise IOError("input stream must not be in non blocking mode")
        if bytes_read == 0:
            raise IOError("unexpected EOF")
        bytes_read += new_bytes_read

def read_exact(input_stream: RawIOBase, n : int) -> bytes:
    buffer = bytearray(n)
    readinto_exact(input_stream, buffer)
    return buffer
