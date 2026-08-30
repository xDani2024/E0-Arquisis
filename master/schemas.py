from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class Demand(BaseModel):
    city: str
    demand: float
    unit: str


class PackageBody(BaseModel):
    demands: list[Demand]
    validUntil: datetime
    metaContent: str
    constraints: dict


class EventCreate(BaseModel):
    idpk: UUID
    type: Literal["demand-set"]
    packageBody: PackageBody
