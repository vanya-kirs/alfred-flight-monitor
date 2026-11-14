from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Protocol, Sequence

from alfred_flights.ticket_search.domain import SearchQuery, SearchResult, SortMode, TicketOffer
from alfred_flights.ticket_search.locations import resolve_location


class TicketProvider(Protocol):
    def search(self, query: SearchQuery) -> list[TicketOffer]: ...


class TicketSearchService:
    def __init__(self, provider: TicketProvider, minimum_connection_minutes: int = 90) -> None:
        self.provider = provider
        self.minimum_connection_minutes = minimum_connection_minutes

    def search(self, query: SearchQuery) -> SearchResult:
        normalized = _normalize_and_validate(query)
        offers = [
            replace(
                item,
                total_price_eur=(item.price_per_adult_eur * normalized.adults).quantize(Decimal("0.01")),
            )
            for item in self.provider.search(normalized)
        ]
        offers = [item for item in offers if self._connections_are_safe(item)]
        if any(item.total_price_eur <= 0 for item in offers):
            raise ValueError("provider offers must have a positive price")
        if any(item.duration_minutes <= 0 for item in offers):
            raise ValueError("provider offers must have a positive duration")
        if normalized.return_date is not None:
            offers = [item for item in offers if item.inbound is not None]
        if normalized.strict_baggage:
            offers = [item for item in offers if item.checked_baggage_kg > 0]
        assessed = _assess_offers(offers, normalized)
        return SearchResult(normalized, tuple(sort_offers(assessed, normalized.sort_by)))

    def _connections_are_safe(self, offer: TicketOffer) -> bool:
        journeys = [offer.outbound]
        if offer.inbound is not None:
            journeys.append(offer.inbound)
        return all(
            connection >= self.minimum_connection_minutes
            for journey in journeys
            for connection in journey.connection_minutes
        )


def sort_offers(offers: Sequence[TicketOffer], mode: SortMode) -> list[TicketOffer]:
    if mode is SortMode.CHEAPEST:
        key = lambda item: (item.total_price_eur, -item.recommendation_score, item.id)
    elif mode is SortMode.FASTEST:
        key = lambda item: (item.duration_minutes, -item.recommendation_score, item.id)
    elif mode is SortMode.FEWEST_STOPS:
        key = lambda item: (item.stops, -item.recommendation_score, item.id)
    else:
        key = lambda item: (-item.recommendation_score, item.id)
    return sorted(offers, key=key)


def _normalize_and_validate(query: SearchQuery) -> SearchQuery:
    origin = resolve_location(query.origin)
    destination = resolve_location(query.destination)
    if origin is None:
        raise ValueError(f"unknown origin: {query.origin}")
    if destination is None:
        raise ValueError(f"unknown destination: {query.destination}")
    if origin == destination:
        raise ValueError("origin and destination must be different")
    if not 1 <= query.adults <= 9:
        raise ValueError("adults must be between 1 and 9")
    if query.return_date is not None and query.return_date < query.departure_date:
        raise ValueError("return date must not be before departure date")
    countries = tuple(country.strip().upper() for country in query.visa_free_countries)
    if any(len(country) != 2 or not country.isascii() or not country.isalpha() for country in countries):
        raise ValueError("country codes must use two letters")
    return replace(query, origin=origin, destination=destination, visa_free_countries=countries)


def _assess_offers(offers: list[TicketOffer], query: SearchQuery) -> list[TicketOffer]:
    if not offers:
        return []
    min_price = min(item.total_price_eur for item in offers)
    min_duration = min(item.duration_minutes for item in offers)
    assessed: list[TicketOffer] = []
    for item in offers:
        advantages: list[str] = []
        disadvantages: list[str] = []
        risky_countries = tuple(
            country for country in item.transit_countries if country not in query.visa_free_countries
        )

        if item.stops == 0:
            advantages.append("Прямой рейс")
        if item.checked_baggage_kg > 0:
            advantages.append("Багаж включён")
        elif query.checked_baggage_required:
            disadvantages.append("Багаж не включён")
        if item.total_price_eur == min_price:
            advantages.append("Лучшая цена")
        if item.duration_minutes == min_duration:
            advantages.append("Самый быстрый вариант")
        if item.transit_countries and not risky_countries:
            advantages.append("Транзит соответствует указанным визовым условиям")
        if risky_countries:
            disadvantages.append(
                "Требования транзитной визы не подтверждены: " + ", ".join(risky_countries)
            )
        if item.airport_change:
            disadvantages.append("Требуется смена аэропорта")
        if item.overnight_layover:
            disadvantages.append("Ночная пересадка")
        if item.total_price_eur > min_price * Decimal("1.35"):
            disadvantages.append("Цена заметно выше минимальной")
        if item.duration_minutes > min_duration * 1.35:
            disadvantages.append("Долгое время в пути")

        price_points = 40 * float(min_price / item.total_price_eur)
        duration_points = 25 * (min_duration / item.duration_minutes)
        route_points = max(0, 15 - item.stops * 5)
        baggage_points = 10 if not query.checked_baggage_required or item.checked_baggage_kg > 0 else 0
        visa_points = max(0, 10 - len(risky_countries) * 5)
        penalty = (10 if item.airport_change else 0) + (5 if item.overnight_layover else 0)
        score = round(max(0, price_points + duration_points + route_points + baggage_points + visa_points - penalty), 1)
        assessed.append(
            replace(
                item,
                recommendation_score=score,
                advantages=tuple(advantages),
                disadvantages=tuple(disadvantages),
            )
        )
    return assessed
