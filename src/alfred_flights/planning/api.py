from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from alfred_flights.planning.service import PreliminaryPlanService


class PreliminaryPlanRequest(BaseModel):
    flight: dict[str, Any]
    hotel: dict[str, Any]


def create_planning_router(service: PreliminaryPlanService) -> APIRouter:
    router = APIRouter()

    @router.post("/preliminary-plans")
    def preliminary_plans(payload: PreliminaryPlanRequest) -> dict[str, Any]:
        try:
            return service.build(payload.flight, payload.hotel)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
