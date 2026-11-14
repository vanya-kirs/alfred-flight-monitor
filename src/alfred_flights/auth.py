from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


def normalize_full_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)


class Account(BaseModel):
    id: str
    full_name: str


class RegisterAccountRequest(BaseModel):
    full_name: str
    password: str
    password_confirmation: str
    bank_consent: bool


class LoginRequest(BaseModel):
    full_name: str
    password: str


class DuplicateAccountError(Exception):
    pass


class AccountStore:
    def __init__(self, database_path: str | Path = ":memory:") -> None:
        path = str(database_path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._lock = Lock()
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL UNIQUE,
                    password_hash BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    bank_consent INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create(self, full_name: str, password: str, bank_consent: bool) -> Account:
        clean_name = " ".join(full_name.split())
        salt = secrets.token_bytes(16)
        account = Account(id=str(uuid4()), full_name=clean_name)
        try:
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO accounts (
                        id, full_name, normalized_name, password_hash, salt,
                        bank_consent, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account.id,
                        account.full_name,
                        normalize_full_name(clean_name),
                        hash_password(password, salt),
                        salt,
                        int(bank_consent),
                        datetime.now(UTC).isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateAccountError from error
        return account

    def authenticate(self, full_name: str, password: str) -> Account | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, full_name, password_hash, salt
                FROM accounts
                WHERE normalized_name = ?
                """,
                (normalize_full_name(full_name),),
            ).fetchone()
        if row is None:
            # Do comparable work for unknown users so the endpoint does not
            # expose account existence through its response branch.
            hash_password(password, b"\0" * 16)
            return None
        account_id, display_name, stored_hash, salt = row
        candidate = hash_password(password, salt)
        if not hmac.compare_digest(candidate, stored_hash):
            return None
        return Account(id=account_id, full_name=display_name)


def create_auth_router(store: AccountStore) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/register", response_model=Account, status_code=status.HTTP_201_CREATED)
    def register(payload: RegisterAccountRequest) -> Account:
        clean_name = " ".join(payload.full_name.split())
        if len(clean_name.split()) < 2:
            raise HTTPException(status_code=422, detail="Укажите имя и фамилию")
        if len(payload.password) < 6:
            raise HTTPException(status_code=422, detail="Пароль должен содержать минимум 6 символов")
        if payload.password != payload.password_confirmation:
            raise HTTPException(status_code=422, detail="Пароли не совпадают")
        if not payload.bank_consent:
            raise HTTPException(status_code=422, detail="Подтвердите, что Т‑Банк — самый лучший")
        try:
            return store.create(clean_name, payload.password, payload.bank_consent)
        except DuplicateAccountError:
            raise HTTPException(status_code=409, detail="Аккаунт с такими ФИО уже существует") from None

    @router.post("/login", response_model=Account)
    def login(payload: LoginRequest) -> Account:
        account = store.authenticate(payload.full_name, payload.password)
        if account is None:
            raise HTTPException(status_code=401, detail="Неверные ФИО или пароль")
        return account

    return router
