from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from alfred_flights.domain import Flight, FlightState
from alfred_flights.ticket_search.domain import SearchQuery, SortMode, TicketOffer
from alfred_flights.ticket_search.service import TicketSearchService
from alfred_flights.travel.domain import ItemState, ItemType, TripRole
from alfred_flights.travel.notifications import NotificationOutbox
from alfred_flights.travel.service import AccessDenied, NotFound, TravelService


@dataclass(frozen=True, slots=True)
class Incident:
    id: UUID
    trip_id: UUID
    flight_id: UUID
    event_key: str
    state: str
    affected_item_ids: tuple[UUID, ...]
    offers: tuple[TicketOffer, ...] = ()
    proposal_offer_id: str | None = None
    proposed_by: UUID | None = None
    resolved_item_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class IncidentService:
    def __init__(self, travel: TravelService, tickets: TicketSearchService, outbox: NotificationOutbox) -> None:
        self.travel = travel
        self.tickets = tickets
        self.outbox = outbox
        self.incidents: dict[UUID, Incident] = {}
        self.by_event: dict[str, UUID] = {}

    def observe(self, flight: Flight) -> list[Incident]:
        if flight.state not in {FlightState.DELAYED, FlightState.CANCELLED}:
            return []
        affected = [
            item for item in self.travel.items.values()
            if str(item.metadata.get("flight_id")) == str(flight.id)
            and item.state not in {ItemState.CANCELLED, ItemState.SUPERSEDED}
        ]
        created: list[Incident] = []
        for trip_id in {item.trip_id for item in affected}:
            event_key = f"flight:{flight.id}:{flight.state.value}:{flight.last_observed_at}"
            existing = self.by_event.get(event_key)
            if existing:
                created.append(self.incidents[existing])
                continue
            trip_items = tuple(item.id for item in affected if item.trip_id == trip_id)
            offers: tuple[TicketOffer, ...] = ()
            if flight.origin and flight.destination:
                result = self.tickets.search(SearchQuery(
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_at.date(),
                    checked_baggage_required=any(
                        bool(self.travel.items[item_id].metadata.get("checked_baggage_required"))
                        for item_id in trip_items
                    ),
                    sort_by=SortMode.RECOMMENDED,
                ))
                offers = result.offers
            incident = Incident(uuid4(), trip_id, flight.id, event_key, "open", trip_items, offers)
            self.incidents[incident.id] = incident
            self.by_event[event_key] = incident.id
            self.outbox.create_for_trip(
                trip_id,
                event_key=event_key,
                kind=f"flight_{flight.state.value}",
                message=f"Рейс {flight.flight_number}: {flight.state.value}. Подготовлены альтернативы.",
            )
            created.append(incident)
        return created

    def list_for_trip(self, actor_id: UUID, trip_id: UUID) -> list[Incident]:
        self.travel.get_trip(actor_id, trip_id)
        return [item for item in self.incidents.values() if item.trip_id == trip_id]

    def propose(self, actor_id: UUID, incident_id: UUID, offer_id: str) -> Incident:
        incident = self._incident(incident_id)
        role = self.travel.role_for(actor_id, incident.trip_id)
        if role not in {TripRole.OWNER, TripRole.EDITOR}:
            raise AccessDenied("viewer cannot propose alternatives")
        if offer_id not in {offer.id for offer in incident.offers}:
            raise NotFound("alternative offer was not found")
        updated = replace(incident, state="proposed", proposal_offer_id=offer_id, proposed_by=actor_id)
        self.incidents[incident.id] = updated
        return updated

    def resolve(self, owner_id: UUID, incident_id: UUID, expected_version: int) -> Incident:
        incident = self._incident(incident_id)
        if self.travel.role_for(owner_id, incident.trip_id) is not TripRole.OWNER:
            raise AccessDenied("only owner can apply an alternative")
        offer = next((item for item in incident.offers if item.id == incident.proposal_offer_id), None)
        if offer is None:
            raise ValueError("select an alternative before resolving")
        version = expected_version
        for item_id in incident.affected_item_ids:
            changed = self.travel.change_item_state(
                owner_id, item_id, expected_version=version, state=ItemState.SUPERSEDED
            )
            version = changed.trip_version
        journey = offer.outbound
        first, last = journey.segments[0], journey.segments[-1]
        new_item = self.travel.add_itinerary_item(
            owner_id,
            incident.trip_id,
            expected_version=version,
            item_type=ItemType.FLIGHT,
            title=f"Альтернатива {first.flight_number}",
            start_at=first.departure_at,
            end_at=last.arrival_at,
            timezone="UTC",
            provider_reference=offer.id,
            metadata={
                "baggage_kg": offer.checked_baggage_kg,
                "transit_countries": list(offer.transit_countries),
                "purchase_url": offer.purchase_url,
            },
            state=ItemState.PLANNED,
        )
        updated = replace(incident, state="resolved", resolved_item_id=new_item.id)
        self.incidents[incident.id] = updated
        self.outbox.create_for_trip(
            incident.trip_id,
            event_key=f"incident:{incident.id}:resolved",
            kind="plan_updated",
            message="Владелец применил альтернативный рейс. Общий план обновлён.",
        )
        return updated

    def _incident(self, incident_id: UUID) -> Incident:
        try:
            return self.incidents[incident_id]
        except KeyError:
            raise NotFound("incident was not found") from None


def incident_dict(item: Incident) -> dict[str, Any]:
    return {
        "id": str(item.id), "trip_id": str(item.trip_id), "flight_id": str(item.flight_id),
        "state": item.state, "affected_item_ids": [str(value) for value in item.affected_item_ids],
        "proposal_offer_id": item.proposal_offer_id, "resolved_item_id": str(item.resolved_item_id) if item.resolved_item_id else None,
        "alternatives": [
            {
                "id": offer.id, "price_eur": float(offer.total_price_eur),
                "baggage_kg": offer.checked_baggage_kg, "score": offer.recommendation_score,
                "advantages": list(offer.advantages), "disadvantages": list(offer.disadvantages),
                "purchase_url": offer.purchase_url,
            } for offer in item.offers
        ],
    }
