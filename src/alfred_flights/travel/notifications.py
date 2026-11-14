from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from alfred_flights.travel.service import AccessDenied, NotFound, TravelService


@dataclass(frozen=True, slots=True)
class InboxNotification:
    id: UUID
    trip_id: UUID
    user_id: UUID
    event_key: str
    kind: str
    message: str
    created_at: datetime
    read_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    notification_id: UUID
    user_id: UUID
    channel: str
    status: str
    updated_at: datetime


class NotificationOutbox:
    def __init__(self, travel: TravelService) -> None:
        self.travel = travel
        self.notifications: dict[UUID, InboxNotification] = {}
        self.by_event_recipient: dict[tuple[str, UUID], UUID] = {}
        self.deliveries: dict[tuple[UUID, UUID, str], DeliveryRecord] = {}

    def create_for_trip(
        self,
        trip_id: UUID,
        *,
        event_key: str,
        kind: str,
        message: str,
    ) -> list[InboxNotification]:
        self.travel._trip(trip_id)
        recipients = [
            item.user_id for item in self.travel.participants.values() if item.trip_id == trip_id
        ]
        created: list[InboxNotification] = []
        for user_id in recipients:
            dedupe_key = (event_key, user_id)
            existing_id = self.by_event_recipient.get(dedupe_key)
            if existing_id:
                created.append(self.notifications[existing_id])
                continue
            item = InboxNotification(
                uuid4(),
                trip_id,
                user_id,
                event_key,
                kind,
                message,
                datetime.now(UTC),
            )
            self.notifications[item.id] = item
            self.by_event_recipient[dedupe_key] = item.id
            created.append(item)
        return created

    def inbox(self, user_id: UUID, *, unread_only: bool = False) -> list[InboxNotification]:
        self.travel._user(user_id)
        items = [item for item in self.notifications.values() if item.user_id == user_id]
        if unread_only:
            items = [item for item in items if item.read_at is None]
        return sorted(items, key=lambda item: (item.created_at, str(item.id)), reverse=True)

    def mark_read(self, notification_id: UUID, user_id: UUID) -> InboxNotification:
        item = self._owned(notification_id, user_id)
        updated = item if item.read_at else replace(item, read_at=datetime.now(UTC))
        self.notifications[item.id] = updated
        return updated

    def record_delivery(
        self,
        notification_id: UUID,
        user_id: UUID,
        channel: str,
        status: str,
    ) -> DeliveryRecord:
        self._owned(notification_id, user_id)
        key = (notification_id, user_id, channel)
        existing = self.deliveries.get(key)
        if existing and existing.status == status:
            return existing
        record = DeliveryRecord(notification_id, user_id, channel, status, datetime.now(UTC))
        self.deliveries[key] = record
        return record

    def _owned(self, notification_id: UUID, user_id: UUID) -> InboxNotification:
        try:
            item = self.notifications[notification_id]
        except KeyError:
            raise NotFound("notification was not found") from None
        if item.user_id != user_id:
            raise AccessDenied("notification belongs to another user")
        return item
