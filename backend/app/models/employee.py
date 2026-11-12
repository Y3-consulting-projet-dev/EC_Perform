from pydantic import BaseModel


class UpdateProfileRequest(BaseModel):
    nom: str
    prenoms: str
