# Legacy Removal Report

## Official Decision

Ambitionz Rebirth is the only active runtime product.

The pre-Rebirth Arena, Ascension, BE2, SocketIO, SQLAlchemy/database-backed
account systems, economy, progression, shop, collection and old deck builder are
retired from the active Flask app. They remain in the repository only as
historical implementation context.

Do not restore retired routes, APIs or services to make old tests pass. Future
work should migrate useful ideas into Rebirth-native contracts instead.

## Active Product Surface

- `GET /`
- `GET /rebirth`
- `GET /rebirth/account`
- `GET /rebirth/collection`
- `GET /rebirth/shop`
- `GET /rebirth/progression`
- `GET /rebirth/profile`
- `GET /rebirth/desktop`
- `GET /rebirth/onboarding`
- `GET /rebirth/balance`
- `GET /rebirth/release`
- `GET /health`
- `POST /api/rebirth/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/next-turn`
- `GET /api/rebirth/shell`
- `GET /api/rebirth/session`
- `GET /api/rebirth/csrf`
- `POST /api/rebirth/auth/register`
- `POST /api/rebirth/auth/login`
- `POST /api/rebirth/auth/logout`
- `POST /api/rebirth/auth/change-password`
- `GET /api/rebirth/auth-plan`
- `GET /api/rebirth/collection`
- `POST /api/rebirth/loadout`
- `GET /api/rebirth/shop`
- `POST /api/rebirth/booster/open`
- `GET /api/rebirth/progression`
- `GET /api/rebirth/profile`
- `POST /api/rebirth/progression/claim-daily`
- `GET /api/rebirth/desktop`
- `GET /api/rebirth/onboarding`
- `POST /api/rebirth/onboarding/complete`
- `GET /api/rebirth/balance/simulate`
- `GET /api/rebirth/release`

The `/rebirth/collection`, `/rebirth/shop`, `/rebirth/progression` and
`/rebirth/profile` pages are new Rebirth-native persisted surfaces. They do not
reactivate the retired top-level `/collection`, `/shop`, `/progression`,
`/profile`, old economy, old deck builder or old account runtime.

## Redirected Legacy Browser Routes

The following retired browser routes redirect to `/rebirth`:

- `/arena`
- `/training`
- `/training-legacy`
- `/collection`
- `/deck-builder`
- `/shop`
- `/ranking`
- `/leaderboard`
- `/missions`
- `/progression`
- `/campaign`
- `/tutorial`
- `/profile`
- `/how-to-play`
- `/inventory`
- `/economy`
- `/match-history`

Unknown non-API browser routes also redirect to `/rebirth`.

## Disabled Legacy API Routes

The following legacy API groups return JSON `410 legacy_disabled`:

- `/api/ascension/*`
- `/api/beta/*`
- `/api/booster/*`

Unknown API routes return JSON `404 not_found`.

## Test Archive Policy

The authoritative test suite is `tests/rebirth` and is selected through
`pytest.ini`.

Historical tests that target retired systems have been moved to
`tests/legacy_disabled`. That directory contains a README and collection guard
so the repository is explicit about why those tests are outside the default
release gate.

This is intentional release hygiene, not a hidden failure. Those tests assert
pre-Rebirth behavior that the product decision has retired.

## Legacy Files Still Present But Inert

Old modules, templates, CSS, JavaScript and QA scripts remain in the working
tree for auditability. The active Rebirth templates do not load old Arena,
Ascension, economy, progression, shop or deck-builder assets.

Reports and QA screenshots can be large and should not be edited or deleted as
part of release hygiene unless a dedicated cleanup task explicitly asks for it.
