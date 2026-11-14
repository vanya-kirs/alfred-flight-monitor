from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID


from alfred_flights.domain import (
    Flight,
    FlightCheckResult,
    FlightState,
    Notification,
    ProviderObservation,
    new_notification,
)


class FlightRepository(Protocol):
    def save(self, flight: Flight) -> Flight: ...
    def get(self, flight_id: UUID) -> Flight: ...
    def list_all(self) -> list[Flight]: ...


class NotificationRepository(Protocol):
    def save(self, notification: Notification) -> Notification: ...
    def list_all(self) -> list[Notification]: ...


class FlightStatusProvider(Protocol):
    def observe(self, flight: Flight) -> ProviderObservation: ...


class FlightMonitoringService:
    def __init__(
        self,
        *,
        flights: FlightRepository,
        notifications: NotificationRepository,
        provider: FlightStatusProvider,
    ) -> None:
        self.flights = flights
        self.notifications = notifications
        self.provider = provider

    def register_flight(
        self,
        flight_number: str,
        departure_at: datetime,
        origin: str | None = None,
        destination: str | None = None,
    ) -> Flight:
        return self.flights.save(Flight.register(flight_number, departure_at, origin, destination))

    def list_flights(self) -> list[Flight]:
        return self.flights.list_all()

    def get_flight(self, flight_id: UUID) -> Flight:
        return self.flights.get(flight_id)

    def list_notifications(self) -> list[Notification]:
        return self.notifications.list_all()

    def check_flight(self, flight_id: UUID) -> FlightCheckResult:
        current = self.flights.get(flight_id)
        updated = current.apply(self.provider.observe(current))
        if updated is current:
            return FlightCheckResult(current, None)

        self.flights.save(updated)
        disruption_changed = (
            updated.state in {FlightState.DELAYED, FlightState.CANCELLED}
            and (updated.state != current.state or updated.delay_minutes != current.delay_minutes)
        )
        notification = None
        if disruption_changed:
            notification = self.notifications.save(new_notification(updated))
        return FlightCheckResult(updated, notification)

