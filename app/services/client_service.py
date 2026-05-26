import re

from app.dtos import ClientDTO, CreateClientDTO
from app.integrations import PipefyService
from app.repositories import ClientRepository
from app.shared import get_logger

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class ClientService:
    def __init__(self, repository: ClientRepository, pipefy: PipefyService) -> None:
        self._repository = repository
        self._pipefy = pipefy

    def create(self, dto: CreateClientDTO) -> ClientDTO:
        if not dto.name.strip():
            raise ValueError("name is required")
        if not dto.request_type.strip():
            raise ValueError("request_type is required")
        if not _EMAIL_RE.match(dto.email):
            raise ValueError(f"invalid email: {dto.email}")
        if dto.patrimony_value < 0:
            raise ValueError("patrimony_value must be non-negative")

        client = self._repository.create(
            name=dto.name,
            email=dto.email,
            request_type=dto.request_type,
            patrimony_value=dto.patrimony_value,
        )

        pipefy_card_id = self._pipefy.create_card(
            name=client.name,
            email=client.email,
            patrimony_value=client.patrimony_value,
        )

        if pipefy_card_id:
            client = self._repository.update_pipefy_card_id(
                email=client.email,
                pipefy_card_id=pipefy_card_id,
            )

        logger.info(
            "client created id=%s email=%s pipefy_card_id=%s",
            client.id,
            client.email,
            client.pipefy_card_id,
        )
        return client
