# Ticket Search and Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add functional one-way/round-trip ticket search with baggage, price, visa and connection assessment, deterministic sorting, offer selection, and a minimal Russian UI.

**Architecture:** A pure domain/service package owns validation, scoring, explanations, and sorting behind a provider protocol. A deterministic demo provider supplies offers; FastAPI exposes search and trip-plan endpoints; the existing framework-free page consumes them.

**Tech Stack:** Python 3.11+, dataclasses, FastAPI/Pydantic, pytest, vanilla HTML/CSS/JavaScript

**Spec:** `docs/superpowers/specs/2026-11-07-ticket-search-design.md`

## Global Constraints

- Search stores no passport or visa data.
- Prices are labeled demo estimates, use EUR, and cover all passengers.
- Selection never purchases or reserves a ticket.
- Existing monitoring endpoints and tests remain unchanged.
- Demo connections below 90 minutes are excluded.

## Review Focus

- Unknown airports and identical origin/destination return validation errors.
- Return dates before departure dates are rejected.
- Passenger counts outside 1–9 are rejected and total price multiplication is exact.
- Baggage-required and visa-risk offers receive visible disadvantages and lower recommendation scores.
- Every sort mode is deterministic under ties.

---

### Task 1: Search domain, assessment, and sorting

**Files:**
- Create: `src/alfred_flights/ticket_search/domain.py`
- Create: `src/alfred_flights/ticket_search/service.py`
- Create: `tests/test_ticket_search.py`

**Interfaces:**
- Produces: `SearchQuery`, `TicketOffer`, `SearchResult`, `TicketSearchService.search(query)`, and `sort_offers(offers, mode)`.

- [x] Write failing tests for validation, passenger price, connection exclusion, baggage/visa explanations, round trips, and all sort modes.
- [x] Run `pytest tests/test_ticket_search.py -q` and confirm failures name missing behavior.
- [x] Implement immutable domain models, airport normalization, assessment/scoring, and stable sorting.
- [x] Run the full suite and confirm it passes.

### Task 2: Deterministic demo provider and API

**Files:**
- Create: `src/alfred_flights/ticket_search/providers/demo.py`
- Create: `src/alfred_flights/ticket_search/api.py`
- Modify: `src/alfred_flights/api.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: Task 1 service and models.
- Produces: `POST /ticket-search`, `POST /trip-plan/selection`, and `GET /trip-plan`.

- [x] Write failing API tests for one-way search, round-trip search, sorting fields, invalid input, and selection persistence.
- [x] Implement demo route catalog, Pydantic schemas, router wiring, and in-memory selected plan.
- [x] Run the full suite and confirm it passes.

### Task 3: Minimal search frontend

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 2 endpoints.
- Produces: search form, filter/sort controls, pros/cons result cards, and selection feedback.

- [x] Extend the dashboard test with the search form and results-region contract and watch it fail.
- [x] Implement the minimal UI and local re-sorting while preserving monitoring controls.
- [x] Run the full suite, compile modules, and smoke-test the live page and search endpoint.
