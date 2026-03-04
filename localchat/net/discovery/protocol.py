import json
from dataclasses import dataclass
from uuid import UUID

from localchat.config.limits import MAX_CHAT_NAME_LENGTH
from localchat.net.discovery.models import DiscoveredServer


_VERSION = 1
_REQ_KIND = "discover_request"
_RES_KIND = "discover_response"


@dataclass(frozen=True)
class DiscoveryRequest:
    nonce: UUID
    reply_port: int


@dataclass(frozen=True)
class DiscoveryResponse:
    nonce: UUID
    server: DiscoveredServer


def encode_discovery_request(request: DiscoveryRequest) -> bytes:
    _validate_port(request.reply_port)
    payload = {
        "v": _VERSION,
        "kind": _REQ_KIND,
        "nonce": str(request.nonce),
        "reply_port": request.reply_port,
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def decode_discovery_request(payload: bytes) -> DiscoveryRequest:
    obj = _decode_json(payload)
    _validate_common(obj, _REQ_KIND)
    nonce = _parse_uuid(obj.get("nonce"), "nonce")
    reply_port = _parse_int(obj.get("reply_port"), "reply_port")
    _validate_port(reply_port)
    return DiscoveryRequest(nonce=nonce, reply_port=reply_port)


def encode_discovery_response(response: DiscoveryResponse) -> bytes:
    _validate_server(response.server)
    payload = {
        "v": _VERSION,
        "kind": _RES_KIND,
        "nonce": str(response.nonce),
        "server_id": str(response.server.server_id),
        "server_name": response.server.server_name,
        "host": response.server.host,
        "port": response.server.port,
        "requires_password": bool(response.server.requires_password),
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def decode_discovery_response(payload: bytes) -> DiscoveryResponse:
    obj = _decode_json(payload)
    _validate_common(obj, _RES_KIND)
    nonce = _parse_uuid(obj.get("nonce"), "nonce")
    server_id = _parse_uuid(obj.get("server_id"), "server_id")
    server_name = _parse_str(obj.get("server_name"), "server_name")
    if len(server_name) == 0 or len(server_name) > MAX_CHAT_NAME_LENGTH:
        raise IOError("invalid server_name length")
    host = _parse_str(obj.get("host"), "host")
    if len(host) == 0:
        raise IOError("invalid host")
    port = _parse_int(obj.get("port"), "port")
    _validate_port(port)
    requires_password = bool(obj.get("requires_password", False))
    return DiscoveryResponse(
        nonce=nonce,
        server=DiscoveredServer(
            server_id=server_id,
            server_name=server_name,
            host=host,
            port=port,
            requires_password=requires_password,
        ),
    )


def _decode_json(payload: bytes) -> dict:
    try:
        raw = payload.decode("utf-8")
    except UnicodeDecodeError as e:
        raise IOError("payload is not valid utf-8") from e
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise IOError("payload is not valid json") from e
    if not isinstance(obj, dict):
        raise IOError("payload must be an object")
    return obj


def _validate_common(obj: dict, expected_kind: str):
    v = _parse_int(obj.get("v"), "v")
    if v != _VERSION:
        raise IOError("unsupported discovery version")
    kind = _parse_str(obj.get("kind"), "kind")
    if kind != expected_kind:
        raise IOError("unexpected discovery kind")


def _validate_server(server: DiscoveredServer):
    if len(server.server_name) == 0 or len(server.server_name) > MAX_CHAT_NAME_LENGTH:
        raise ValueError("invalid server_name length")
    if len(server.host) == 0:
        raise ValueError("invalid host")
    _validate_port(server.port)


def _parse_uuid(value, field: str) -> UUID:
    if not isinstance(value, str):
        raise IOError(f"invalid {field}")
    try:
        return UUID(value)
    except ValueError as e:
        raise IOError(f"invalid {field}") from e


def _parse_int(value, field: str) -> int:
    if not isinstance(value, int):
        raise IOError(f"invalid {field}")
    return value


def _parse_str(value, field: str) -> str:
    if not isinstance(value, str):
        raise IOError(f"invalid {field}")
    return value


def _validate_port(port: int):
    if port <= 0 or port > 65535:
        raise IOError("invalid port")
