from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import db
from app.routers import auth, balances, clients, cycles, documents, employees, missions

app = FastAPI(title="Ec-perform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
