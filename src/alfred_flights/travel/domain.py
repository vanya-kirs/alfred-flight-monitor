from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class TripRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class ItemType(StrEnum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    TRANSFER = "transfer"
    ACTIVITY = "activity"
    CUSTOM = "custom"


class ItemState(StrEnum):
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    display_name: str


@dataclass(frozen=True, slots=True)
class Trip:
    id: UUID
    name: str
    destinations: tuple[str, ...]
    start_date: date
    end_date: date
    timezone: str
    owner_id: UUID
    version: int


@dataclass(frozen=True, slots=True)
class Participant:
    trip_id: UUID
    user_id: UUID
    role: TripRole


@dataclass(frozen=True, slots=True)
class Invitation:
    token: str
    trip_id: UUID
    role: TripRole
    expires_at: datetime
    accepted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ItineraryItem:
    id: UUID
    trip_id: UUID
    item_type: ItemType
    title: str
    start_at: datetime
    end_at: datetime
    timezone: str
    state: ItemState
    participant_ids: tuple[UUID, ...]
    provider_reference: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    trip_version: int = 0


@dataclass(frozen=True, slots=True)
class AuditEvent:
    trip_id: UUID
    version: int
    actor_id: UUID
    action: str
    entity_id: UUID
    occurred_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Conflict:
    code: str
    item_ids: tuple[UUID, ...]
    message: str

