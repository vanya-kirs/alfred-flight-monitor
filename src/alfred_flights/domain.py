from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class FlightState(StrEnum):
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    DEPARTED = "departed"
    ARRIVED = "arrived"


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    state: FlightState
    observed_at: datetime
    delay_minutes: int = 0

    def __post_init__(self) -> None:
        _require_aware(self.observed_at, "observed_at")
        if self.delay_minutes < 0:
            raise ValueError("delay_minutes must be non-negative")


@dataclass(frozen=True, slots=True)
class Flight:
    id: UUID
    flight_number: str
    departure_at: datetime
    origin: str | None = None
    destination: str | None = None
    state: FlightState = FlightState.SCHEDULED
    delay_minutes: int = 0
    last_observed_at: datetime | None = None

    @classmethod
    def register(
        cls,
        flight_number: str,
        departure_at: datetime,
        origin: str | None = None,
        destination: str | None = None,
    ) -> "Flight":
        _require_aware(departure_at, "departure_at")
        normalized = "".join(flight_number.upper().split())
        if not normalized:
            raise ValueError("flight_number must not be empty")
        return cls(
            id=uuid4(),
            flight_number=normalized,
            departure_at=departure_at.astimezone(UTC),
            origin=origin.strip().upper() if origin else None,
            destination=destination.strip().upper() if destination else None,
        )

    def apply(self, observation: ProviderObservation) -> "Flight":
        if self.last_observed_at is not None and observation.observed_at <= self.last_observed_at:
            return self
        return replace(
            self,
            state=observation.state,
            delay_minutes=observation.delay_minutes,
            last_observed_at=observation.observed_at.astimezone(UTC),
        )


@dataclass(frozen=True, slots=True)
class Notification:
    id: UUID
    flight_id: UUID
    created_at: datetime
    message: str


@dataclass(frozen=True, slots=True)
class FlightCheckResult:
    flight: Flight
    notification: Notification | None


def new_notification(flight: Flight, now: datetime | None = None) -> Notification:
    created_at = now or datetime.now(UTC)
    if flight.state is FlightState.DELAYED:
        message = f"Flight {flight.flight_number} is delayed by {flight.delay_minutes} minutes."
    elif flight.state is FlightState.CANCELLED:
        message = f"Flight {flight.flight_number} has been cancelled."
    else:
        raise ValueError("notifications are created only for disruptions")
    return Notification(uuid4(), flight.id, created_at, message)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")

