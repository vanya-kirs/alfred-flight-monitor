from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from alfred_flights.travel.domain import ItemState, ItemType, TripRole
from alfred_flights.travel.service import AccessDenied, NotFound, TravelService


@dataclass(frozen=True, slots=True)
class InventoryOffer:
    id: str
    kind: ItemType
    title: str
    start_at: datetime
    end_at: datetime
    timezone: str
    price_eur: float
    advantages: tuple[str, ...]
    disadvantages: tuple[str, ...]
    tags: tuple[str, ...] = ()
    checkout_url: str = ""


@dataclass(frozen=True, slots=True)
class Booking:
    id: UUID
    trip_id: UUID
    offer: InventoryOffer
    status: str
    payment_token: str | None
    itinerary_item_id: UUID | None = None


class InventoryService:
    def __init__(self, travel: TravelService) -> None:
        self.travel = travel
        self.offers: dict[str, InventoryOffer] = {}
        self.bookings: dict[UUID, Booking] = {}

    def search(
        self, kind: ItemType, destination: str, start_at: datetime, end_at: datetime, timezone: str
    ) -> list[InventoryOffer]:
        if kind not in {ItemType.HOTEL, ItemType.TRANSFER, ItemType.ACTIVITY}:
            raise ValueError("inventory kind must be hotel, transfer or activity")
        if start_at.tzinfo is None or end_at.tzinfo is None or end_at <= start_at:
            raise ValueError("valid timezone-aware interval is required")
        names = {
            ItemType.HOTEL: (
                "Central Hotel", "Quiet Stay", "Airport Rooms", "City Garden", "Riverside Hotel",
                "Old Town Rooms", "Park Residence", "Metro Hotel", "Family Suites", "Boutique House",
                "Panorama Hotel", "Budget Inn",
            ),
            ItemType.TRANSFER: ("Private transfer", "Airport Express", "City shuttle"),
            ItemType.ACTIVITY: ("Historic walk", "Local food tour", "Modern art museum"),
        }[kind]
        tags = {
            ItemType.HOTEL: ("comfort", "quiet"),
            ItemType.TRANSFER: ("fast", "family"),
            ItemType.ACTIVITY: ("history", "food", "art"),
        }[kind]
        result: list[InventoryOffer] = []
        for index, name in enumerate(names):
            offer_id = f"{kind.value}-{destination.lower().replace(' ', '-')}-{index + 1}"
            offer = InventoryOffer(
                offer_id, kind, f"{name} · {destination}", start_at, end_at, timezone,
                round(35 + index * 27.5, 2),
                ("Вписывается в расписание", "Бесплатная отмена" if index == 0 else "Мгновенное подтверждение"),
                (() if index == 0 else ("Цена выше минимальной",)),
                (tags[index % len(tags)],),
                f"https://www.booking.com/searchresults.html?ss={quote(f'{name} {destination}')}",
            )
            self.offers[offer.id] = offer
            result.append(offer)
        return result

    def create_booking(
        self, actor_id: UUID, trip_id: UUID, offer_id: str, payment_token: str, payment_data: dict[str, Any] | None = None
    ) -> Booking:
        self.travel._require_role(actor_id, trip_id, {TripRole.OWNER, TripRole.EDITOR})
        forbidden = {"pan", "cvv", "card_number", "passport", "passport_number"}
        if forbidden & set((payment_data or {}).keys()):
            raise ValueError("raw payment or passport fields are forbidden")
        if not payment_token.startswith("tok_"):
            raise ValueError("opaque payment token is required")
        try:
            offer = self.offers[offer_id]
        except KeyError:
            raise NotFound("inventory offer was not found") from None
        booking = Booking(uuid4(), trip_id, offer, "pending", payment_token)
        self.bookings[booking.id] = booking
        return booking

    def confirm(self, actor_id: UUID, booking_id: UUID, expected_version: int) -> Booking:
        try:
            booking = self.bookings[booking_id]
        except KeyError:
            raise NotFound("booking was not found") from None
        self.travel._require_role(actor_id, booking.trip_id, {TripRole.OWNER, TripRole.EDITOR})
        if booking.status == "confirmed":
            return booking
        offer = booking.offer
        item = self.travel.add_itinerary_item(
            actor_id, booking.trip_id, expected_version=expected_version, item_type=offer.kind,
            title=offer.title, start_at=offer.start_at, end_at=offer.end_at, timezone=offer.timezone,
            provider_reference=offer.id, metadata={"price_eur": offer.price_eur, "booking_id": str(booking.id)},
            state=ItemState.CONFIRMED,
        )
        updated = replace(booking, status="confirmed", itinerary_item_id=item.id, payment_token=None)
        self.bookings[booking.id] = updated
        return updated


class PersonalizationService:
    def __init__(self) -> None:
        self.preferences: dict[UUID, dict[str, float]] = {}

    def set_preferences(self, user_id: UUID, interests: dict[str, float]) -> dict[str, float]:
        cleaned = {str(key).lower(): max(-1.0, min(1.0, float(value))) for key, value in interests.items()}
        self.preferences[user_id] = cleaned
        return cleaned

    def feedback(self, user_id: UUID, tag: str, liked: bool) -> dict[str, float]:
        values = self.preferences.setdefault(user_id, {})
        values[tag.lower()] = max(-1.0, min(1.0, values.get(tag.lower(), 0) + (0.2 if liked else -0.2)))
        return dict(values)

    def reset(self, user_id: UUID) -> None:
        self.preferences.pop(user_id, None)

    def rank(self, user_id: UUID, offers: list[InventoryOffer]) -> list[dict[str, Any]]:
        prefs = self.preferences.get(user_id, {})
        ranked = []
        for offer in offers:
            matched = [tag for tag in offer.tags if prefs.get(tag, 0) > 0]
            score = round(50 + sum(prefs.get(tag, 0) * 40 for tag in offer.tags) - offer.price_eur / 20, 1)
            ranked.append({"offer": offer, "score": score, "reason": f"Интересы: {', '.join(matched)}" if matched else "Базовый рейтинг"})
        return sorted(ranked, key=lambda item: (-item["score"], item["offer"].id))


@dataclass(frozen=True, slots=True)
class SensitiveReference:
    id: UUID
    trip_id: UUID
    user_id: UUID
    vault_token: str
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SensitiveReferenceVault:
    def __init__(self, travel: TravelService) -> None:
        self.travel = travel
        self.references: dict[UUID, SensitiveReference] = {}
        self.audit: list[dict[str, Any]] = []

    def store(
        self, user_id: UUID, trip_id: UUID, vault_token: str, *, abandoned: bool = False,
        raw_data: dict[str, Any] | None = None, now: datetime | None = None,
    ) -> SensitiveReference:
        self.travel.get_trip(user_id, trip_id)
        if raw_data:
            raise ValueError("raw passport data must be sent directly to the external vault")
        if not vault_token.startswith("vault_"):
            raise ValueError("opaque vault token is required")
        current = now or datetime.now(UTC)
        trip = self.travel._trip(trip_id)
        trip_expiry = datetime.combine(trip.end_date, datetime.max.time(), tzinfo=UTC) + timedelta(hours=24)
        expires = current + timedelta(minutes=30) if abandoned else trip_expiry
        reference = SensitiveReference(uuid4(), trip_id, user_id, vault_token, expires, current)
        self.references[reference.id] = reference
        self.audit.append({"action": "reference.created", "reference_id": str(reference.id)})
        return reference

    def purge(self, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        expired = [key for key, value in self.references.items() if value.expires_at <= current]
        for key in expired:
            del self.references[key]
            self.audit.append({"action": "reference.deleted", "reference_id": str(key)})
        return len(expired)


def offer_dict(item: InventoryOffer) -> dict[str, Any]:
    return {
        "id": item.id, "kind": item.kind.value, "title": item.title,
        "start_at": item.start_at.isoformat(), "end_at": item.end_at.isoformat(), "timezone": item.timezone,
        "price_eur": item.price_eur, "advantages": list(item.advantages),
        "disadvantages": list(item.disadvantages), "tags": list(item.tags), "checkout_url": item.checkout_url,
    }


def booking_dict(item: Booking) -> dict[str, Any]:
    return {"id": str(item.id), "trip_id": str(item.trip_id), "offer": offer_dict(item.offer), "status": item.status,
            "itinerary_item_id": str(item.itinerary_item_id) if item.itinerary_item_id else None}
