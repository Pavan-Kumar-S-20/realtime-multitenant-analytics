import csv
import codecs
from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.db.session import get_db
from app.models.schemas import EventCreate, User, Event, APIKeyResponse, APIKey, APIKeyCreate
from app.api.deps import get_current_user, require_roles, verify_api_key_and_get_org, apply_rate_limit, generate_secure_api_key
from app.worker.celery_app import process_events_task

router = APIRouter()

# --- Ingestion Subsystem Endpoints ---

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(apply_rate_limit)])
async def ingest_json_events(
    payload: List[EventCreate], 
    org_id: int = Depends(verify_api_key_and_get_org)
):
    """Secure machine-to-machine batch JSON pipeline payload processor ingestion link"""
    normalized_batch = [
        {
            "event_name": event.event_name,
            "properties": event.properties,
            "org_id": org_id,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None
        } for event in payload
    ]
    process_events_task.delay(normalized_batch)
    return {"status": "accepted", "queued_records": len(payload)}

@router.post("/ingest/csv", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(apply_rate_limit)])
async def ingest_csv_file(
    file: UploadFile = File(...), 
    org_id: int = Depends(verify_api_key_and_get_org)
):
    """Parses text/csv stream buffers asynchronously and safely normalizes properties matrix values"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Unsupported media reference format. CSV required.")
        
    normalized_batch = []
    csv_reader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
    
    for row in csv_reader:
        if 'event_name' not in row:
            continue
        event_name = row.pop('event_name')
        normalized_batch.append({
            "event_name": event_name,
            "properties": row, # Maps all other columns into generic structural details dictionary
            "org_id": org_id,
            "timestamp": row.get('timestamp')
        })
        
    if not normalized_batch:
        raise HTTPException(status_code=400, detail="Zero decipherable records parsed from spreadsheet payload structure.")
        
    process_events_task.delay(normalized_batch)
    return {"status": "accepted", "queued_records": len(normalized_batch)}

# --- Management Operations Subsystem Endpoints ---

@router.get("/metrics")
async def get_metrics(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.org_id == current_user.org_id).order_by(Event.timestamp.desc()))
    records = result.scalars().all()
    return {
        "tenant_id": current_user.org_id,
        "metrics_count": len(records),
        "timeline_series": [
            {"id": r.id, "name": r.event_name, "properties": r.properties, "time": r.timestamp.isoformat()} for r in records
        ]
    }

@router.post("/keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_token_access_pair(
    payload: APIKeyCreate,
    current_user: User = Depends(require_roles(["Owner", "Admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Instantiates a new masked secure credentials pair mapping to the user's tenant sandbox boundary"""
    raw_key, prefix, hashed_key = generate_secure_api_key()
    new_key = APIKey(hashed_key=hashed_key, prefix=prefix, org_id=current_user.org_id, name=payload.name, is_active=True)
    
    db.add(new_key)
    await db.commit()
    
    # Return response model containing plain text key ONLY ONCE upon creation hook cycle execution
    response_data = APIKeyResponse.from_attributes(new_key)
    setattr(response_data, "prefix", raw_key) # Mask swap presentation return
    return response_data