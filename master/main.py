from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from master.database import Base, engine, get_db
from master.models import Event
from master.schemas import EventCreate

import json


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
def health(
    database: Session = Depends(get_db),
):
    database.execute(select(1))

    return {
        "status": "healthy",
        "database": "connected",
    }

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
    event_id: int | None = Query(
        default=None,
        alias="id",
        ge=1,
    ),
    idpk: UUID | None = Query(default=None),
    event_type: str | None = Query(
        default=None,
        alias="type",
    ),
    received_at: date | None = Query(
        default=None,
        alias="receivedAt",
    ),
    city: str | None = Query(default=None),
    demand: float | None = Query(default=None),
    unit: str | None = Query(default=None),
    valid_until: date | None = Query(
        default=None,
        alias="validUntil",
    ),
    meta_content: str | None = Query(
        default=None,
        alias="metaContent",
    ),
    constraints: str | None = Query(default=None),
    database: Session = Depends(get_db),
):
    filters = []

    if event_id is not None:
        filters.append(Event.id == event_id)

    if idpk is not None:
        filters.append(Event.idpk == idpk)

    if event_type is not None:
        filters.append(Event.type == event_type)

    if received_at is not None:
        start_of_day = datetime.combine(
            received_at,
            time.min,
            tzinfo=timezone.utc,
        )

        end_of_day = start_of_day + timedelta(days=1)

        filters.append(Event.received_at >= start_of_day)
        filters.append(Event.received_at < end_of_day)

    if city is not None:
        filters.append(
            Event.package_body["demands"].contains(
                [{"city": city}]
            )
        )

    if demand is not None:
        filters.append(
            Event.package_body["demands"].contains(
                [{"demand": demand}]
            )
        )

    if unit is not None:
        filters.append(
            Event.package_body["demands"].contains(
                [{"unit": unit}]
            )
        )

    if valid_until is not None:
        filters.append(
            Event.package_body["validUntil"]
            .as_string()
            .like(f"{valid_until.isoformat()}%")
        )

    if meta_content is not None:
        filters.append(
            Event.package_body["metaContent"].as_string()
            == meta_content
        )

    if constraints is not None:
        try:
            constraints_value = json.loads(constraints)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="constraints must be valid JSON",
            )

        if not isinstance(constraints_value, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="constraints must be a JSON object",
            )

        filters.append(
            Event.package_body["constraints"]
            == constraints_value
        )

    total = database.scalar(
        select(func.count(Event.id)).where(*filters)
    )

    offset = (page - 1) * limit

    events = database.scalars(
        select(Event)
        .where(*filters)
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