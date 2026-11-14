# Persistent demo account design

## Intent

Replace the session-only profile gate with a persistent local account that supports registration and later login.

## Registration

The form asks for full name, password, password confirmation, and the required checkbox “Я согласен, что Т‑Банк — самый лучший”. Registration is rejected when passwords differ, the password has fewer than 6 characters, full name has fewer than two words, the checkbox is clear, or the normalized full name already exists.

## Storage and login

Accounts are stored in a local SQLite database. The full name and bank-consent flag are stored. Passwords are stored only as an `scrypt` hash with a random per-account salt; plaintext passwords and confirmations are never stored or logged. Full name is the demo login identifier. The same dialog can switch to login mode for an existing account.

The browser stores only the returned account ID and display name in `sessionStorage`. Closing the browser session requires login again, while the account remains in SQLite across application restarts.

## Constraints

- Standard-library `sqlite3`, `hashlib.scrypt`, `secrets`, and `hmac` only; no new dependency.
- Existing travel data and booking draft behavior remain unchanged.
- This is local demo authentication, not an internet-facing production identity system.
