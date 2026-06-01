from fastapi import FastAPI

from app.routers import campaigns, health, tracks, users, recommendations

app = FastAPI(title="Oasis Lite API")

app.include_router(health.router)
app.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])

@app.get("/")
def root():
    return {"message": "Welcome to the Oasis Lite API"}