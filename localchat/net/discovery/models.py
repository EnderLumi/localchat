from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DiscoveredServer:
    server_id: UUID
    server_name: str
    host: str
    port: int
    requires_password: bool = False
