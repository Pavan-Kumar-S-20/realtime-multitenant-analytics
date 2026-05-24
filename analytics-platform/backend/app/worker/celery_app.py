from celery import Celery
import asyncio
from datetime import datetime

celery_app = Celery(
    "analytics_pipeline",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

def execute_async_task(coroutine):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)

@celery_app.task(name="process_events_task")
def process_events_task(payload_batch: list):
    from app.db.session import AsyncSessionLocal
    from app.models.schemas import Event

    async def save_records():
        async with AsyncSessionLocal() as session:
            for entry in payload_batch:
                # Direct string parsing safety fallback logic
                if entry.get("timestamp"):
                    parsed_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                else:
                    parsed_time = datetime.utcnow()
                    
                session.add(Event(
                    org_id=entry["org_id"],
                    event_name=entry["event_name"],
                    properties=entry["properties"],
                    timestamp=parsed_time
                ))
            await session.commit()

    execute_async_task(save_records())
    return f"Pipeline batch success. Flushed {len(payload_batch)} records to cluster."