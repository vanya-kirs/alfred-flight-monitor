from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from alfred_flights.ticket_search.domain import (
    Journey,
    SearchQuery,
    Segment,
    SortMode,
    TicketOffer,
)
from alfred_flights.ticket_search.service import TicketSearchService, sort_offers
from alfred_flights.ticket_search.locations import resolve_location, suggest_locations


def segment(
    origin: str,
    destination: str,
    departure: datetime,
    duration_minutes: int,
    flight_number: str,
) -> Segment:
    return Segment(
        origin=origin,
        destination=destination,
        departure_at=departure,
        arrival_at=departure + timedelta(minutes=duration_minutes),
        flight_number=flight_number,
        airline="Demo Air",
    )


def offer(
    offer_id: str,
    price: str,
    duration_minutes: int,
    *,
    checked_baggage_kg: int = 0,
    transit_countries: tuple[str, ...] = (),
    connection_minutes: int | None = None,
) -> TicketOffer:
    departure = datetime(2026, 12, 10, 8, 0, tzinfo=UTC)
    if connection_minutes is None:
        segments = (segment("MOW", "IST", departure, duration_minutes, f"{offer_id}1"),)
    else:
        first = segment("MOW", "TBS", departure, 150, f"{offer_id}1")
        second_departure = first.arrival_at + timedelta(minutes=connection_minutes)
        second = segment("TBS", "IST", second_departure, duration_minutes - 150 - connection_minutes, f"{offer_id}2")
        segments = (first, second)
    return TicketOffer(
        id=offer_id,
        outbound=Journey(segments=segments),
        inbound=None,
        price_per_adult_eur=Decimal(price),
        total_price_eur=Decimal("0"),
        currency="EUR",
        cabin_baggage_kg=8,
        checked_baggage_kg=checked_baggage_kg,
        transit_countries=transit_countries,
    )


class StaticProvider:
    def __init__(self, offers: list[TicketOffer]) -> None:
        self.offers = offers

    def search(self, query: SearchQuery) -> list[TicketOffer]:
        return list(self.offers)


def query(**changes: object) -> SearchQuery:
    values: dict[str, object] = {
        "origin": "Москва",
        "destination": "istanbul",
        "departure_date": date(2026, 12, 10),
        "return_date": None,
        "adults": 2,
        "checked_baggage_required": True,
        "strict_baggage": False,
        "visa_free_countries": ("GE",),
        "sort_by": SortMode.RECOMMENDED,
    }
    values.update(changes)
    return SearchQuery(**values)


def test_search_normalizes_airports_and_multiplies_price_by_passengers() -> None:
    service = TicketSearchService(StaticProvider([offer("direct", "120", 240, checked_baggage_kg=23)]))

    result = service.search(query())

    assert result.query.origin == "MOW"
    assert result.query.destination == "IST"
    assert result.offers[0].total_price_eur == Decimal("240.00")
    assert "Багаж включён" in result.offers[0].advantages
    assert "Прямой рейс" in result.offers[0].advantages


def test_location_suggestions_match_partial_city_and_iata_code() -> None:
    russian = suggest_locations("мос", limit=5)
    by_code = suggest_locations("svo", limit=5)

    assert russian[0]["code"] == "MOW"
    assert russian[0]["city"] == "Москва"
    assert any(item["code"] == "SVO" for item in by_code)
    assert all({"code", "city", "airport", "label"} <= item.keys() for item in russian + by_code)
    assert suggest_locations("питер", limit=3)[0]["code"] == "LED"
    assert suggest_locations("сочи", limit=3)[0]["code"] == "AER"
    assert resolve_location("Санкт Питербург") == "LED"
    assert resolve_location("Санкт Петербург") == "LED"
    assert resolve_location("Сочи") == "AER"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"origin": "XXX"}, "unknown origin"),
        ({"destination": "MOW"}, "origin and destination"),
        ({"adults": 0}, "between 1 and 9"),
        ({"return_date": date(2026, 12, 9)}, "return date"),
        ({"visa_free_countries": ("ЖЖ",)}, "country codes"),
    ],
)
def test_search_rejects_invalid_queries(changes: dict[str, object], message: str) -> None:
    service = TicketSearchService(StaticProvider([]))

    with pytest.raises(ValueError, match=message):
        service.search(query(**changes))


def test_search_excludes_connections_shorter_than_ninety_minutes() -> None:
    short = offer("short", "90", 360, connection_minutes=60, transit_countries=("GE",))
    safe = offer("safe", "100", 390, connection_minutes=120, transit_countries=("GE",))
    service = TicketSearchService(StaticProvider([short, safe]))

    result = service.search(query())

    assert [item.id for item in result.offers] == ["safe"]


def test_baggage_and_unknown_visa_risk_are_explained_and_penalized() -> None:
    suitable = offer("suitable", "150", 300, checked_baggage_kg=23, transit_countries=("GE",))
    risky = offer("risky", "130", 300, transit_countries=("TR",))
    service = TicketSearchService(StaticProvider([risky, suitable]))

    result = service.search(query())

    by_id = {item.id: item for item in result.offers}
    assert "Багаж не включён" in by_id["risky"].disadvantages
    assert "Требования транзитной визы не подтверждены: TR" in by_id["risky"].disadvantages
    assert by_id["suitable"].recommendation_score > by_id["risky"].recommendation_score


def test_strict_baggage_filter_removes_offers_without_checked_baggage() -> None:
    service = TicketSearchService(
        StaticProvider([
            offer("light", "80", 240),
            offer("bag", "120", 260, checked_baggage_kg=23),
        ])
    )

    result = service.search(query(strict_baggage=True))

    assert [item.id for item in result.offers] == ["bag"]


def test_round_trip_offer_keeps_inbound_journey_and_total_price() -> None:
    outbound = offer("round", "210", 240, checked_baggage_kg=23)
    inbound_departure = datetime(2026, 12, 20, 9, 0, tzinfo=UTC)
    round_trip = replace(
        outbound,
        inbound=Journey((segment("IST", "MOW", inbound_departure, 250, "DA200"),)),
    )
    service = TicketSearchService(StaticProvider([round_trip]))

    result = service.search(query(return_date=date(2026, 12, 20)))

    assert result.offers[0].inbound is not None
    assert result.offers[0].total_price_eur == Decimal("420.00")


def test_sort_modes_use_documented_primary_fields_and_stable_ties() -> None:
    cheap = offer("a-cheap", "80", 400)
    fast = offer("b-fast", "120", 220)
    direct = offer("c-direct", "110", 300)
    assessed = TicketSearchService(StaticProvider([fast, direct, cheap])).search(
        query(checked_baggage_required=False)
    ).offers

    assert [item.id for item in sort_offers(assessed, SortMode.CHEAPEST)] == ["a-cheap", "c-direct", "b-fast"]
    assert [item.id for item in sort_offers(assessed, SortMode.FASTEST)] == ["b-fast", "c-direct", "a-cheap"]
    expected_by_score = [item.id for item in sorted(assessed, key=lambda item: (-item.recommendation_score, item.id))]
    assert [item.id for item in sort_offers(assessed, SortMode.FEWEST_STOPS)] == expected_by_score
    assert [item.id for item in sort_offers(assessed, SortMode.RECOMMENDED)] == [item.id for item in assessed]


def test_search_rejects_provider_offers_with_non_positive_price() -> None:
    broken = offer("broken", "0", 240)
    service = TicketSearchService(StaticProvider([broken]))

    with pytest.raises(ValueError, match="positive price"):
        service.search(query())
