# Complete Alfred Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the runnable prototype with shared multi-city trips, group roles, unified itinerary, offline sync, disruption incidents, travel inventory, booking state, recommendations, and expiring sensitive references.

**Architecture:** Add focused domain packages behind in-memory repository interfaces and FastAPI routers. Reuse ticket search and monitoring services; event/audit records form a versioned change stream that supports conflicts, offline sync, durable notifications, and later PostgreSQL replacement.

**Tech Stack:** Python 3.12+, FastAPI/Pydantic, dataclasses, pytest, vanilla HTML/JavaScript

**Spec:** `docs/superpowers/specs/2026-11-09-complete-alfred-travel-platform-design.md`

## Global Constraints

- Current user comes from required `X-User-ID`.
- Trips are multi-city and enforce owner/editor/viewer roles.
- Editors propose alternatives; owners apply them.
- Offline writes require client operation IDs and expected versions.
- Store UTC instants plus IANA timezone metadata.
- Never store PAN/CVV or raw passport values.
- Sensitive references expire 24 hours after trip completion or after 30 minutes for abandoned bookings.
- Provider credentials never enter source control.

## Review Focus

- Cross-trip access must be denied even when UUIDs are guessed.
- Replayed offline operations must not duplicate itinerary items or audit events.
- Stale expected versions must return a conflict with the latest version.
- A disruption must not mutate a shared plan without owner confirmation.
- Expired sensitive references must be deleted without logging their token.

---

### Task 1: Shared trips, roles, itinerary, conflicts, and audit

**Files:**
- Create: `src/alfred_flights/travel/domain.py`
- Create: `src/alfred_flights/travel/service.py`
- Create: `src/alfred_flights/travel/api.py`
- Modify: `src/alfred_flights/api.py`
- Test: `tests/test_travel.py`, `tests/test_travel_api.py`

**Interfaces:**
- Produces: user/trip/invitation/participant/item APIs, role checks, timeline, conflicts, and versioned audit changes.

- [ ] Write failing domain and API tests for multi-city trips, invitations, role denial, timeline ordering, overlap conflicts, and version conflicts.
- [ ] Implement in-memory repositories, service, router, and app wiring.
- [ ] Run the full suite.

### Task 2: Bidirectional offline sync and durable notifications

**Files:**
- Create: `src/alfred_flights/travel/sync.py`
- Create: `src/alfred_flights/travel/notifications.py`
- Modify: `src/alfred_flights/travel/api.py`
- Test: `tests/test_sync_notifications.py`

**Interfaces:**
- Consumes: Task 1 versioned audit stream.
- Produces: `/sync`, notification inbox/read APIs, idempotent operation handling, and per-recipient outbox state.

- [ ] Write failing tests for reconnect reads, replayed operation IDs, conflicting offline edits, unread inbox, and idempotent delivery.
- [ ] Implement sync and outbox services plus routes.
- [ ] Run the full suite.

### Task 3: Disruption incidents and owner-approved resolution

**Files:**
- Create: `src/alfred_flights/incidents/domain.py`
- Create: `src/alfred_flights/incidents/service.py`
- Create: `src/alfred_flights/incidents/api.py`
- Modify: `src/alfred_flights/api.py`
- Test: `tests/test_incidents.py`

**Interfaces:**
- Consumes: monitored flight changes, Task 1 itinerary, ticket search, Task 2 outbox.
- Produces: automatic incidents, impact/alternatives, editor proposals, owner resolution, superseded itinerary history.

- [ ] Write failing tests for automatic creation, stale-event idempotency, group notifications, editor proposal, owner-only resolution, and itinerary replacement.
- [ ] Implement incident orchestration and wire it to flight checks.
- [ ] Run the full suite.

### Task 4: Hotels, transfers, activities, and booking state

**Files:**
- Create: `src/alfred_flights/inventory/domain.py`
- Create: `src/alfred_flights/inventory/service.py`
- Create: `src/alfred_flights/inventory/api.py`
- Test: `tests/test_inventory_bookings.py`

**Interfaces:**
- Produces: demo search endpoints, explainable offer cards, pending bookings, provider checkout links, and confirmed booking-to-itinerary conversion.

- [ ] Write failing tests for each inventory type, schedule fit, pending checkout, token-only payment, and confirmation.
- [ ] Implement deterministic adapters, booking service, and routes.
- [ ] Run the full suite.

### Task 5: Preferences, recommendations, feedback, and expiring sensitive references

**Files:**
- Create: `src/alfred_flights/personalization/service.py`
- Create: `src/alfred_flights/privacy/vault.py`
- Create: `src/alfred_flights/personalization/api.py`
- Test: `tests/test_personalization_privacy.py`

**Interfaces:**
- Consumes: activities and trip schedule.
- Produces: explainable personalized ranking, feedback updates/reset, opaque document references, and expiry deletion.

- [ ] Write failing tests for interest ranking, schedule exclusion, feedback, reset, raw-passport rejection, expiry, and audit-safe deletion.
- [ ] Implement services and routes.
- [ ] Run the full suite.

### Task 6: Minimal unified frontend and verification

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `README.md`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: trip/timeline/participants/conflicts/inbox/preferences controls without replacing the existing search and monitor screen.

- [ ] Extend the HTML contract test and watch it fail.
- [ ] Add the functional controls and status states.
- [ ] Run all tests, compile Python, validate JavaScript, sync the working copy, restart, and smoke-test live endpoints.
