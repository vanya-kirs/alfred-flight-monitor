# Guided Travel UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make registration, flight-to-hotel continuation, plan editing, booking recommendations, project information, and multi-filter hotel search clear and functional.

**Architecture:** Keep all demo identity and dialog orchestration in the existing vanilla JavaScript page, with passwords never persisted. Keep strict hotel-filter semantics in FastAPI, but enrich deterministic offer metadata and give empty strict searches a useful UI recovery path.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, vanilla HTML/CSS/JavaScript, sessionStorage/localStorage.

**Spec:** `docs/superpowers/specs/2026-11-13-guided-travel-ux-design.md`

## Global Constraints

- No new dependencies.
- Passwords are never stored or transmitted.
- Synthetic provider search URLs are not presented as property pages.
- Flight dates never change when hotel recommendations are applied.
- UI copy remains Russian.

## Review Focus

- Registration reloads without retaining the password.
- Hotel popup appears only after a flight is selected and dismissal does not select an hotel.
- New and modified activities use the requested day/time and remain chronologically ordered.
- Applying a booking recommendation changes hotel/passenger draft values only, never flight dates.
- Several common hotel filters plus each meal plan return strict matches; impossible combinations produce a recoverable empty state.

---

### Task 1: Hotel filter density and truthful hotel detail

**Files:**
- Modify: `src/alfred_flights/platform/api.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: richer `_hotel_details(index)` feature overlap and no generic provider button on `/hotels/{detail_id}`.

- [ ] Add failing tests for common multi-feature combinations across meal plans and absence of “Поиск у поставщика” on synthetic details.
- [ ] Run focused tests and verify RED.
- [ ] Enrich deterministic feature sets without weakening all-of filtering; replace the external link with a demo-data notice.
- [ ] Run focused tests and verify GREEN.

### Task 2: Registration, project dialog, and visible hotel continuation

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `register-gate`, `project-dialog`, `hotel-next-step`, `completeDemoRegistration()`, and `showHotelContinuationPopup()`.

- [ ] Add failing dashboard contract assertions for registration fields, project dialog, GitHub placeholder, and fixed continuation popup.
- [ ] Run the dashboard test and verify RED.
- [ ] Implement the dialogs, session-only name persistence, password non-persistence, top-bar identity, and popup actions.
- [ ] Run the dashboard test and verify GREEN.

### Task 3: Time-aware plan change dialog

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `plan-change-dialog`, `openPlanChangeEditor(card)`, and `applyPlanChange()`.

- [ ] Add failing assertions for mode, target, date, time, duration, and apply controls.
- [ ] Run the dashboard test and verify RED.
- [ ] Implement modify/create flows, ISO timestamp construction, chronological sorting, persistence, and plan rerendering.
- [ ] Run the dashboard test and verify GREEN.

### Task 4: Read-only booking draft with Alfred recommendation

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `recommendedBookingParameters(draft)` and `applyBookingRecommendation()`; removes direct number-input mutation.

- [ ] Add failing assertions that booking parameters are read-only metrics and recommendation functions/actions exist.
- [ ] Run the dashboard test and verify RED.
- [ ] Replace inputs/listeners with read-only metrics, recommendation copy, and explicit application that preserves flight dates.
- [ ] Run the dashboard test and full suite.

### Task 5: Empty-filter recovery, sync, and browser verification

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify only if needed: `tests/test_api.py`

**Interfaces:**
- Produces: selected-filter summary and `resetHotelFilters()` recovery action.

- [ ] Add failing dashboard assertions for reset behavior and explicit strict-empty copy.
- [ ] Implement filter summary and one-click reset/research.
- [ ] Run the full suite and JavaScript syntax check.
- [ ] Sync to `/Users/airmac/alfred-flight-monitor`, restart port 8001, and verify registration, popup, editor, bookings, project dialog, and filter flow in the browser.
