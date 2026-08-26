from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import db
from app.routers import auth, balances, clients, cycles, documents, employees, missions

app = FastAPI(title="Ec-perform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    # Autorise aussi l'accès depuis un autre poste du même réseau local (ex. un collègue sur
    # le même Wi-Fi ouvrant http://<ip-du-poste>:5173), sans figer une IP précise (DHCP).
    allow_origin_regex=r"http://(192\.168|10\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1]))\.\d{1,3}\.\d{1,3}:5173",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(clients.router)
app.include_router(missions.router)
app.include_router(documents.router)
app.include_router(balances.router)
app.include_router(cycles.router)


@app.get("/health")
def health():
    server_info = db.client.server_info()
    return {"status": "ok", "database": db.name, "mongo_version": server_info["version"]}
