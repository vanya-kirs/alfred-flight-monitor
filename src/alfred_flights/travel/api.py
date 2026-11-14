from __future__ import annotations

from datetime import date, datetime
from typing import Any, Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from alfred_flights.travel.domain import ItemType, TripRole
from alfred_flights.travel.notifications import NotificationOutbox
from alfred_flights.travel.service import AccessDenied, NotFound, TravelService, VersionConflict
from alfred_flights.travel.sync import SyncService


CurrentUser = Annotated[UUID, Header(alias="X-User-ID")]


class CreateUserRequest(BaseModel):
    display_name: str


class CreateTripRequest(BaseModel):
    name: str
    destinations: list[str]
    start_date: date
    end_date: date
    timezone: str


class CreateInvitationRequest(BaseModel):
    role: TripRole


class AcceptInvitationRequest(BaseModel):
    token: str


class CreateItemRequest(BaseModel):
    expected_version: int
    item_type: ItemType
    title: str
    start_at: datetime
    end_at: datetime
    timezone: str
    participant_ids: list[UUID] = Field(default_factory=list)
    provider_reference: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SyncRequest(BaseModel):
    trip_id: UUID
    after_version: int = 0
    operations: list[dict[str, Any]] = Field(default_factory=list)


def create_travel_router(
    service: TravelService,
    sync: SyncService | None = None,
    outbox: NotificationOutbox | None = None,
) -> APIRouter:
    router = APIRouter()

    @router.post("/users", status_code=status.HTTP_201_CREATED)
    def create_user(payload: CreateUserRequest) -> dict[str, Any]:
        try:
            return _user(service.create_user(payload.display_name))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/trips", status_code=status.HTTP_201_CREATED)
    def create_trip(payload: CreateTripRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            trip = service.create_trip(
                user_id,
                payload.name,
                tuple(payload.destinations),
                payload.start_date,
                payload.end_date,
                payload.timezone,
            )
            return _trip(trip)
        except Exception as exc:
            _raise_travel_error(exc)

    @router.get("/trips")
    def list_trips(user_id: CurrentUser) -> list[dict[str, Any]]:
        try:
            return [_trip(item) for item in service.list_trips(user_id)]
        except Exception as exc:
            _raise_travel_error(exc)

    @router.get("/trips/{trip_id}")
    def get_trip(trip_id: UUID, user_id: CurrentUser) -> dict[str, Any]:
        try:
            return _trip(service.get_trip(user_id, trip_id))
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/trips/{trip_id}/invitations", status_code=status.HTTP_201_CREATED)
    def create_invitation(
        trip_id: UUID,
        payload: CreateInvitationRequest,
        user_id: CurrentUser,
    ) -> dict[str, Any]:
        try:
            item = service.create_invitation(user_id, trip_id, payload.role)
            return {
                "token": item.token,
                "trip_id": str(item.trip_id),
                "role": item.role.value,
                "expires_at": item.expires_at.isoformat(),
            }
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/invitations/accept")
    def accept_invitation(payload: AcceptInvitationRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            item = service.accept_invitation(user_id, payload.token)
            return {"trip_id": str(item.trip_id), "user_id": str(item.user_id), "role": item.role.value}
        except Exception as exc:
            _raise_travel_error(exc)

    @router.get("/trips/{trip_id}/participants")
    def list_participants(trip_id: UUID, user_id: CurrentUser) -> list[dict[str, Any]]:
        try:
            return [
                {"trip_id": str(item.trip_id), "user_id": str(item.user_id), "role": item.role.value}
                for item in service.list_participants(user_id, trip_id)
            ]
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/trips/{trip_id}/itinerary", status_code=status.HTTP_201_CREATED)
    def add_item(trip_id: UUID, payload: CreateItemRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            item = service.add_itinerary_item(
                user_id,
                trip_id,
                expected_version=payload.expected_version,
                item_type=payload.item_type,
                title=payload.title,
                start_at=payload.start_at,
                end_at=payload.end_at,
                timezone=payload.timezone,
                participant_ids=tuple(payload.participant_ids),
                provider_reference=payload.provider_reference,
                metadata=payload.metadata,
            )
            return _item(item)
        except Exception as exc:
            _raise_travel_error(exc)

    @router.get("/trips/{trip_id}/itinerary")
    def list_itinerary(trip_id: UUID, user_id: CurrentUser) -> list[dict[str, Any]]:
        try:
            return [_item(item) for item in service.list_itinerary(user_id, trip_id)]
        except Exception as exc:
            _raise_travel_error(exc)

    @router.get("/trips/{trip_id}/conflicts")
    def conflicts(trip_id: UUID, user_id: CurrentUser) -> list[dict[str, Any]]:
        try:
            return [
                {"code": item.code, "item_ids": [str(value) for value in item.item_ids], "message": item.message}
                for item in service.detect_conflicts(user_id, trip_id)
            ]
        except Exception as exc:
            _raise_travel_error(exc)

    @router.get("/trips/{trip_id}/audit")
    def audit(trip_id: UUID, user_id: CurrentUser, after_version: int = 0) -> list[dict[str, Any]]:
        try:
            return [
                {
                    "trip_id": str(item.trip_id),
                    "version": item.version,
                    "actor_id": str(item.actor_id),
                    "action": item.action,
                    "entity_id": str(item.entity_id),
                    "occurred_at": item.occurred_at.isoformat(),
                    "payload": item.payload,
                }
                for item in service.audit_events(user_id, trip_id, after_version)
            ]
        except Exception as exc:
            _raise_travel_error(exc)

    if sync is not None:
        @router.post("/sync")
        def synchronize(payload: SyncRequest, user_id: CurrentUser) -> dict[str, Any]:
            try:
                result = sync.synchronize(
                    user_id,
                    payload.trip_id,
                    after_version=payload.after_version,
                    operations=payload.operations,
                )
                result["changes"] = [
                    {
                        "version": event.version,
                        "action": event.action,
                        "entity_id": str(event.entity_id),
                        "occurred_at": event.occurred_at.isoformat(),
                        "payload": event.payload,
                    }
                    for event in result["changes"]
                ]
                return result
            except Exception as exc:
                _raise_travel_error(exc)

    if outbox is not None:
        @router.get("/notifications/inbox")
        def notification_inbox(user_id: CurrentUser, unread_only: bool = False) -> list[dict[str, Any]]:
            try:
                return [_notification(item) for item in outbox.inbox(user_id, unread_only=unread_only)]
            except Exception as exc:
                _raise_travel_error(exc)

        @router.post("/notifications/{notification_id}/read")
        def read_notification(notification_id: UUID, user_id: CurrentUser) -> dict[str, Any]:
            try:
                return _notification(outbox.mark_read(notification_id, user_id))
            except Exception as exc:
                _raise_travel_error(exc)

    return router


def _raise_travel_error(exc: Exception) -> None:
    if isinstance(exc, VersionConflict):
        raise HTTPException(status_code=409, detail={"message": str(exc), "current_version": exc.current_version}) from exc
    if isinstance(exc, AccessDenied):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, NotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, (ValueError, KeyError)):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


def _user(item: Any) -> dict[str, Any]:
    return {"id": str(item.id), "display_name": item.display_name}


def _trip(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "destinations": list(item.destinations),
        "start_date": item.start_date.isoformat(),
        "end_date": item.end_date.isoformat(),
        "timezone": item.timezone,
        "owner_id": str(item.owner_id),
        "version": item.version,
    }


def _item(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "trip_id": str(item.trip_id),
        "item_type": item.item_type.value,
        "title": item.title,
        "start_at": item.start_at.isoformat(),
        "end_at": item.end_at.isoformat(),
        "timezone": item.timezone,
        "state": item.state.value,
        "participant_ids": [str(value) for value in item.participant_ids],
        "provider_reference": item.provider_reference,
        "metadata": item.metadata,
        "trip_version": item.trip_version,
    }


def _notification(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "trip_id": str(item.trip_id),
        "kind": item.kind,
        "message": item.message,
        "created_at": item.created_at.isoformat(),
        "read_at": item.read_at.isoformat() if item.read_at else None,
    }
