from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from alfred_flights.adapters.memory import (
    InMemoryFlightRepository,
    InMemoryNotificationRepository,
    StubFlightStatusProvider,
)
from alfred_flights.application import FlightMonitoringService
from alfred_flights.domain import FlightState, ProviderObservation


class FlightMonitoringServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.flights = InMemoryFlightRepository()
        self.notifications = InMemoryNotificationRepository()
        self.provider = StubFlightStatusProvider()
        self.service = FlightMonitoringService(
            flights=self.flights,
            notifications=self.notifications,
            provider=self.provider,
        )
        self.departure = datetime(2026, 11, 10, 7, 30, tzinfo=UTC)

    def test_registers_a_normalized_scheduled_flight(self) -> None:
        flight = self.service.register_flight("  su 100 ", self.departure)

        self.assertEqual(flight.flight_number, "SU100")
        self.assertEqual(flight.departure_at, self.departure)
        self.assertEqual(flight.state, FlightState.SCHEDULED)
        self.assertEqual(self.flights.get(flight.id), flight)

    def test_rejects_naive_departure_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.service.register_flight("SU100", datetime(2026, 11, 10, 7, 30))

    def test_delayed_observation_updates_flight_and_creates_notification(self) -> None:
        flight = self.service.register_flight("SU100", self.departure)
        observed_at = self.departure - timedelta(hours=5)
        self.provider.set_observation(
            flight.id,
            ProviderObservation(
                state=FlightState.DELAYED,
                observed_at=observed_at,
                delay_minutes=95,
            ),
        )

        result = self.service.check_flight(flight.id)

        self.assertEqual(result.flight.state, FlightState.DELAYED)
        self.assertEqual(result.flight.delay_minutes, 95)
        self.assertIsNotNone(result.notification)
        self.assertIn("95", result.notification.message)
        self.assertEqual(len(self.notifications.list_all()), 1)

    def test_stale_observation_does_not_roll_flight_back(self) -> None:
        flight = self.service.register_flight("SU100", self.departure)
        recent = self.departure - timedelta(hours=4)
        stale = recent - timedelta(minutes=10)
        self.provider.set_observation(
            flight.id,
            ProviderObservation(FlightState.DELAYED, recent, delay_minutes=40),
        )
        self.service.check_flight(flight.id)
        self.provider.set_observation(
            flight.id,
            ProviderObservation(FlightState.SCHEDULED, stale),
        )

        result = self.service.check_flight(flight.id)

        self.assertEqual(result.flight.state, FlightState.DELAYED)
        self.assertEqual(result.flight.delay_minutes, 40)
        self.assertIsNone(result.notification)

    def test_identical_disruption_does_not_duplicate_notification(self) -> None:
        flight = self.service.register_flight("SU100", self.departure)
        observation = ProviderObservation(
            FlightState.CANCELLED,
            self.departure - timedelta(hours=3),
        )
        self.provider.set_observation(flight.id, observation)

        first = self.service.check_flight(flight.id)
        second = self.service.check_flight(flight.id)

        self.assertIsNotNone(first.notification)
        self.assertIsNone(second.notification)
        self.assertEqual(len(self.notifications.list_all()), 1)


if __name__ == "__main__":
    unittest.main()
