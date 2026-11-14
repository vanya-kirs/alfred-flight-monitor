# Persistent Account Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist local Alfred accounts with password confirmation, required bank consent, and login.

**Architecture:** Add an isolated SQLite-backed account store and auth router. Keep only account identity in browser session storage; all credential verification happens in FastAPI.

**Tech Stack:** Python 3.12 standard library, FastAPI, Pydantic, pytest, vanilla JavaScript.

**Spec:** `docs/superpowers/specs/2026-11-13-persistent-account-design.md`

## Global Constraints

- Never store plaintext passwords or confirmations.
- Use `scrypt` with a random salt and constant-time comparison.
- Keep all existing APIs backward compatible.

## Review Focus

- A second application instance using the same database accepts login for the registered account.
- Mismatched passwords and missing bank consent return validation errors.
- Duplicate full names are rejected case-insensitively.
- Wrong passwords do not reveal whether the hash or salt exists.
- The browser never writes password values to local or session storage.

---

### Task 1: Persistent account store and auth API

**Files:**
- Create: `src/alfred_flights/auth.py`
- Modify: `src/alfred_flights/api.py`
- Modify: `src/alfred_flights/main.py`
- Create: `tests/test_auth.py`

**Interfaces:**
- Produces: `AccountStore`, `POST /auth/register`, and `POST /auth/login`.

- [ ] Write failing tests for registration, mismatch, consent, duplicate, wrong password, and cross-instance persistence.
- [ ] Run `tests/test_auth.py` and verify RED.
- [ ] Implement SQLite schema, scrypt hashing, router, configurable app database path, and persistent live path.
- [ ] Run auth tests and verify GREEN.

### Task 2: Registration/login dialog

**Files:**
- Modify: `src/alfred_flights/web/index.html`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: Task 1 auth endpoints.
- Produces: confirmation input, required bank checkbox, register/login mode, and session account identity.

- [ ] Write failing dashboard assertions for confirmation, consent, login switch, and absence of the old separate consent gate.
- [ ] Run dashboard test and verify RED.
- [ ] Implement API-backed register/login flow and remove the session-only credential validation.
- [ ] Run dashboard and full tests, sync live copy, restart, and browser-verify registration plus login.
