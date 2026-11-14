from datetime import UTC, date, datetime, timedelta

import pytest

from alfred_flights.travel.domain import ItemType, TripRole
from alfred_flights.travel.service import AccessDenied, TravelService, VersionConflict


def build_service() -> tuple[TravelService, object, object, object]:
    service = TravelService()
    owner = service.create_user("Анна")
    editor = service.create_user("Борис")
    viewer = service.create_user("Вера")
    return service, owner, editor, viewer


def test_multi_city_trip_invitation_roles_and_timeline() -> None:
    service, owner, editor, viewer = build_service()
    trip = service.create_trip(
        owner.id,
        "Италия и Франция",
        ("ROM", "PAR"),
        date(2026, 12, 10),
        date(2026, 12, 20),
        "Europe/Rome",
    )
    editor_invite = service.create_invitation(owner.id, trip.id, TripRole.EDITOR)
    viewer_invite = service.create_invitation(owner.id, trip.id, TripRole.VIEWER)
    service.accept_invitation(editor.id, editor_invite.token)
    service.accept_invitation(viewer.id, viewer_invite.token)

    later = service.add_itinerary_item(
        editor.id,
        trip.id,
        expected_version=trip.version,
        item_type=ItemType.ACTIVITY,
        title="Лувр",
        start_at=datetime(2026, 12, 15, 14, 0, tzinfo=UTC),
        end_at=datetime(2026, 12, 15, 16, 0, tzinfo=UTC),
        timezone="Europe/Paris",
    )
    earlier = service.add_itinerary_item(
        owner.id,
        trip.id,
        expected_version=later.trip_version,
        item_type=ItemType.FLIGHT,
        title="Рейс в Рим",
        start_at=datetime(2026, 12, 10, 7, 0, tzinfo=UTC),
        end_at=datetime(2026, 12, 10, 11, 0, tzinfo=UTC),
        timezone="Europe/Rome",
    )

    assert trip.destinations == ("ROM", "PAR")
    assert [item.id for item in service.list_itinerary(viewer.id, trip.id)] == [earlier.id, later.id]
    with pytest.raises(AccessDenied):
        service.add_itinerary_item(
            viewer.id,
            trip.id,
            expected_version=earlier.trip_version,
            item_type=ItemType.CUSTOM,
            title="Нельзя добавить",
            start_at=datetime(2026, 12, 16, 10, 0, tzinfo=UTC),
            end_at=datetime(2026, 12, 16, 11, 0, tzinfo=UTC),
            timezone="Europe/Paris",
        )


def test_overlapping_items_create_conflict_and_audit_versions() -> None:
    service, owner, _, _ = build_service()
    trip = service.create_trip(
        owner.id,
        "Москва",
        ("MOW",),
        date(2026, 12, 10),
        date(2026, 12, 12),
        "Europe/Moscow",
    )
    first = service.add_itinerary_item(
        owner.id,
        trip.id,
        expected_version=trip.version,
        item_type=ItemType.TRANSFER,
        title="Трансфер",
        start_at=datetime(2026, 12, 10, 10, 0, tzinfo=UTC),
        end_at=datetime(2026, 12, 10, 11, 0, tzinfo=UTC),
        timezone="Europe/Moscow",
    )
    second = service.add_itinerary_item(
        owner.id,
        trip.id,
        expected_version=first.trip_version,
        item_type=ItemType.ACTIVITY,
        title="Экскурсия",
        start_at=datetime(2026, 12, 10, 10, 30, tzinfo=UTC),
        end_at=datetime(2026, 12, 10, 12, 0, tzinfo=UTC),
        timezone="Europe/Moscow",
    )

    conflicts = service.detect_conflicts(owner.id, trip.id)
    audit = service.audit_events(owner.id, trip.id)

    assert conflicts[0].code == "time_overlap"
    assert set(conflicts[0].item_ids) == {first.id, second.id}
    assert [event.version for event in audit] == [1, 2, 3]


def test_stale_expected_version_is_rejected_with_current_version() -> None:
    service, owner, _, _ = build_service()
    trip = service.create_trip(
        owner.id,
        "Рим",
        ("ROM",),
        date(2026, 12, 10),
        date(2026, 12, 12),
        "Europe/Rome",
    )
    service.add_itinerary_item(
        owner.id,
        trip.id,
        expected_version=trip.version,
        item_type=ItemType.HOTEL,
        title="Отель",
        start_at=datetime(2026, 12, 10, 12, 0, tzinfo=UTC),
        end_at=datetime(2026, 12, 12, 9, 0, tzinfo=UTC),
        timezone="Europe/Rome",
    )

    with pytest.raises(VersionConflict) as exc:
        service.add_itinerary_item(
            owner.id,
            trip.id,
            expected_version=trip.version,
            item_type=ItemType.ACTIVITY,
            title="Колизей",
            start_at=datetime(2026, 12, 11, 12, 0, tzinfo=UTC),
            end_at=datetime(2026, 12, 11, 14, 0, tzinfo=UTC),
            timezone="Europe/Rome",
        )

    assert exc.value.current_version == 2

