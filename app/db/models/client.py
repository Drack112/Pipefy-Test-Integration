from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class ClientModel(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    request_type = Column(String, nullable=False)
    patrimony_value = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="Aguardando Análise")
    priority = Column(String, nullable=True)
    pipefy_card_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
