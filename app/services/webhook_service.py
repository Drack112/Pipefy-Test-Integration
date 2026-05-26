from app.dtos.webhook import WebhookPayloadDTO
from app.integrations import PipefyService
from app.repositories import ClientRepository, WebhookEventRepository
from app.shared import get_logger

logger = get_logger(__name__)

_THRESHOLD = 200_000


class WebhookService:
    def __init__(
        self,
        client_repo: ClientRepository,
        event_repo: WebhookEventRepository,
        pipefy: PipefyService,
    ) -> None:
        self._client_repo = client_repo
        self._event_repo = event_repo
        self._pipefy = pipefy

    def process_card_updated(self, payload: WebhookPayloadDTO) -> dict:
        if self._event_repo.exists(payload.event_id):
            logger.info("webhook duplicate ignored event_id=%s", payload.event_id)
            return {"status": "duplicate", "event_id": payload.event_id}

        client = self._client_repo.get_by_email(payload.client_email)
        if not client:
            raise ValueError(f"client not found: {payload.client_email}")

        priority = (
            "prioridade_alta"
            if client.patrimony_value >= _THRESHOLD
            else "prioridade_normal"
        )

        self._client_repo.update_status_and_priority(
            email=payload.client_email,
            status="Processado",
            priority=priority,
        )

        try:
            self._pipefy.update_card(
                card_id=payload.card_id,
                status="Processado",
                priority=priority,
            )
        except Exception as exc:
            logger.error(
                "pipefy update_card failed card_id=%s — local DB already updated: %s",
                payload.card_id,
                exc,
                exc_info=True,
            )

        self._event_repo.mark_processed(payload.event_id)

        logger.info(
            "webhook processed event_id=%s email=%s priority=%s",
            payload.event_id,
            payload.client_email,
            priority,
        )
        return {
            "status": "processed",
            "event_id": payload.event_id,
            "priority": priority,
        }
