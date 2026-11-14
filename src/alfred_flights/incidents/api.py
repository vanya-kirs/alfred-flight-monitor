from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header
from pydantic import BaseModel

from alfred_flights.incidents.service import IncidentService, incident_dict
from alfred_flights.travel.api import _raise_travel_error

CurrentUser = Annotated[UUID, Header(alias="X-User-ID")]


class ProposalRequest(BaseModel):
    offer_id: str


class ResolutionRequest(BaseModel):
    expected_version: int


def create_incident_router(service: IncidentService) -> APIRouter:
    router = APIRouter(prefix="/incidents")

    @router.get("")
    def list_incidents(trip_id: UUID, user_id: CurrentUser) -> list[dict[str, Any]]:
        try:
            return [incident_dict(item) for item in service.list_for_trip(user_id, trip_id)]
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/{incident_id}/proposal")
    def propose(incident_id: UUID, payload: ProposalRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            return incident_dict(service.propose(user_id, incident_id, payload.offer_id))
        except Exception as exc:
            _raise_travel_error(exc)

    @router.post("/{incident_id}/resolve")
    def resolve(incident_id: UUID, payload: ResolutionRequest, user_id: CurrentUser) -> dict[str, Any]:
        try:
            return incident_dict(service.resolve(user_id, incident_id, payload.expected_version))
        except Exception as exc:
            _raise_travel_error(exc)

    return router
