from datetime import UTC, date, datetime, timedelta

import pytest

from alfred_flights.domain import Flight, FlightState, ProviderObservation
from alfred_flights.incidents.service import IncidentService
from alfred_flights.platform.service import InventoryService, PersonalizationService, SensitiveReferenceVault
from alfred_flights.ticket_search.providers.demo import DemoTicketProvider
from alfred_flights.ticket_search.service import TicketSearchService
from alfred_flights.travel.domain import ItemState, ItemType, TripRole
from alfred_flights.travel.notifications import NotificationOutbox
from alfred_flights.travel.service import AccessDenied, TravelService


def setup_platform():
    travel = TravelService()
    owner = travel.create_user("Owner")
    editor = travel.create_user("Editor")
    trip = travel.create_trip(owner.id, "Europe", ("ROM", "PAR"), date(2026, 12, 10), date(2026, 12, 20), "Europe/Rome")
    invite = travel.create_invitation(owner.id, trip.id, TripRole.EDITOR)
    travel.accept_invitation(editor.id, invite.token)
    return travel, owner, editor, trip


def test_disruption_notifies_group_and_only_owner_applies_replacement() -> None:
    travel, owner, editor, trip = setup_platform()
    outbox = NotificationOutbox(travel)
    incidents = IncidentService(travel, TicketSearchService(DemoTicketProvider()), outbox)
    flight = Flight.register("SU100", datetime(2026, 12, 10, 7, tzinfo=UTC), "MOW", "IST")
    original = travel.add_itinerary_item(
        owner.id, trip.id, expected_version=1, item_type=ItemType.FLIGHT, title="SU100",
        start_at=flight.departure_at, end_at=flight.departure_at + timedelta(hours=4), timezone="Europe/Moscow",
        metadata={"flight_id": str(flight.id), "checked_baggage_required": True},
    )
    cancelled = flight.apply(ProviderObservation(FlightState.CANCELLED, datetime(2026, 12, 9, 8, tzinfo=UTC)))
    incident = incidents.observe(cancelled)[0]
    assert len(outbox.inbox(owner.id)) == len(outbox.inbox(editor.id)) == 1
    proposal = incidents.propose(editor.id, incident.id, incident.offers[0].id)
    with pytest.raises(AccessDenied):
        incidents.resolve(editor.id, incident.id, 2)
    resolved = incidents.resolve(owner.id, proposal.id, 2)
    assert resolved.state == "resolved"
    assert travel.items[original.id].state is ItemState.SUPERSEDED


def test_booking_uses_token_only_and_adds_confirmed_item() -> None:
    travel, owner, _, trip = setup_platform()
    inventory = InventoryService(travel)
    offers = inventory.search(ItemType.HOTEL, "Rome", datetime(2026, 12, 10, 14, tzinfo=UTC), datetime(2026, 12, 12, 9, tzinfo=UTC), "Europe/Rome")
    with pytest.raises(ValueError):
        inventory.create_booking(owner.id, trip.id, offers[0].id, "tok_safe", {"card_number": "4111"})
    booking = inventory.create_booking(owner.id, trip.id, offers[0].id, "tok_safe")
    confirmed = inventory.confirm(owner.id, booking.id, 1)
    assert confirmed.payment_token is None
    assert travel.items[confirmed.itinerary_item_id].state is ItemState.CONFIRMED


def test_personalization_and_passport_reference_expiry_without_token_in_audit() -> None:
    travel, owner, _, trip = setup_platform()
    inventory = InventoryService(travel)
    personal = PersonalizationService()
    offers = inventory.search(ItemType.ACTIVITY, "Rome", datetime(2026, 12, 11, 10, tzinfo=UTC), datetime(2026, 12, 11, 12, tzinfo=UTC), "Europe/Rome")
    personal.set_preferences(owner.id, {"history": 1})
    assert personal.rank(owner.id, offers)[0]["offer"].tags == ("history",)
    vault = SensitiveReferenceVault(travel)
    now = datetime(2026, 12, 1, tzinfo=UTC)
    with pytest.raises(ValueError):
        vault.store(owner.id, trip.id, "vault_ok", raw_data={"passport_number": "secret"}, now=now)
    reference = vault.store(owner.id, trip.id, "vault_secret-token", abandoned=True, now=now)
    assert vault.purge(now + timedelta(minutes=31)) == 1
    assert reference.id not in vault.references
    assert "vault_secret-token" not in str(vault.audit)
