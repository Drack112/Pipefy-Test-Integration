from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.client import ClientModel
from app.dtos import ClientDTO
from app.shared import get_logger

logger = get_logger(__name__)


class ClientRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        name: str,
        email: str,
        request_type: str,
        patrimony_value: float,
        pipefy_card_id: Optional[str] = None,
    ) -> ClientDTO:
        model = ClientModel(
            name=name,
            email=email,
            request_type=request_type,
            patrimony_value=patrimony_value,
            status="Aguardando Análise",
            pipefy_card_id=pipefy_card_id,
        )
        self._db.add(model)
        try:
            self._db.commit()
            self._db.refresh(model)
        except IntegrityError:
            self._db.rollback()
            logger.warning("duplicate email rejected email=%s", email)
            raise ValueError(f"email already registered: {email}")
        return self._to_dto(model)

    def get_by_email(self, email: str) -> Optional[ClientDTO]:
        model = self._db.query(ClientModel).filter(ClientModel.email == email).first()
        return self._to_dto(model) if model else None

    def update_pipefy_card_id(self, email: str, pipefy_card_id: str) -> ClientDTO:
        model = self._db.query(ClientModel).filter(ClientModel.email == email).first()
        if not model:
            raise ValueError(f"client not found: {email}")
        model.pipefy_card_id = pipefy_card_id
        self._db.commit()
        self._db.refresh(model)
        return self._to_dto(model)

    def update_status_and_priority(
        self, email: str, status: str, priority: str
    ) -> ClientDTO:
        model = self._db.query(ClientModel).filter(ClientModel.email == email).first()
        if not model:
            raise ValueError(f"client not found: {email}")
        model.status = status
        model.priority = priority
        self._db.commit()
        self._db.refresh(model)
        return self._to_dto(model)

    def _to_dto(self, model: ClientModel) -> ClientDTO:
        return ClientDTO(
            id=model.id,
            name=model.name,
            email=model.email,
            request_type=model.request_type,
            patrimony_value=model.patrimony_value,
            status=model.status,
            priority=model.priority,
            pipefy_card_id=model.pipefy_card_id,
        )
