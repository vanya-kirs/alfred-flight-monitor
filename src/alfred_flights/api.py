from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, HTTPException, Path as ApiPath, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from alfred_flights.adapters.memory import (
    InMemoryFlightRepository,
    InMemoryNotificationRepository,
    StubFlightStatusProvider,
)
from alfred_flights.application import FlightMonitoringService
from alfred_flights.auth import AccountStore, create_auth_router
from alfred_flights.domain import FlightState, ProviderObservation
from alfred_flights.incidents.api import create_incident_router
from alfred_flights.incidents.service import IncidentService
from alfred_flights.platform.api import create_platform_router
from alfred_flights.platform.service import InventoryService, PersonalizationService, SensitiveReferenceVault
from alfred_flights.planning.api import create_planning_router
from alfred_flights.planning.service import PreliminaryPlanService
from alfred_flights.ticket_search.api import (
    TicketSearchState,
    create_ticket_search_router,
    search_result_to_dict,
)
from alfred_flights.ticket_search.domain import SearchQuery, SortMode
from alfred_flights.ticket_search.providers.demo import DemoTicketProvider
from alfred_flights.ticket_search.service import TicketSearchService
from alfred_flights.travel.api import create_travel_router
from alfred_flights.travel.notifications import NotificationOutbox
from alfred_flights.travel.service import TravelService
from alfred_flights.travel.sync import SyncService


class RegisterFlightRequest(BaseModel):
    flight_number: str
    departure_at: datetime
    origin: str | None = None
    destination: str | None = None


class DemoObservationRequest(BaseModel):
    state: FlightState
    observed_at: datetime
    delay_minutes: int = 0


class FlightAlternativesRequest(BaseModel):
    adults: int = 1
    checked_baggage_required: bool = False
    strict_baggage: bool = False
    visa_free_countries: list[str] = Field(default_factory=list)
    sort_by: SortMode = SortMode.RECOMMENDED


class FlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flight_number: str
    departure_at: datetime
    origin: str | None
    destination: str | None
    state: FlightState
    delay_minutes: int
    last_observed_at: datetime | None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flight_id: UUID
    created_at: datetime
    message: str


class CheckFlightResponse(BaseModel):
    flight: FlightResponse
    notification: NotificationResponse | None


FlightId = Annotated[UUID, ApiPath(description="Registered flight identifier")]

WEB_INDEX = Path(__file__).with_name("web").joinpath("index.html")


def create_app(account_db_path: str | Path = ":memory:") -> FastAPI:
    app = FastAPI(
        title="Alfred Flight Monitor",
        version="0.1.0",
        description="MVP API for detecting flight disruptions.",
    )
    flights = InMemoryFlightRepository()
    notifications = InMemoryNotificationRepository()
    provider = StubFlightStatusProvider()
    service = FlightMonitoringService(
        flights=flights,
        notifications=notifications,
        provider=provider,
    )
    app.state.service = service
    app.state.provider = provider
    ticket_search_state = TicketSearchState()
    ticket_search_service = TicketSearchService(DemoTicketProvider())
    travel_service = TravelService()
    sync_service = SyncService(travel_service)
    travel_outbox = NotificationOutbox(travel_service)
    incident_service = IncidentService(travel_service, ticket_search_service, travel_outbox)
    inventory_service = InventoryService(travel_service)
    personalization_service = PersonalizationService()
    sensitive_vault = SensitiveReferenceVault(travel_service)
    preliminary_plans = PreliminaryPlanService()
    account_store = AccountStore(account_db_path)
    app.state.ticket_search = ticket_search_service
    app.state.ticket_search_state = ticket_search_state
    app.state.travel = travel_service
    app.state.sync = sync_service
    app.state.travel_outbox = travel_outbox
    app.state.incidents = incident_service
    app.state.inventory = inventory_service
    app.state.personalization = personalization_service
    app.state.sensitive_vault = sensitive_vault
    app.state.preliminary_plans = preliminary_plans
    app.state.account_store = account_store
    app.include_router(create_auth_router(account_store))
    app.include_router(create_ticket_search_router(ticket_search_service, ticket_search_state))
    app.include_router(create_travel_router(travel_service, sync_service, travel_outbox))
    app.include_router(create_incident_router(incident_service))
    app.include_router(create_platform_router(inventory_service, personalization_service, sensitive_vault))
    app.include_router(create_planning_router(preliminary_plans))

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def dashboard() -> HTMLResponse:
        return HTMLResponse(WEB_INDEX.read_text(encoding="utf-8"))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/flights",
        response_model=FlightResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def register_flight(payload: RegisterFlightRequest) -> object:
        try:
            return service.register_flight(
                payload.flight_number,
                payload.departure_at,
                payload.origin,
                payload.destination,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/flights", response_model=list[FlightResponse])
    def list_flights() -> object:
        return service.list_flights()

    @app.get("/flights/{flight_id}", response_model=FlightResponse)
    def get_flight(flight_id: FlightId) -> object:
        return _get_flight_or_404(service, flight_id)

    @app.post("/flights/{flight_id}/check", response_model=CheckFlightResponse)
    def check_flight(flight_id: FlightId) -> object:
        _get_flight_or_404(service, flight_id)
        try:
            result = service.check_flight(flight_id)
            incident_service.observe(result.flight)
            return result
        except LookupError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/flights/{flight_id}/alternatives")
    def find_flight_alternatives(
        flight_id: FlightId,
        payload: FlightAlternativesRequest,
    ) -> object:
        flight = _get_flight_or_404(service, flight_id)
        if flight.state not in {FlightState.DELAYED, FlightState.CANCELLED}:
            raise HTTPException(status_code=409, detail="alternatives require a delayed or cancelled flight")
        if not flight.origin or not flight.destination:
            raise HTTPException(status_code=422, detail="flight origin and destination are required")
        try:
            result = ticket_search_service.search(
                SearchQuery(
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_date=flight.departure_at.date(),
                    adults=payload.adults,
                    checked_baggage_required=payload.checked_baggage_required,
                    strict_baggage=payload.strict_baggage,
                    visa_free_countries=tuple(payload.visa_free_countries),
                    sort_by=payload.sort_by,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        search_id = ticket_search_state.store_search(result.offers)
        return search_result_to_dict(result, search_id)

    @app.get("/notifications", response_model=list[NotificationResponse])
    def list_notifications() -> object:
        return service.list_notifications()

    @app.post(
        "/demo/flights/{flight_id}/observation",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
    )
    def set_demo_observation(flight_id: FlightId, payload: DemoObservationRequest) -> Response:
        _get_flight_or_404(service, flight_id)
        try:
            observation = ProviderObservation(
                state=payload.state,
                observed_at=payload.observed_at,
                delay_minutes=payload.delay_minutes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        provider.set_observation(flight_id, observation)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


def _get_flight_or_404(service: FlightMonitoringService, flight_id: UUID) -> object:
    try:
        return service.get_flight(flight_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
