# Alfred Flight Monitor — MVP Design

## Intent

Build the first working backend slice of “Альфред, друг Бэтмена”: a travel assistant that notices a delayed or cancelled flight, explains the impact, and prepares actionable alternatives without buying anything on the user's behalf.

## MVP goals

- Register a flight by number and departure date/time.
- Poll a replaceable flight-status provider.
- Store all instants as timezone-aware UTC values.
- Record a durable notification when a status changes to delayed or cancelled.
- Expose HTTP endpoints to add flights, inspect them, and trigger a status check.
- Keep the domain logic independent of FastAPI and future PostgreSQL/Redis adapters.

## First implementation slice

The initial slice uses an in-memory repository and deterministic demo provider so it runs without API keys. It covers registration, monitoring, stale-provider-data protection, status-change events, and an HTTP API. PostgreSQL, Redis-backed jobs, Telegram delivery, connection-risk calculation, alternative-flight search, and group itineraries are explicit follow-up slices.

## Constraints

- Python 3.11+ and FastAPI.
- No passport or payment-card data in this service.
- External status timestamps older than the last accepted update are ignored.
- A flight change is never treated as permission to buy, cancel, or rebook.
- Provider access is behind an interface so a real aviation API can replace the demo provider.

## API shape

- `POST /flights` registers a flight.
- `GET /flights` lists registered flights.
- `GET /flights/{flight_id}` returns one flight.
- `POST /flights/{flight_id}/check` polls the provider and returns the updated flight plus any newly created notification.
- `GET /notifications` lists durable in-app notifications.
- `GET /health` reports service health.

## Follow-up architecture

FastAPI remains the synchronous edge. PostgreSQL becomes the source of truth; Redis supplies caching and a job queue; a worker polls provider APIs with retries and freshness tracking; notification adapters deliver Telegram/push/SMS; itinerary and alternative-search modules consume flight-change events.

