from pydantic import BaseModel


class ClientCreateRequest(BaseModel):
    raisonSociale: str
    secteurActivite: str
    formeJuridique: str = ""
    rccm: str
    compteContribuable: str = ""
    regimeFiscal: str = ""
    adresse: str = ""
    exerciceComptable: str = ""
    ville: str
    contactPrincipal: str = ""
    email: str = ""
    telephone: str = ""


class ClientUpdateRequest(ClientCreateRequest):
    pass
