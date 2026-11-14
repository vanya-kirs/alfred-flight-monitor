from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class SortMode(StrEnum):
    RECOMMENDED = "recommended"
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    FEWEST_STOPS = "fewest_stops"


@dataclass(frozen=True, slots=True)
class Segment:
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    flight_number: str
    airline: str

    def __post_init__(self) -> None:
        if self.departure_at.tzinfo is None or self.arrival_at.tzinfo is None:
            raise ValueError("segment times must be timezone-aware")
        if self.arrival_at <= self.departure_at:
            raise ValueError("segment arrival must be after departure")


@dataclass(frozen=True, slots=True)
class Journey:
    segments: tuple[Segment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("journey must contain at least one segment")

    @property
    def duration_minutes(self) -> int:
        delta = self.segments[-1].arrival_at - self.segments[0].departure_at
        return int(delta.total_seconds() // 60)

    @property
    def stops(self) -> int:
        return len(self.segments) - 1

    @property
    def connection_minutes(self) -> tuple[int, ...]:
        return tuple(
            int((current.departure_at - previous.arrival_at).total_seconds() // 60)
            for previous, current in zip(self.segments, self.segments[1:])
        )


@dataclass(frozen=True, slots=True)
class SearchQuery:
    origin: str
    destination: str
    departure_date: date
    return_date: date | None = None
    adults: int = 1
    checked_baggage_required: bool = False
    strict_baggage: bool = False
    visa_free_countries: tuple[str, ...] = ()
    sort_by: SortMode = SortMode.RECOMMENDED


@dataclass(frozen=True, slots=True)
class TicketOffer:
    id: str
    outbound: Journey
    inbound: Journey | None
    price_per_adult_eur: Decimal
    total_price_eur: Decimal
    currency: str
    cabin_baggage_kg: int
    checked_baggage_kg: int
    transit_countries: tuple[str, ...] = ()
    airport_change: bool = False
    overnight_layover: bool = False
    recommendation_score: float = 0.0
    advantages: tuple[str, ...] = ()
    disadvantages: tuple[str, ...] = ()
    purchase_url: str | None = None

    @property
    def duration_minutes(self) -> int:
        inbound_duration = self.inbound.duration_minutes if self.inbound else 0
        return self.outbound.duration_minutes + inbound_duration

    @property
    def stops(self) -> int:
        inbound_stops = self.inbound.stops if self.inbound else 0
        return self.outbound.stops + inbound_stops


@dataclass(frozen=True, slots=True)
class SearchResult:
    query: SearchQuery
    offers: tuple[TicketOffer, ...]
    is_demo: bool = True

