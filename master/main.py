from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from master.database import Base, engine, get_db
from master.models import Event
from master.schemas import EventCreate


Base.metadata.create_all(bind=engine)

app = FastAPI(title="EnergyShark API")

def serialize_event(event: Event):
    return {
        "id": event.id,
        "idpk": event.idpk,
        "type": event.type,
        "packageBody": event.package_body,
        "receivedAt": event.received_at,
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/events", status_code=status.HTTP_201_CREATED)
def receive_event(
    event: EventCreate,
    database: Session = Depends(get_db),
):
    database_event = Event(
        idpk=event.idpk,
        type=event.type,
        package_body=event.packageBody.model_dump(mode="json"),
    )

    database.add(database_event)

    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event with this idpk already exists",
        )

    database.refresh(database_event)

    return serialize_event(database_event)

@app.get("/history")
def list_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    database: Session = Depends(get_db),
):
    total = database.scalar(
        select(func.count()).select_from(Event)
    )

    offset = (page - 1) * limit

    events = database.scalars(
        select(Event)
        .order_by(Event.received_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "records": [
            serialize_event(event)
            for event in events
        ],
    }

@app.get("/history/{event_id}")
def get_history_detail(
    event_id: int,
    database: Session = Depends(get_db),
):
    event = database.get(Event, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return serialize_event(event)