# Legacy Removal Report

## Removed From Active Product

The active Flask app no longer imports or initializes:

- Arena routes.
- BE2 or old battle engines.
- Socket.io handlers.
- SQLAlchemy models.
- Economy, shop, collection, deck builder, missions, ranking or progression services.
- Old templates, CSS or JavaScript.
- Ascension/Rebirth hybrid intents, 3D adapters or HP 32 combat.

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
- `/how-to-play`
- `/inventory`
- `/economy`
- `/match-history`

## Disabled Legacy API Routes

The following legacy API groups return JSON `410 legacy_disabled`:

- `/api/ascension/*`
- `/api/beta/*`
- `/api/booster/*`

## Legacy Files Still Present But Inert

Old files remain in the repository history and working tree for auditability, but the active product does not import them. They are not loaded by the home or Rebirth game templates.

The active test configuration in `pytest.ini` limits `pytest -q` to the Rebirth MVP tests. Old tests are no longer authoritative for the active product.
