# Rebirth Auth Plan

## Decision

Rebirth auth is a Rebirth-native layer on the PostgreSQL foundation. The
retired SocketIO and legacy account/economy runtimes are not active and must
not be restored as shortcuts.

## MVP Shape

- Email/password account creation with normalized email and unique username.
- Flask signed session cookie backed by a revocable server-side session token.
- Secure cookie flags in production.
- CSRF protection for state-changing Rebirth JSON routes.
- Small in-memory rate limit for auth endpoints.
- Password change flow for signed-in Rebirth accounts.
- Rebirth user id attached to collection, loadout, booster history and rewards.
- JSON errors that match the existing `{ "ok": false, "error": ... }` shape.

## Current Implementation

Foundation v58 moves the active auth/persistence layer to PostgreSQL using
synchronous SQLAlchemy and `psycopg`. Passwords are accepted through JSON
endpoints and hashed with PBKDF2. Sessions are stored as SHA-256 token hashes
with expiry/revocation timestamps. Collection, loadout, booster history,
progression, achievements, tutorial claims, wallet/ledger and match recovery
persist per user in the same schema.

State-changing `/api/rebirth/*` routes require a session CSRF token by default.
Register/login rotate the Rebirth session, logout clears it, and auth endpoints
are throttled in memory for the current process.

The active page is:

- `GET /rebirth/account`
- `GET /rebirth/profile`

The active APIs are:

- `GET /api/rebirth/session`
- `GET /api/rebirth/csrf`
- `POST /api/rebirth/auth/register`
- `POST /api/rebirth/auth/login`
- `POST /api/rebirth/auth/logout`
- `POST /api/rebirth/auth/change-password`
- `GET /api/rebirth/auth-plan`

## Persistence Store

Required production environment:

```text
REBIRTH_DATABASE_URL=postgresql://...
```

`REBIRTH_DB_PATH` is allowed only in isolated automated tests where
`TESTING=True` or `REBIRTH_ALLOW_SQLITE_TESTING=true`.

Tables:

- `users`
- `user_sessions`
- `user_collection`
- `user_loadout`
- `user_progress`
- `reward_claims`
- `booster_history`
- `user_achievements`
- `wallet_ledger`
- `economy_transactions`
- `economy_ledger`
- `match_history`

## Non-Goals

- No legacy login restoration.
- No old economy restoration.
- No hidden account mutation from anonymous booster or loadout endpoints.
- No async loop/pool split inside Flask requests.
- No real-money payment processor or simulated receipt credit.
