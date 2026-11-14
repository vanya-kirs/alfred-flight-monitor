from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from alfred_flights.api import create_app


REGISTRATION = {
    "full_name": "Иван Иванов",
    "password": "secret42",
    "password_confirmation": "secret42",
    "bank_consent": True,
}


def test_registration_persists_hashed_password_and_allows_login_after_restart(tmp_path) -> None:
    database = tmp_path / "accounts.sqlite3"

    with TestClient(create_app(database)) as client:
        registration = client.post("/auth/register", json=REGISTRATION)

    assert registration.status_code == 201
    assert registration.json()["full_name"] == "Иван Иванов"
    assert set(registration.json()) == {"id", "full_name"}

    with sqlite3.connect(database) as connection:
        password_hash, salt, bank_consent = connection.execute(
            "SELECT password_hash, salt, bank_consent FROM accounts"
        ).fetchone()
    assert password_hash != REGISTRATION["password"].encode()
    assert len(password_hash) == 32
    assert len(salt) == 16
    assert bank_consent == 1

    with TestClient(create_app(database)) as restarted_client:
        login = restarted_client.post(
            "/auth/login",
            json={"full_name": "  иВАН   иванов ", "password": "secret42"},
        )

    assert login.status_code == 200
    assert login.json() == registration.json()


def test_registration_rejects_mismatched_password_confirmation() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/auth/register",
            json={**REGISTRATION, "password_confirmation": "different"},
        )

    assert response.status_code == 422
    assert "не совпадают" in response.json()["detail"]


def test_registration_requires_bank_consent() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/auth/register",
            json={**REGISTRATION, "bank_consent": False},
        )

    assert response.status_code == 422
    assert "Т‑Банк" in response.json()["detail"]


def test_registration_rejects_duplicate_normalized_full_name() -> None:
    with TestClient(create_app()) as client:
        assert client.post("/auth/register", json=REGISTRATION).status_code == 201
        duplicate = client.post(
            "/auth/register",
            json={**REGISTRATION, "full_name": "  ИВАН   ИВАНОВ  "},
        )

    assert duplicate.status_code == 409
    assert "уже существует" in duplicate.json()["detail"]


def test_login_rejects_wrong_password_without_revealing_account_details() -> None:
    with TestClient(create_app()) as client:
        assert client.post("/auth/register", json=REGISTRATION).status_code == 201
        wrong_password = client.post(
            "/auth/login",
            json={"full_name": "Иван Иванов", "password": "incorrect"},
        )
        unknown_account = client.post(
            "/auth/login",
            json={"full_name": "Пётр Петров", "password": "incorrect"},
        )

    assert wrong_password.status_code == 401
    assert unknown_account.status_code == 401
    assert wrong_password.json() == unknown_account.json() == {"detail": "Неверные ФИО или пароль"}
