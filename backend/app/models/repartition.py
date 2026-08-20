from pydantic import BaseModel


class RepartitionUpdateRequest(BaseModel):
    risque: str
    assigneA: str | None = None
    delai: str | None = None
