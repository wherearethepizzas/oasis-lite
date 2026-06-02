from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.routers import campaigns, events, health, tracks, users, recommendations
from app.schemas import RootResponse

app = FastAPI(title="Oasis Lite API")

app.include_router(health.router)
app.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(events.router, tags=["events"])

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/", response_model=RootResponse)
def root():
    return {"message": "Welcome to the Oasis Lite API"}
