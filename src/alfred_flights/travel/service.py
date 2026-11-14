from __future__ import annotations

import secrets
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from alfred_flights.travel.domain import (
    AuditEvent,
    Conflict,
    Invitation,
    ItemState,
    ItemType,
    ItineraryItem,
    Participant,
    Trip,
    TripRole,
    User,
)


class TravelError(Exception):
    pass


class NotFound(TravelError):
    pass


class AccessDenied(TravelError):
    pass


class VersionConflict(TravelError):
    def __init__(self, current_version: int) -> None:
        super().__init__(f"expected version is stale; current version is {current_version}")
        self.current_version = current_version


class TravelService:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.trips: dict[UUID, Trip] = {}
        self.participants: dict[tuple[UUID, UUID], Participant] = {}
        self.invitations: dict[str, Invitation] = {}
        self.items: dict[UUID, ItineraryItem] = {}
        self.audit: dict[UUID, list[AuditEvent]] = {}

    def create_user(self, display_name: str) -> User:
        name = display_name.strip()
        if not name:
            raise ValueError("display_name must not be empty")
        user = User(uuid4(), name)
        self.users[user.id] = user
        return user

    def create_trip(
        self,
        actor_id: UUID,
        name: str,
        destinations: tuple[str, ...],
        start_date: date,
        end_date: date,
        timezone: str,
    ) -> Trip:
        self._user(actor_id)
        if not destinations:
            raise ValueError("trip must have at least one destination")
        if end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        ZoneInfo(timezone)
        trip = Trip(
            uuid4(),
            name.strip() or "Без названия",
            tuple(item.strip().upper() for item in destinations),
            start_date,
            end_date,
            timezone,
            actor_id,
            1,
        )
        self.trips[trip.id] = trip
        self.participants[(trip.id, actor_id)] = Participant(trip.id, actor_id, TripRole.OWNER)
        self.audit[trip.id] = [
            AuditEvent(trip.id, 1, actor_id, "trip.created", trip.id, datetime.now(UTC))
        ]
        return trip

    def list_trips(self, actor_id: UUID) -> list[Trip]:
        self._user(actor_id)
        return [trip for trip in self.trips.values() if (trip.id, actor_id) in self.participants]

    def get_trip(self, actor_id: UUID, trip_id: UUID) -> Trip:
        trip = self._trip(trip_id)
        self._participant(actor_id, trip_id)
        return trip

    def create_invitation(
        self,
        actor_id: UUID,
        trip_id: UUID,
        role: TripRole,
        ttl: timedelta = timedelta(hours=24),
    ) -> Invitation:
        self._require_role(actor_id, trip_id, {TripRole.OWNER})
        if role is TripRole.OWNER:
            raise ValueError("owner invitations are not allowed")
        invitation = Invitation(
            secrets.token_urlsafe(24),
            trip_id,
            role,
            datetime.now(UTC) + ttl,
        )
        self.invitations[invitation.token] = invitation
        return invitation

    def accept_invitation(self, user_id: UUID, token: str) -> Participant:
        self._user(user_id)
        try:
            invitation = self.invitations[token]
        except KeyError:
            raise NotFound("invitation was not found") from None
        if invitation.accepted_by is not None:
            raise ValueError("invitation was already used")
        if invitation.expires_at <= datetime.now(UTC):
            raise ValueError("invitation has expired")
        participant = Participant(invitation.trip_id, user_id, invitation.role)
        self.participants[(invitation.trip_id, user_id)] = participant
        self.invitations[token] = replace(invitation, accepted_by=user_id)
        return participant

    def list_participants(self, actor_id: UUID, trip_id: UUID) -> list[Participant]:
        self._participant(actor_id, trip_id)
        return [item for item in self.participants.values() if item.trip_id == trip_id]

    def add_itinerary_item(
        self,
        actor_id: UUID,
        trip_id: UUID,
        *,
        expected_version: int,
        item_type: ItemType,
        title: str,
        start_at: datetime,
        end_at: datetime,
        timezone: str,
        participant_ids: tuple[UUID, ...] = (),
        provider_reference: str | None = None,
        metadata: dict[str, Any] | None = None,
        state: ItemState = ItemState.PLANNED,
    ) -> ItineraryItem:
        self._require_role(actor_id, trip_id, {TripRole.OWNER, TripRole.EDITOR})
        trip = self._trip(trip_id)
        if expected_version != trip.version:
            raise VersionConflict(trip.version)
        if start_at.tzinfo is None or end_at.tzinfo is None:
            raise ValueError("itinerary times must be timezone-aware")
        if end_at <= start_at:
            raise ValueError("end_at must be after start_at")
        ZoneInfo(timezone)
        for user_id in participant_ids:
            self._participant(user_id, trip_id)
        next_version = trip.version + 1
        item = ItineraryItem(
            uuid4(),
            trip_id,
            item_type,
            title.strip() or item_type.value,
            start_at.astimezone(UTC),
            end_at.astimezone(UTC),
            timezone,
            state,
            participant_ids,
            provider_reference,
            dict(metadata or {}),
            next_version,
        )
        self.items[item.id] = item
        self.trips[trip_id] = replace(trip, version=next_version)
        self.audit[trip_id].append(
            AuditEvent(
                trip_id,
                next_version,
                actor_id,
                "itinerary.created",
                item.id,
                datetime.now(UTC),
                {"item_type": item_type.value, "title": item.title},
            )
        )
        return item

    def list_itinerary(self, actor_id: UUID, trip_id: UUID) -> list[ItineraryItem]:
        self._participant(actor_id, trip_id)
        return sorted(
            (item for item in self.items.values() if item.trip_id == trip_id),
            key=lambda item: (item.start_at, str(item.id)),
        )

    def change_item_state(
        self,
        actor_id: UUID,
        item_id: UUID,
        *,
        expected_version: int,
        state: ItemState,
    ) -> ItineraryItem:
        try:
            item = self.items[item_id]
        except KeyError:
            raise NotFound("itinerary item was not found") from None
        self._require_role(actor_id, item.trip_id, {TripRole.OWNER})
        trip = self._trip(item.trip_id)
        if trip.version != expected_version:
            raise VersionConflict(trip.version)
        next_version = trip.version + 1
        updated = replace(item, state=state, trip_version=next_version)
        self.items[item_id] = updated
        self.trips[item.trip_id] = replace(trip, version=next_version)
        self.audit[item.trip_id].append(
            AuditEvent(
                item.trip_id,
                next_version,
                actor_id,
                "itinerary.state_changed",
                item.id,
                datetime.now(UTC),
                {"state": state.value},
            )
        )
        return updated

    def detect_conflicts(self, actor_id: UUID, trip_id: UUID) -> list[Conflict]:
        items = [
            item
            for item in self.list_itinerary(actor_id, trip_id)
            if item.state not in {ItemState.CANCELLED, ItemState.SUPERSEDED}
        ]
        conflicts: list[Conflict] = []
        for index, first in enumerate(items):
            for second in items[index + 1 :]:
                shares_people = (
                    not first.participant_ids
                    or not second.participant_ids
                    or bool(set(first.participant_ids) & set(second.participant_ids))
                )
                if shares_people and first.start_at < second.end_at and second.start_at < first.end_at:
                    conflicts.append(
                        Conflict(
                            "time_overlap",
                            (first.id, second.id),
                            f"{first.title} overlaps {second.title}",
                        )
                    )
        return conflicts

    def audit_events(self, actor_id: UUID, trip_id: UUID, after_version: int = 0) -> list[AuditEvent]:
        self._participant(actor_id, trip_id)
        return [event for event in self.audit[trip_id] if event.version > after_version]

    def role_for(self, user_id: UUID, trip_id: UUID) -> TripRole:
        return self._participant(user_id, trip_id).role

    def _user(self, user_id: UUID) -> User:
        try:
            return self.users[user_id]
        except KeyError:
            raise NotFound("user was not found") from None

    def _trip(self, trip_id: UUID) -> Trip:
        try:
            return self.trips[trip_id]
        except KeyError:
            raise NotFound("trip was not found") from None

    def _participant(self, user_id: UUID, trip_id: UUID) -> Participant:
        self._user(user_id)
        try:
            return self.participants[(trip_id, user_id)]
        except KeyError:
            raise AccessDenied("user has no access to this trip") from None

    def _require_role(self, user_id: UUID, trip_id: UUID, allowed: set[TripRole]) -> Participant:
        participant = self._participant(user_id, trip_id)
        if participant.role not in allowed:
            raise AccessDenied("role does not allow this operation")
        return participant

