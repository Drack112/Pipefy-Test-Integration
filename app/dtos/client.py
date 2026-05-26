from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CreateClientDTO:
    name: str
    email: str
    request_type: str
    patrimony_value: float


@dataclass
class ClientDTO:
    id: int
    name: str
    email: str
    request_type: str
    patrimony_value: float
    status: str
    priority: Optional[str] = field(default=None)
    pipefy_card_id: Optional[str] = field(default=None)
