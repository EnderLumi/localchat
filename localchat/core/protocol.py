# Message formats, serialization, packet types
import json
import time

PACKET_TYPES= {
    "public",
    "private",
    "join",
    "leave",
    "system",
    "info",
    "error",
    "ping",
    "pong"
}

REQUIRED_FIELDS = {
    "type",
    "from",
    "timestamp",
    "payload"
}


def make_packet(packet_type, sender, payload, **kwargs):
    if packet_type not in PACKET_TYPES:
        raise ValueError(f"Unbekannter Pakettyp: {packet_type}")
        #raise ValueError("Unknown packet type '%s'" % packet_type)
    if not isinstance(payload, dict):
        raise TypeError("Payload must be a dict")

    packet = {
        "type": packet_type,
        "from": sender,
        "timestamp": time.time(),
        "payload": payload,
    }

    # optional fields like {"to"} for /msg
    packet.update(kwargs)
    return packet


def encode_packet(packet):
    # dict -> UTF-8 bytes
    if not isinstance(packet, dict):
        raise TypeError("packet must be a dict")
    try:
        json_text = json.dumps(packet, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Error during serialization: {e}")
    return json_text.encode("utf-8")


def decode_packet(raw):
    # bytes -> dict
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be a bytes or bytearray")
    try:
        text = raw.decode("utf-8")
        packet = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"Error during decoding packet: {e}")
    return packet


def validate_packet(packet):
    # checks structural validity
    if not isinstance(packet, dict):
        return False
    if not REQUIRED_FIELDS.issubset(packet.keys()):
        return False
    if packet["type"] not in PACKET_TYPES:
        return False
    if not isinstance(packet["payload"], dict):
        return False
    return True
