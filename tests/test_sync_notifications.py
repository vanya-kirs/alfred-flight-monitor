from datetime import UTC, date, datetime

from alfred_flights.travel.domain import ItemType, TripRole
from alfred_flights.travel.notifications import NotificationOutbox
from alfred_flights.travel.service import TravelService
from alfred_flights.travel.sync import SyncService


def setup_trip() -> tuple[TravelService, object, object, object]:
    travel = TravelService()
    owner = travel.create_user("Анна")
    editor = travel.create_user("Борис")
    trip = travel.create_trip(
        owner.id,
        "Италия",
        ("ROM",),
        date(2026, 12, 10),
        date(2026, 12, 15),
        "Europe/Rome",
    )
    invite = travel.create_invitation(owner.id, trip.id, TripRole.EDITOR)
    travel.accept_invitation(editor.id, invite.token)
    return travel, owner, editor, trip


def test_offline_sync_applies_operation_once_and_returns_changes() -> None:
    travel, owner, _, trip = setup_trip()
    sync = SyncService(travel)
    operation = {
        "operation_id": "phone-1:add-hotel",
        "action": "itinerary.add",
        "expected_version": 1,
        "payload": {
            "item_type": "hotel",
            "title": "Hotel Roma",
            "start_at": "2026-12-10T14:00:00Z",
            "end_at": "2026-12-15T09:00:00Z",
            "timezone": "Europe/Rome",
        },
    }

    first = sync.synchronize(owner.id, trip.id, after_version=0, operations=[operation])
    replay = sync.synchronize(owner.id, trip.id, after_version=0, operations=[operation])

    assert first["results"][0]["status"] == "applied"
    assert replay["results"][0]["status"] == "replayed"
    assert len(travel.list_itinerary(owner.id, trip.id)) == 1
    assert [event.version for event in replay["changes"]] == [1, 2]
    assert replay["current_version"] == 2


def test_offline_sync_reports_version_conflict_without_applying() -> None:
    travel, owner, _, trip = setup_trip()
    sync = SyncService(travel)
    travel.add_itinerary_item(
        owner.id,
        trip.id,
        expected_version=1,
        item_type=ItemType.HOTEL,
        title="Existing",
        start_at=datetime(2026, 12, 10, 14, 0, tzinfo=UTC),
        end_at=datetime(2026, 12, 11, 9, 0, tzinfo=UTC),
        timezone="Europe/Rome",
    )

    result = sync.synchronize(
        owner.id,
        trip.id,
        after_version=1,
        operations=[
            {
                "operation_id": "phone-1:stale",
                "action": "itinerary.add",
                "expected_version": 1,
                "payload": {
                    "item_type": "activity",
                    "title": "Stale activity",
                    "start_at": "2026-12-12T10:00:00Z",
                    "end_at": "2026-12-12T11:00:00Z",
                    "timezone": "Europe/Rome",
                },
            }
        ],
    )

    assert result["results"][0] == {
        "operation_id": "phone-1:stale",
        "status": "conflict",
        "current_version": 2,
    }
    assert len(travel.list_itinerary(owner.id, trip.id)) == 1


def test_notification_outbox_is_idempotent_and_keeps_unread_state() -> None:
    travel, owner, editor, trip = setup_trip()
    outbox = NotificationOutbox(travel)

    first = outbox.create_for_trip(
        trip.id,
        event_key="flight:SU100:cancelled",
        kind="flight_cancelled",
        message="Рейс SU100 отменён",
    )
    second = outbox.create_for_trip(
        trip.id,
        event_key="flight:SU100:cancelled",
        kind="flight_cancelled",
        message="Рейс SU100 отменён",
    )
    delivery = outbox.record_delivery(first[0].id, owner.id, "push", "delivered")
    repeated_delivery = outbox.record_delivery(first[0].id, owner.id, "push", "delivered")
    outbox.mark_read(first[0].id, owner.id)

    assert [item.id for item in first] == [item.id for item in second]
    assert len(first) == 2
    assert outbox.inbox(owner.id, unread_only=True) == []
    assert len(outbox.inbox(editor.id, unread_only=True)) == 1
    assert delivery == repeated_delivery
