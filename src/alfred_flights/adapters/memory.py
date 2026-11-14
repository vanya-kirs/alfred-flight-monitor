from __future__ import annotations

from uuid import UUID


from alfred_flights.domain import Flight, Notification, ProviderObservation


class InMemoryFlightRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Flight] = {}

    def save(self, flight: Flight) -> Flight:
        self._items[flight.id] = flight
        return flight

    def get(self, flight_id: UUID) -> Flight:
        try:
            return self._items[flight_id]
        except KeyError:
            raise KeyError(f"flight {flight_id} was not found") from None

    def list_all(self) -> list[Flight]:
        return list(self._items.values())


class InMemoryNotificationRepository:
    def __init__(self) -> None:
        self._items: list[Notification] = []

    def save(self, notification: Notification) -> Notification:
        self._items.append(notification)
        return notification

    def list_all(self) -> list[Notification]:
        return list(self._items)


class StubFlightStatusProvider:
    def __init__(self) -> None:
        self._observations: dict[UUID, ProviderObservation] = {}

    def set_observation(self, flight_id: UUID, observation: ProviderObservation) -> None:
        self._observations[flight_id] = observation

    def observe(self, flight: Flight) -> ProviderObservation:
        try:
            return self._observations[flight.id]
        except KeyError:
            raise LookupError(f"provider has no observation for flight {flight.id}") from None
