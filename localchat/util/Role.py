from enum import Enum

class Role(str, Enum):
    HOST = "host"
    MEMBER = "member"
