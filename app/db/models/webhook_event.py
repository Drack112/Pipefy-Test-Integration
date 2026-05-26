from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from app.db.session import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id = Column(String, primary_key=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
