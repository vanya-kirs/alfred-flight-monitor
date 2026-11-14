# Preliminary Trip Plans Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build four explainable preliminary itineraries after the user selects both a flight and a hotel.

**Architecture:** Add a deterministic planning service and FastAPI endpoint that consumes selected flight/hotel summaries and returns optimal, comfortable, intensive, and budget variants. Replace the current abstract shared-trip setup on the main screen with a selection summary, readiness state, plan comparison, and apply action; keep advanced group-trip APIs intact.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, vanilla HTML/CSS/JavaScript, pytest

**Spec:** Approved in chat on 2026-11-10.

## Global Constraints

- A plan is generated only when both a flight and hotel are selected.
- Optimal is recommended by default.
- Plans account for arrival, transfer, hotel check-in/out, free time, and activities.
- Do not create bookings or payments when applying a preliminary plan.

## Review Focus

- Hotel check-in before flight arrival must be clamped to the arrival/transfer time.
- Night arrivals must not schedule immediate intensive activities.
- Applying a plan must be local and reversible.
- Re-selecting a flight or hotel must invalidate old plan variants.
- Mobile cards must remain readable.

---

### Task 1: Deterministic plan generation

**Files:**
- Create: `src/alfred_flights/planning/service.py`
- Create: `src/alfred_flights/planning/api.py`
- Modify: `src/alfred_flights/api.py`
- Test: `tests/test_preliminary_plans.py`

- [ ] Write failing tests for required selections, four strategies, night-arrival rest, timeline ordering, and optimal recommendation.
- [ ] Implement `PreliminaryPlanService.build(flight, hotel) -> list[PlanVariant]` and `/preliminary-plans`.
- [ ] Run focused and full tests.

### Task 2: Selection and comparison UI

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

- [ ] Write failing HTML-contract assertions for selection summary and plan cards.
- [ ] Make ticket and hotel cards selectable and retain their summaries.
- [ ] Replace the abstract shared plan block with readiness, four variants, comparison, and an apply button.
- [ ] Verify JavaScript, full tests, live browser flow, and responsive layout.
