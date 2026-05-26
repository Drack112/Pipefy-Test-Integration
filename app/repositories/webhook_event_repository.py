from sqlalchemy.orm import Session

from app.db.models.webhook_event import WebhookEvent


class WebhookEventRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def exists(self, event_id: str) -> bool:
        return (
            self._db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event_id)
            .first()
            is not None
        )

    def mark_processed(self, event_id: str) -> None:
        self._db.add(WebhookEvent(event_id=event_id))
        self._db.commit()
