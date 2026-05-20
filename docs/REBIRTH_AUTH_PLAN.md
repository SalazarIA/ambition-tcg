# Rebirth Auth Plan

## Decision

Rebirth auth must be a new Rebirth-native layer. The retired SocketIO,
SQLAlchemy and legacy account/economy runtime is not active and should not be
restored as a shortcut.

## MVP Shape

- Email/password account creation with normalized email and unique username.
- Flask signed session cookie.
- Secure cookie flags in production.
- CSRF protection for state-changing Rebirth JSON routes.
- Small in-memory rate limit for auth endpoints.
- Password change flow for signed-in Rebirth accounts.
- Rebirth user id attached to collection, loadout, booster history and rewards.
- JSON errors that match the existing `{ "ok": false, "error": ... }` shape.

## Current Implementation

Rebirth 011-020 implemented the first real Rebirth auth/persistence layer and
production-oriented MVP hardening.
Passwords are accepted through JSON endpoints, hashed with PBKDF2 and stored in
the Rebirth SQLite database. Account collection, loadout, booster history,
progression, achievements and tutorial state now persist per user.

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

Default path:

```text
instance/rebirth.db
```

Override:

- `REBIRTH_DB_PATH`

Tables:

- `users`
- `user_collection`
- `user_loadout`
- `user_progress`
- `reward_claims`
- `booster_history`
- `user_achievements`

## Non-Goals

- No legacy login restoration.
- No old economy restoration.
- No hidden account mutation from anonymous booster or loadout endpoints.
- No SQLAlchemy/database dependency.
- No payment processor.
