from graphql import GraphQLError
from strawberry.types import Info

from app.dtos import CreateClientDTO
from app.graphql.types import ClientType, CreateClientInput
from app.integrations import PipefyService
from app.repositories import ClientRepository
from app.services import ClientService
from app.shared import get_logger

logger = get_logger(__name__)


def resolve_health() -> str:
    return "ok"


def resolve_create_client(info: Info, input: CreateClientInput) -> ClientType:
    db = info.context["db"]
    service = ClientService(
        repository=ClientRepository(db),
        pipefy=PipefyService(),
    )
    try:
        dto = service.create(
            CreateClientDTO(
                name=input.client_name,
                email=input.client_email,
                request_type=input.request_type,
                patrimony_value=input.patrimony_value,
            )
        )
    except ValueError as exc:
        logger.debug("create_client rejected: %s", exc)
        raise GraphQLError(str(exc)) from None
    except Exception as exc:
        logger.error("create_client unexpected error: %s", exc, exc_info=True)
        raise

    return ClientType(
        id=dto.id,
        name=dto.name,
        email=dto.email,
        request_type=dto.request_type,
        patrimony_value=dto.patrimony_value,
        status=dto.status,
        priority=dto.priority,
    )
