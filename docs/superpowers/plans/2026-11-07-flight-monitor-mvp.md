# Alfred Flight Monitor MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a locally runnable backend that registers flights, polls a provider, rejects stale updates, and records disruption notifications.

**Architecture:** Keep pure monitoring rules in an application service behind repository and provider protocols. Add in-memory adapters for the first executable slice and expose them through FastAPI dependency wiring.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest/httpx for API tests

**Spec:** `docs/superpowers/specs/2026-11-07-flight-monitor-design.md`

## Global Constraints

- Store timezone-aware UTC values only.
- Do not accept or store passport/payment-card data.
- Ignore provider observations older than the last accepted update.
- Never purchase, cancel, or rebook automatically.

## Review Focus

- Naive datetimes must be rejected at registration.
- Duplicate flight numbers on different departure dates must remain distinct.
- Stale provider observations must not roll state backward.
- Repeated identical disruption observations must not duplicate notifications.
- Unknown flight identifiers must produce HTTP 404.

---

### Task 1: Monitoring domain slice

**Files:**
- Create: `src/alfred_flights/domain.py`
- Create: `src/alfred_flights/application.py`
- Create: `src/alfred_flights/adapters/memory.py`
- Test: `tests/test_monitoring.py`

**Interfaces:**
- Produces: `FlightMonitoringService.register_flight(...)`, `FlightMonitoringService.check_flight(...)`, in-memory repository/provider adapters.

- [x] Write tests for registration, UTC validation, delayed/cancelled notifications, stale observations, and notification deduplication.
- [x] Run `python -m unittest discover -s tests -v` and confirm missing production modules fail.
- [x] Implement the minimal domain, ports, service, and memory adapters.
- [x] Re-run the suite and confirm the domain tests pass.

### Task 2: HTTP API

**Files:**
- Create: `src/alfred_flights/api.py`
- Create: `src/alfred_flights/main.py`
- Test: `tests/test_api.py`
- Create: `pyproject.toml`

**Interfaces:**
- Consumes: `FlightMonitoringService` from Task 1.
- Produces: FastAPI application and the endpoints defined in the design.

- [x] Write failing endpoint tests for health, registration, list, check, notification list, validation, and 404 behavior.
- [x] Implement Pydantic schemas, error translation, and dependency wiring.
- [x] Run the full test suite.

### Task 3: Operator documentation and demo

**Files:**
- Create: `README.md`
- Create: `.env.example`

**Interfaces:**
- Consumes: the runnable API from Task 2.
- Produces: setup commands and a deterministic disruption demo.

- [x] Document environment setup, test/run commands, endpoint examples, architecture, limitations, and next slices.
- [x] Execute the documented tests and import smoke check.

