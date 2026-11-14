from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from alfred_flights.ticket_search.domain import Journey, SearchQuery, Segment, TicketOffer
from alfred_flights.ticket_search.locations import location_data


@dataclass(frozen=True, slots=True)
class Variant:
    slug: str
    departure_hour: int
    price_factor: str
    duration_delta: int
    checked_baggage_kg: int
    connection: bool
    airline: str


VARIANTS = (
    Variant("light", 8, "1.00", 0, 0, False, "SkyWays"),
    Variant("flex", 11, "1.24", 20, 23, False, "Demo Air"),
    Variant("early", 6, "1.10", -10, 20, False, "Aurora Demo"),
    Variant("late", 23, "0.96", 35, 0, False, "Night Jet"),
    Variant("comfort", 9, "1.42", 5, 32, False, "Comfort Wings"),
    Variant("direct-plus", 14, "1.17", 15, 23, False, "City Air"),
    Variant("connection", 6, "0.88", 240, 20, True, "Connect Air"),
    Variant("connection-value", 7, "0.82", 300, 0, True, "Budget Connect"),
    Variant("connection-bag", 10, "1.02", 210, 23, True, "BagFly"),
    Variant("evening", 20, "1.07", 25, 20, False, "Evening Air"),
    Variant("business-lite", 12, "1.60", 0, 32, False, "Prime Demo"),
    Variant("weekend-special", 16, "0.91", 40, 15, False, "Weekend Wings"),
    Variant("sunrise", 5, "0.93", 15, 20, False, "Sunrise Air"),
    Variant("morning-value", 7, "0.86", 55, 0, False, "Value Jet"),
    Variant("midday", 10, "1.05", 10, 15, False, "Atlas Wings"),
    Variant("afternoon", 13, "1.12", 5, 23, False, "Nova Air"),
    Variant("late-afternoon", 15, "0.98", 30, 20, False, "Cloud Jet"),
    Variant("early-evening", 17, "1.08", 20, 23, False, "Vista Air"),
    Variant("evening-value", 18, "0.89", 65, 0, True, "Transit Plus"),
    Variant("night-bag", 22, "1.14", 25, 23, False, "Moon Air"),
)


class DemoTicketProvider:
    def search(self, query: SearchQuery) -> list[TicketOffer]:
        distance_km = _distance_km(query.origin, query.destination)
        base_price = max(Decimal("60"), Decimal(str(round(distance_km * 0.08, 2))))
        direct_minutes = max(60, round(distance_km / 800 * 60 + 45))
        round_trip_factor = Decimal("1.85") if query.return_date else Decimal("1")
        purchase_url = _aviasales_search_url(query)
        return [
            self._offer(
                query,
                variant,
                base_price * Decimal(variant.price_factor) * round_trip_factor,
                max(60, direct_minutes + variant.duration_delta),
                purchase_url,
                index,
            )
            for index, variant in enumerate(VARIANTS, start=1)
        ]

    def _offer(
        self,
        query: SearchQuery,
        variant: Variant,
        price: Decimal,
        duration_minutes: int,
        purchase_url: str,
        index: int,
    ) -> TicketOffer:
        outbound, transit = _build_journey(
            query.origin,
            query.destination,
            query.departure_date,
            variant,
            duration_minutes,
            f"O{index}",
        )
        inbound = None
        inbound_transit: tuple[str, ...] = ()
        if query.return_date is not None:
            inbound, inbound_transit = _build_journey(
                query.destination,
                query.origin,
                query.return_date,
                variant,
                duration_minutes + 10,
                f"I{index}",
            )
        journeys = [outbound] + ([inbound] if inbound is not None else [])
        route_key = f"{query.origin}-{query.destination}-{query.departure_date.isoformat()}"
        return TicketOffer(
            id=f"demo-{route_key}-{variant.slug}",
            outbound=outbound,
            inbound=inbound,
            price_per_adult_eur=price.quantize(Decimal("0.01")),
            total_price_eur=Decimal("0"),
            currency="EUR",
            cabin_baggage_kg=5 if variant.checked_baggage_kg == 0 else 8,
            checked_baggage_kg=variant.checked_baggage_kg,
            transit_countries=tuple(dict.fromkeys((*transit, *inbound_transit))),
            airport_change=False,
            overnight_layover=any(_has_overnight_layover(journey) for journey in journeys),
            purchase_url=purchase_url,
        )


def _build_journey(
    origin: str,
    destination: str,
    departure_date: date,
    variant: Variant,
    duration_minutes: int,
    flight_suffix: str,
) -> tuple[Journey, tuple[str, ...]]:
    origin_data = location_data(origin)
    departure = datetime.combine(
        departure_date,
        time(hour=variant.departure_hour),
        tzinfo=ZoneInfo(str(origin_data["tz"])),
    )
    if not variant.connection:
        segment = _segment(
            origin,
            destination,
            departure,
            duration_minutes,
            f"{variant.airline[:2].upper()}{flight_suffix}",
            variant.airline,
        )
        return Journey((segment,)), ()

    hub = _connection_hub(origin, destination)
    hub_data = location_data(hub)
    first_minutes = min(180, max(90, duration_minutes // 3))
    first = _segment(
        origin,
        hub,
        departure,
        first_minutes,
        f"{variant.airline[:2].upper()}{flight_suffix}A",
        variant.airline,
    )
    second_departure = first.arrival_at + timedelta(minutes=120)
    second_minutes = max(90, duration_minutes - first_minutes - 120)
    second = _segment(
        hub,
        destination,
        second_departure,
        second_minutes,
        f"{variant.airline[:2].upper()}{flight_suffix}B",
        variant.airline,
    )
    return Journey((first, second)), (str(hub_data["country"]),)


def _segment(
    origin: str,
    destination: str,
    departure_at: datetime,
    duration_minutes: int,
    flight_number: str,
    airline: str,
) -> Segment:
    destination_data = location_data(destination)
    arrival_utc = departure_at.astimezone(UTC) + timedelta(minutes=duration_minutes)
    arrival_local = arrival_utc.astimezone(ZoneInfo(str(destination_data["tz"])))
    return Segment(
        origin=origin,
        destination=destination,
        departure_at=departure_at,
        arrival_at=arrival_local,
        flight_number=flight_number,
        airline=airline,
    )


def _connection_hub(origin: str, destination: str) -> str:
    for hub in ("IST", "FRA", "DXB", "TBS"):
        if hub not in {origin, destination}:
            return hub
    return "AMS"


def _distance_km(origin: str, destination: str) -> float:
    first = location_data(origin)
    second = location_data(destination)
    lat1, lon1 = math.radians(float(first["lat"])), math.radians(float(first["lon"]))
    lat2, lon2 = math.radians(float(second["lat"])), math.radians(float(second["lon"]))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _aviasales_search_url(query: SearchQuery) -> str:
    params = f"{query.origin}{query.departure_date:%d%m}{query.destination}"
    if query.return_date is not None:
        params += f"{query.return_date:%d%m}"
    params += str(query.adults)
    return f"https://www.aviasales.com/search/{params}"


def _has_overnight_layover(journey: Journey) -> bool:
    return any(
        previous.arrival_at.date() != current.departure_at.date()
        for previous, current in zip(journey.segments, journey.segments[1:])
    )
