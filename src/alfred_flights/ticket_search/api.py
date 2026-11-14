from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from alfred_flights.ticket_search.domain import SearchQuery, SortMode, TicketOffer
from alfred_flights.ticket_search.service import TicketSearchService, sort_offers
from alfred_flights.ticket_search.locations import RUSSIAN_CITY_NAMES, location_data, suggest_locations


class TicketSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: date
    return_date: date
    adults: int = 1
    checked_baggage_required: bool = False
    strict_baggage: bool = False
    visa_free_countries: list[str] = Field(default_factory=list)
    sort_by: SortMode = SortMode.RECOMMENDED


class SortOffersRequest(BaseModel):
    search_id: str
    sort_by: SortMode
    offer_ids: list[str] | None = None


class SelectOfferRequest(BaseModel):
    search_id: str
    offer_id: str


class TicketSearchState:
    def __init__(self) -> None:
        self.searches: dict[str, dict[str, TicketOffer]] = {}
        self.selections: dict[str, tuple[TicketOffer, datetime]] = {}

    def store_search(self, offers: tuple[TicketOffer, ...]) -> str:
        search_id = str(uuid4())
        self.searches[search_id] = {offer.id: offer for offer in offers}
        return search_id

    def get_offers(self, search_id: str) -> dict[str, TicketOffer]:
        try:
            return self.searches[search_id]
        except KeyError:
            raise KeyError(f"unknown search: {search_id}") from None


def create_ticket_search_router(
    service: TicketSearchService,
    state: TicketSearchState,
) -> APIRouter:
    router = APIRouter()

    @router.get("/locations/suggest")
    def location_suggestions(
        q: str = Query(min_length=1, max_length=80),
        limit: int = Query(default=8, ge=1, le=20),
    ) -> list[dict[str, str]]:
        return suggest_locations(q, limit)

    @router.post("/ticket-search")
    def search_tickets(payload: TicketSearchRequest) -> dict[str, Any]:
        query = SearchQuery(
            origin=payload.origin,
            destination=payload.destination,
            departure_date=payload.departure_date,
            return_date=payload.return_date,
            adults=payload.adults,
            checked_baggage_required=payload.checked_baggage_required,
            strict_baggage=payload.strict_baggage,
            visa_free_countries=tuple(payload.visa_free_countries),
            sort_by=payload.sort_by,
        )
        try:
            result = service.search(query)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        search_id = state.store_search(result.offers)
        return search_result_to_dict(result, search_id)

    @router.post("/ticket-search/sort")
    def reorder_offers(payload: SortOffersRequest) -> list[dict[str, Any]]:
        try:
            search_offers = state.get_offers(payload.search_id)
            ids = payload.offer_ids or list(search_offers)
            offers = [search_offers[offer_id] for offer_id in ids]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return [_offer_to_dict(offer) for offer in sort_offers(offers, payload.sort_by)]

    @router.post("/trip-plan/selection", status_code=status.HTTP_201_CREATED)
    def select_offer(payload: SelectOfferRequest) -> dict[str, Any]:
        try:
            offer = state.get_offers(payload.search_id)[payload.offer_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="offer is not present in this search") from exc
        state.selections[payload.search_id] = (offer, datetime.now(UTC))
        return _plan_to_dict(state, payload.search_id)

    @router.get("/trip-plan")
    def get_trip_plan(search_id: str) -> dict[str, Any]:
        if search_id not in state.searches:
            raise HTTPException(status_code=404, detail="search was not found")
        return _plan_to_dict(state, search_id)

    return router


def search_result_to_dict(result: Any, search_id: str) -> dict[str, Any]:
    return {
        "search_id": search_id,
        "provider": "local-demo-catalog",
        "purchase_destination": "Aviasales",
        "query": _query_to_dict(result.query),
        "offers": [_offer_to_dict(offer) for offer in result.offers],
        "is_demo": result.is_demo,
    }


def _query_to_dict(query: SearchQuery) -> dict[str, Any]:
    return {
        "origin": query.origin,
        "destination": query.destination,
        "departure_date": query.departure_date.isoformat(),
        "return_date": query.return_date.isoformat() if query.return_date else None,
        "adults": query.adults,
        "checked_baggage_required": query.checked_baggage_required,
        "strict_baggage": query.strict_baggage,
        "visa_free_countries": list(query.visa_free_countries),
        "sort_by": query.sort_by.value,
    }


def _journey_to_dict(journey: Any) -> dict[str, Any]:
    first_departure_hour = journey.segments[0].departure_at.hour
    return {
        "segments": [
            _segment_to_dict(segment)
            for segment in journey.segments
        ],
        "duration_minutes": journey.duration_minutes,
        "stops": journey.stops,
        "departure_period": "night" if first_departure_hour >= 22 or first_departure_hour < 6 else "day",
    }


def _segment_to_dict(segment: Any) -> dict[str, Any]:
    origin = location_data(segment.origin)
    destination = location_data(segment.destination)
    return {
                "origin": segment.origin,
                "destination": segment.destination,
                "origin_city": RUSSIAN_CITY_NAMES.get(segment.origin, str(origin.get("city") or segment.origin)),
                "destination_city": RUSSIAN_CITY_NAMES.get(segment.destination, str(destination.get("city") or segment.destination)),
                "origin_airport": str(origin.get("name") or segment.origin),
                "destination_airport": str(destination.get("name") or segment.destination),
                "departure_at": segment.departure_at.isoformat(),
                "arrival_at": segment.arrival_at.isoformat(),
                "flight_number": segment.flight_number,
                "airline": segment.airline,
            }


def _offer_to_dict(offer: TicketOffer) -> dict[str, Any]:
    return {
        "id": offer.id,
        "outbound": _journey_to_dict(offer.outbound),
        "inbound": _journey_to_dict(offer.inbound) if offer.inbound else None,
        "price_per_adult_eur": str(offer.price_per_adult_eur),
        "total_price_eur": str(offer.total_price_eur),
        "currency": offer.currency,
        "cabin_baggage_kg": offer.cabin_baggage_kg,
        "checked_baggage_kg": offer.checked_baggage_kg,
        "transit_countries": list(offer.transit_countries),
        "airport_change": offer.airport_change,
        "overnight_layover": offer.overnight_layover,
        "duration_minutes": offer.duration_minutes,
        "stops": offer.stops,
        "recommendation_score": offer.recommendation_score,
        "advantages": list(offer.advantages),
        "disadvantages": list(offer.disadvantages),
        "purchase_url": offer.purchase_url,
    }


def _plan_to_dict(state: TicketSearchState, search_id: str) -> dict[str, Any]:
    selection = state.selections.get(search_id)
    return {
        "search_id": search_id,
        "selected_offer": _offer_to_dict(selection[0]) if selection else None,
        "selected_at": selection[1].isoformat() if selection else None,
        "booking_created": False,
    }

