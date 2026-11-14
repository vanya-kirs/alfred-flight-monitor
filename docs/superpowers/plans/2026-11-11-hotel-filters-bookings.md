# Hotel Filters and Trip Bookings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add strict hotel filters, day-specific activity editing, a persistent editable booking summary, and reliable hotel navigation.

**Architecture:** Extend the existing hotel-search request and deterministic hotel metadata so the backend owns filter semantics and stores returned offers for exact detail lookup. Keep itinerary editing and booking-draft aggregation in the current vanilla JavaScript page, persisted in local storage, because this prototype has no authenticated checkout session. Reuse selected flight, hotel, and plan objects as the single source for the booking summary.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, vanilla HTML/CSS/JavaScript, localStorage.

**Spec:** `docs/superpowers/specs/2026-11-11-hotel-filters-bookings-design.md`

## Global Constraints

- Hotel results must satisfy every selected feature and the single selected meal plan.
- Existing unfiltered hotel search must remain backward compatible.
- “Мои бронирования” is a preliminary local draft and must not claim payment or confirmation.
- No raw passport or payment details may be stored.
- All user-facing copy is Russian and matches the current visual system.

## Review Focus

- An impossible combination of hotel filters returns an empty offer list with a useful UI message, not an error.
- Unknown hotel feature or meal codes return HTTP 422 instead of being silently ignored.
- Adding an activity to day 1 never inserts it into day 7 and survives save/reload.
- Removing a flight or hotel clears a dependent plan and updates the total to avoid stale costs.
- A hotel card opens its exact Alfred detail route; generic provider search links are never labeled as the property page.

---

### Task 1: Strict hotel-feature filtering

**Files:**
- Modify: `src/alfred_flights/platform/api.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: existing `InventoryService.search(ItemType.HOTEL, ...)` offers.
- Produces: `HotelSearchRequest.required_features: list[HotelFeature]`, `HotelSearchRequest.meal_plan: MealPlan | None`, and response fields `feature_codes: list[str]`, `meal_code: str`, `cleaning`, `location_tags`, `private_beach`; exact codes come from the spec.

- [ ] **Step 1: Write failing API tests**

Add `test_hotel_search_requires_all_selected_features`, `test_hotel_search_filters_one_meal_plan`, `test_hotel_search_rejects_unknown_filter`, and the impossible-combination assertion. Use literal expected feature codes and verify every returned row satisfies all requested values.

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_api.py -k "hotel_search"`

Expected: FAIL because the request schema and response metadata do not exist.

- [ ] **Step 3: Implement request enums and deterministic metadata**

In `platform/api.py`, define `HotelFeature` and `HotelMealPlan` literals/enums, extend `HotelSearchRequest`, make `_hotel_details(index)` return the machine-readable fields, then filter rows with all-of semantics before sorting.

- [ ] **Step 4: Run hotel tests and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_api.py -k "hotel_search"`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add strict hotel filters`

### Task 2: Hotel filter UI and exact detail links

**Files:**
- Modify: `src/alfred_flights/platform/api.py`
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: Task 1 `required_features`, `meal_plan`, `feature_codes`, and `meal_code` contract.
- Produces: `selectedHotelFilters() -> {required_features: string[], meal_plan: string | null}`, `GET /hotels/{offer_id}`, and current-tab exact-detail anchors.

- [ ] **Step 1: Write failing dashboard contract assertions**

Assert the response exposes the hotel-filter controls, all agreed Russian labels, and the request builder. Add an API test that searches hotels, opens `/hotels/{offer_id}`, and sees the exact title, dates, amenities, and price; verify an unknown offer returns 404.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/pytest -q tests/test_api.py::test_home_page_serves_flight_dashboard`

Expected: FAIL on missing filter controls.

- [ ] **Step 3: Add the compact checkbox filter panel and payload builder**

Add feature checkboxes, exclusive meal select, matching-result summary, empty-result copy, filter payloads in manual and flight-continuation hotel searches, exact hotel detail rendering, and current-tab detail anchors. Label any generic provider URL as “Поиск у поставщика,” never “страница отеля.”

- [ ] **Step 4: Run focused and API hotel tests**

Run: `.venv/bin/pytest -q tests/test_api.py -k "home_page or hotel_search"`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat: add hotel filter controls`

### Task 3: Add activities to the selected day

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: existing `renderPlanDays(timeline)` and `planEventMarkup(event, index)`.
- Produces: per-day `data-add-activity-day="YYYY-MM-DD"` controls and `addActivityToDay(card, dayElement)`.

- [ ] **Step 1: Write the failing dashboard assertion**

Assert the day-scoped control and `addActivityToDay` exist and the old card-level `data-add-activity="strategy"` control is absent.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/pytest -q tests/test_api.py::test_home_page_serves_flight_dashboard`

Expected: FAIL because activity addition is card-scoped.

- [ ] **Step 3: Render and handle one add button per plan day**

Insert the new event after the last event in the clicked day, derive a 90-minute slot, enable inline editing, and persist with `saveEditedPlan(card)`.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_api.py::test_home_page_serves_flight_dashboard`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `fix: add activities to chosen plan day`

### Task 4: Persistent “Мои бронирования” cost editor

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: selected flight, selected hotel, applied plan timeline, original passenger count, hotel nightly price, and Task 3 saved timeline.
- Produces: `bookingDraft`, `saveBookingDraft()`, `renderBookings()`, `calculateBookingTotal(draft)`, and the `bookings` app section.

- [ ] **Step 1: Write failing dashboard assertions**

Assert the fifth navigation target, booking cards, passenger/night editors, remove controls, cost-breakdown labels, and pure calculation function are served.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/pytest -q tests/test_api.py::test_home_page_serves_flight_dashboard`

Expected: FAIL on the missing bookings section.

- [ ] **Step 3: Implement booking-draft state and recalculation**

Persist only JSON-safe selected data. Update it when a flight, hotel, or plan is selected or edited. Apply the spec’s exact flight, hotel, activity, and transfer price rules; render line items and total; enforce dependency invalidation on upstream removal or replacement. Night edits change hotel checkout and cost only, leave flight dates untouched, mark an existing plan stale, and show a date-mismatch warning when applicable.

- [ ] **Step 4: Add editing and removal event handlers**

Passenger and night changes recalculate immediately. Remove actions clear the selected UI state and dependent plan where required. Activity edits reuse the plan editor and refresh bookings after save.

- [ ] **Step 5: Run the focused test and full suite**

Run: `.venv/bin/pytest -q`

Expected: all tests PASS with no warnings.

- [ ] **Step 6: Commit**

Commit: `feat: add editable booking summary`

### Task 5: Browser verification and deployment sync

**Files:**
- Modify only if browser verification reveals a regression.

**Interfaces:**
- Consumes: completed Tasks 1–4.
- Produces: updated live copy at `/Users/airmac/alfred-flight-monitor` and a running server at `127.0.0.1:8001`.

- [ ] **Step 1: Verify the complete flow in the browser**

Search tickets, select one, continue to hotels, apply filters, open a hotel link, select a hotel, build a plan, add an activity to day 1, apply the plan, and verify booking totals update after editing passengers and nights.

- [ ] **Step 2: Sync and run the live copy**

Copy the verified source into `/Users/airmac/alfred-flight-monitor`, keep the local server running, and recheck `/health` plus the dashboard.

- [ ] **Step 3: Final verification**

Run: `.venv/bin/pytest -q`

Expected: all tests PASS.
