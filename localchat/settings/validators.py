from __future__ import annotations

import re

from localchat.config import colors


_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def available_color_names() -> set[str]:
    names: set[str] = set()
    for key, value in vars(colors).items():
        if not key.isupper():
            continue
        if not isinstance(value, str):
            continue
        names.add(key.lower())
    names.add("default")
    return names


def normalize_name_color(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) == 0:
        raise ValueError("name color must not be empty")

    if _HEX_COLOR_RE.match(value):
        # keep hex normalized for stable persistence
        return value.upper()

    lowered = value.lower()
    if lowered in available_color_names():
        return lowered

    raise ValueError("invalid color (use color name from config/colors.py or HEX like #RRGGBB)")

