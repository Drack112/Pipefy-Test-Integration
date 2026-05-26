from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dtos import WebhookPayloadDTO
from app.integrations import PipefyService
from app.repositories import ClientRepository, WebhookEventRepository
from app.services import WebhookService
from app.shared import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks")


class CardUpdatedPayload(BaseModel):
    event_id: str
    card_id: str
    client_email: str
    timestamp: str


@router.post("/pipefy/card-updated")
def card_updated(payload: CardUpdatedPayload, db: Session = Depends(get_db)):
    service = WebhookService(
        client_repo=ClientRepository(db),
        event_repo=WebhookEventRepository(db),
        pipefy=PipefyService(),
    )
    try:
        result = service.process_card_updated(
            WebhookPayloadDTO(
                event_id=payload.event_id,
                card_id=payload.card_id,
                client_email=payload.client_email,
                timestamp=payload.timestamp,
            )
        )
    except ValueError as exc:
        logger.warning("card_updated rejected: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("card_updated unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="internal server error")
    return result
