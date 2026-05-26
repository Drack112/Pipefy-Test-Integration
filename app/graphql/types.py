from typing import Optional

import strawberry


@strawberry.input
class CreateClientInput:
    client_name: str
    client_email: str
    request_type: str
    patrimony_value: float


@strawberry.type
class ClientType:
    id: int
    name: str
    email: str
    request_type: str
    patrimony_value: float
    status: str
    priority: Optional[str]
