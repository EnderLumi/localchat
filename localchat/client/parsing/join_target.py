from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class JoinTarget:
    host: str
    port: int
    room: str | None = None
    scheme: str | None = None
    raw: str = ""


def parse_join_target(raw_target: str) -> JoinTarget:
    raw_target = raw_target.strip()
    if len(raw_target) == 0:
        raise ValueError("join target must not be empty")

    if "://" in raw_target:
        return _parse_join_url(raw_target)
    return _parse_host_port(raw_target)


def _parse_join_url(raw_target: str) -> JoinTarget:
    parsed = urlsplit(raw_target)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("unsupported URL scheme (expected http or https)")
    if parsed.hostname is None:
        raise ValueError("URL host is missing")

    if parsed.port is None:
        port = 443 if parsed.scheme == "https" else 80
    else:
        port = parsed.port

    room = _extract_room(parsed.path)
    return JoinTarget(
        host=parsed.hostname,
        port=port,
        room=room,
        scheme=parsed.scheme,
        raw=raw_target,
    )


def _parse_host_port(raw_target: str) -> JoinTarget:
    parsed = urlsplit(f"//{raw_target}")
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("expected HOST:PORT")
    if parsed.path not in {"", "/"}:
        raise ValueError("path is only supported for URLs (http/https)")

    return JoinTarget(
        host=parsed.hostname,
        port=parsed.port,
        raw=raw_target,
    )


def _extract_room(path: str) -> str | None:
    segments = [segment for segment in path.split("/") if len(segment) > 0]
    if len(segments) == 0:
        return None
    if len(segments) >= 2 and segments[0].lower() == "join":
        return segments[1]
    return segments[-1]
