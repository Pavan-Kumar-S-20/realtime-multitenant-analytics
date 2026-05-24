from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import auth, events
from app.db.session import engine, Base

app = FastAPI(
    title="Real-Time Analytics Core",
    version="1.0.0",
    description="Production-Grade Async Multi-Tenant Pipeline Architecture Engine."
)

# Startup hook to automatically generate tables in 'analytics_db' if they don't exist
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["System Access Controls"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Isolated Pipeline Streams"])

@app.get("/health", tags=["Telemetry"])
async def telemetry_heartbeat():
    return {"status": "healthy", "engine": "online"}