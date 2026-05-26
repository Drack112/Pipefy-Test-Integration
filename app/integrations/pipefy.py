from typing import Optional

from app.config import settings
from app.shared.http_client import HttpClient
from app.shared.logger import get_logger

logger = get_logger(__name__)

_UPDATE_CARD_FIELD_MUTATION = """
mutation UpdateCardField($card_id: ID!, $field_id: ID!, $new_value: [UndefinedInput]) {
  updateCardField(input: {
    card_id: $card_id
    field_id: $field_id
    new_value: $new_value
  }) {
    card {
      id
    }
    success
  }
}
"""

_CREATE_CARD_MUTATION = """
mutation CreateCard($pipe_id: ID!, $fields_attributes: [FieldValueInput]!) {
  createCard(input: {
    pipe_id: $pipe_id
    fields_attributes: $fields_attributes
  }) {
    card {
      id
      title
      current_phase {
        name
      }
    }
  }
}
"""


class PipefyService:
    def __init__(self) -> None:
        self._http = HttpClient(
            base_url=settings.pipefy_api_url,
            headers={"Authorization": f"Bearer {settings.pipefy_token}"},
        )

    def create_card(
        self, name: str, email: str, patrimony_value: float
    ) -> Optional[str]:
        if not settings.pipefy_token:
            logger.warning("pipefy_token not set — skipping createCard email=%s", email)
            return None

        payload = {
            "query": _CREATE_CARD_MUTATION,
            "variables": {
                "pipe_id": settings.pipefy_pipe_id,
                "fields_attributes": [
                    {"field_id": "nome_do_cliente", "field_value": name},
                    {"field_id": "email", "field_value": email},
                    {
                        "field_id": "valor_patrim_nio",
                        "field_value": str(patrimony_value),
                    },
                ],
            },
        }

        try:
            logger.debug(
                "pipefy createCard pipe_id=%s email=%s", settings.pipefy_pipe_id, email
            )
            response = self._http.post(payload=payload)
            if response.get("errors"):
                logger.error(
                    "pipefy createCard returned errors email=%s errors=%s",
                    email,
                    response.get("errors"),
                )
                raise RuntimeError(
                    "pipefy returned errors: %s" % response.get("errors")
                )

            card_id = response["data"]["createCard"]["card"]["id"]
            logger.info("pipefy createCard ok email=%s card_id=%s", email, card_id)
            return card_id
        except Exception as exc:
            logger.error(
                "pipefy createCard failed email=%s: %s", email, exc, exc_info=True
            )
            raise

    def update_card(self, card_id: str, status: str, priority: str) -> None:
        if not settings.pipefy_token:
            logger.warning(
                "pipefy_token not set — skipping updateCard card_id=%s", card_id
            )
            return

        for field_id, value in [("status", status), ("prioridade", priority)]:
            payload = {
                "query": _UPDATE_CARD_FIELD_MUTATION,
                "variables": {
                    "card_id": card_id,
                    "field_id": field_id,
                    "new_value": [value],
                },
            }
            try:
                logger.debug(
                    "pipefy updateCardField card_id=%s field_id=%s value=%s",
                    card_id,
                    field_id,
                    value,
                )
                response = self._http.post(payload=payload)
                if response.get("errors"):
                    logger.error(
                        "pipefy updateCardField errors card_id=%s field_id=%s: %s",
                        card_id,
                        field_id,
                        response.get("errors"),
                    )
                    raise RuntimeError(
                        "pipefy returned errors: %s" % response.get("errors")
                    )
                logger.info(
                    "pipefy updateCardField ok card_id=%s field_id=%s",
                    card_id,
                    field_id,
                )
            except Exception as exc:
                logger.error(
                    "pipefy updateCardField failed card_id=%s field_id=%s: %s",
                    card_id,
                    field_id,
                    exc,
                    exc_info=True,
                )
                raise
