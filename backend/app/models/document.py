from pydantic import BaseModel


class DocumentStatusUpdate(BaseModel):
    statut: str
