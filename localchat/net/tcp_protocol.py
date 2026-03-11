from io import BytesIO
from socket import socket

from localchat.config.limits import MAX_MESSAGE_LENGTH, MAX_TCP_PACKET_SIZE
from localchat.net import SerializableString, SerializableUser, SerializableUserMessage, SerializableUUID
from localchat.util import User, UserMessage


# Client -> server packet types
PT_C_JOIN = 1
PT_C_PUBLIC = 2
PT_C_PRIVATE = 3
PT_C_LEAVE = 4

# Server -> client packet types
PT_S_USER_JOINED = 100
PT_S_USER_LEFT = 101
PT_S_USER_BECAME_HOST = 102
PT_S_JOIN_ACK = 105
PT_S_JOIN_NACK = 106
PT_S_PUBLIC = 110
PT_S_PRIVATE = 111
PT_S_ERROR = 120

# Structured server error codes
ERR_GENERIC = "generic"
ERR_ALREADY_JOINED = "already_joined"
ERR_DISCONNECTED = "disconnected"
ERR_INVALID_USER_NAME = "invalid_user_name"
ERR_JOIN_FIRST = "join_first"
ERR_JOIN_FAILED = "join_failed"
ERR_JOIN_REJECTED = "join_rejected"
ERR_JOIN_TIMEOUT = "join_timeout"
ERR_RATE_LIMITED = "rate_limited"
ERR_SERVER_FULL = "server_full"
ERR_USER_NAME_IN_USE = "user_name_in_use"
ERR_USER_ID_IN_USE = "user_id_in_use"
ERR_UNKNOWN_COMMAND = "unknown_command"
ERR_UNKNOWN_PACKET_TYPE = "unknown_packet_type"
ERR_UNKNOWN_RECIPIENT = "unknown_recipient"

def recv_packet(sock: socket, max_payload_size: int = MAX_TCP_PACKET_SIZE) -> bytes:
    length_bytes = _recv_exact_socket(sock, 4)
    payload_len = int.from_bytes(length_bytes, "big")
    if payload_len <= 0 or payload_len > max_payload_size:
        raise IOError("invalid payload size")
    payload = _recv_exact_socket(sock, payload_len)
    return payload


def send_packet(sock: socket, payload: bytes):
    payload_len = len(payload)
    if payload_len <= 0:
        raise ValueError("payload must not be empty")
    sock.sendall(payload_len.to_bytes(4, "big") + payload)


def _recv_exact_socket(sock: socket, n: int) -> bytes:
    chunks: list[bytes] = []
    bytes_left = n
    while bytes_left > 0:
        chunk = sock.recv(bytes_left)
        if chunk == b"":
            ex = EOFError("unexpected EOF while reading packet")
            raise IOError() from ex
        chunks.append(chunk)
        bytes_left -= len(chunk)
    return b"".join(chunks)


def _build_payload(packet_type: int, body: bytes = b"") -> bytes:
    if packet_type < 0 or packet_type > 255:
        raise ValueError("packet type out of range")
    return bytes([packet_type]) + body


def encode_join(user: User) -> bytes:
    buffer = BytesIO()
    SerializableUser.create_copy(user).serialize(buffer)
    return _build_payload(PT_C_JOIN, buffer.getvalue())


def encode_public_message(message: str) -> bytes:
    buffer = BytesIO()
    SerializableString(message).serialize(buffer)
    return _build_payload(PT_C_PUBLIC, buffer.getvalue())


def encode_private_message(recipient_id, message: str) -> bytes:
    buffer = BytesIO()
    SerializableUUID(recipient_id).serialize(buffer)
    SerializableString(message).serialize(buffer)
    return _build_payload(PT_C_PRIVATE, buffer.getvalue())


def encode_leave() -> bytes:
    return _build_payload(PT_C_LEAVE)


def encode_server_public_message(user_message: UserMessage) -> bytes:
    buffer = BytesIO()
    SerializableUserMessage.create_copy(user_message).serialize(buffer)
    return _build_payload(PT_S_PUBLIC, buffer.getvalue())


def encode_server_join_ack(user: User) -> bytes:
    buffer = BytesIO()
    SerializableUser.create_copy(user).serialize(buffer)
    return _build_payload(PT_S_JOIN_ACK, buffer.getvalue())


def encode_server_join_nack(code: str, message: str | None = None) -> bytes:
    if message is None:
        message = code
        code = ERR_GENERIC
    buffer = BytesIO()
    SerializableString(code).serialize(buffer)
    SerializableString(message).serialize(buffer)
    return _build_payload(PT_S_JOIN_NACK, buffer.getvalue())


def encode_server_private_message(user_message: UserMessage) -> bytes:
    buffer = BytesIO()
    SerializableUserMessage.create_copy(user_message).serialize(buffer)
    return _build_payload(PT_S_PRIVATE, buffer.getvalue())


def encode_server_user_joined(user: User) -> bytes:
    buffer = BytesIO()
    SerializableUser.create_copy(user).serialize(buffer)
    return _build_payload(PT_S_USER_JOINED, buffer.getvalue())


def encode_server_user_left(user: User) -> bytes:
    buffer = BytesIO()
    SerializableUser.create_copy(user).serialize(buffer)
    return _build_payload(PT_S_USER_LEFT, buffer.getvalue())


def encode_server_user_became_host(user: User) -> bytes:
    buffer = BytesIO()
    SerializableUser.create_copy(user).serialize(buffer)
    return _build_payload(PT_S_USER_BECAME_HOST, buffer.getvalue())


def encode_server_error(code: str, message: str | None = None) -> bytes:
    if message is None:
        message = code
        code = ERR_GENERIC
    buffer = BytesIO()
    SerializableString(code).serialize(buffer)
    SerializableString(message).serialize(buffer)
    return _build_payload(PT_S_ERROR, buffer.getvalue())


def decode_server_error(body_stream: BytesIO) -> tuple[str, str]:
    """
    Decodes server errors.
    Supports:
    - structured payload: <code><message>
    - legacy payload: <message>
    """
    first = SerializableString.deserialize(body_stream, MAX_MESSAGE_LENGTH).value
    remaining = len(body_stream.getbuffer()) - body_stream.tell()
    if remaining == 0:
        return ERR_GENERIC, first
    # New format contains a second string.
    second = SerializableString.deserialize(body_stream, MAX_MESSAGE_LENGTH).value
    return first, second


def decode_server_join_nack(body_stream: BytesIO) -> tuple[str, str]:
    code = SerializableString.deserialize(body_stream, MAX_MESSAGE_LENGTH).value
    message = SerializableString.deserialize(body_stream, MAX_MESSAGE_LENGTH).value
    return code, message


def decode_server_join_ack(body_stream: BytesIO) -> SerializableUser:
    return SerializableUser.deserialize(body_stream)


def decode_client_packet(payload: bytes) -> tuple[int, BytesIO]:
    if len(payload) < 1:
        raise IOError("empty packet")
    return payload[0], BytesIO(payload[1:])


def decode_join(body_stream: BytesIO) -> SerializableUser:
    return SerializableUser.deserialize(body_stream)


def decode_public_message(body_stream: BytesIO) -> str:
    return SerializableString.deserialize(body_stream, MAX_MESSAGE_LENGTH).value


def decode_private_message(body_stream: BytesIO) -> tuple[SerializableUUID, str]:
    recipient = SerializableUUID.deserialize(body_stream)
    message = SerializableString.deserialize(body_stream, MAX_MESSAGE_LENGTH).value
    return recipient, message
